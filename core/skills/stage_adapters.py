"""Common stage adapters. All numerical work stays in the existing algorithms."""
from pathlib import Path
import pandas as pd
from .md_adapter import output, persist


def _frame(context, kind):
    frame = context["resolver"].load_frame(kind)
    if frame is None or frame.empty:
        raise ValueError(f"缺少有效 {kind}")
    return frame


def _agent(context, frame, parameters):
    from core.services.pipeline import _cleaning_spec
    from integrations.data_cleaning.src.data_cleaning_agent import DataCleaningSelectionAgent
    scene = context["scene_context"]
    dictionary = context["resolver"].load_json("FIELD_DICTIONARY") or []
    names = set(scene.get("input_columns", [])) | {scene.get("target_column")} | set(scene.get("metadata", {}).get("model_outputs", []))
    spec = _cleaning_spec(dictionary, [name for name in frame.columns if name in names])
    if not scene.get("target_column") or scene["target_column"] not in spec:
        raise ValueError("SceneContext 缺少有效 target 角色")
    return DataCleaningSelectionAgent(spec, resample_rule=f"{parameters.get('resample_seconds', scene.get('sampling_interval') or 10)}s",
        primary_output=scene["target_column"], selection_window=parameters.get("window_length", 30), selection_step=parameters.get("step", 15)), spec


def _write_frame(context, kind, frame):
    return context["resolver"].write_frame(kind, frame, Path(context["output_dir"])/(kind.lower()+".csv"), context["skill_id"], context["execution_id"]).public()


def align(context, inputs, parameters):
    frame = _frame(context, "STANDARDIZED_DATA").reset_index()
    timestamp = context["scene_context"].get("timestamp_column", "timestamp")
    if timestamp not in frame:
        return output(context, {}, [], status="unavailable", warnings=["缺少场景时间轴"])
    frame = frame.rename(columns={timestamp: "timestamp"}).sort_values("timestamp").reset_index(drop=True)
    if len(frame) < context["scene_context"].get("constraints", {}).get("minimum_rows", 150):
        return output(context, {}, [], status="unavailable", warnings=["insufficient_data：不足 150 行，不能冻结独立训练/验证/测试分区"])
    intervals = pd.to_datetime(frame.timestamp).diff().dt.total_seconds()
    native = intervals[intervals > 0].median()
    requested = parameters.get("resample_seconds", 10)
    seconds = max(requested, native) if pd.notna(native) else requested
    cuts = [0, int(len(frame)*.6), int(len(frame)*.8), len(frame)]
    refs, parts, previous = [], {}, None
    for i, label in enumerate(("TRAIN", "VALIDATION", "TEST")):
        agent, _ = _agent(context, frame, {**parameters, "resample_seconds": seconds})
        aligned = agent.align_timestamp(frame.iloc[cuts[i]:cuts[i+1]])
        if previous is not None:
            aligned = aligned.loc[aligned.index > previous]
        if aligned.empty:
            raise ValueError("时间轴对齐后分区为空")
        previous = aligned.index[-1]
        refs.append(_write_frame(context, "ALIGNED_"+label, aligned))
        parts[label.lower()] = {"rows": len(aligned), "start": str(aligned.index[0]), "end": str(aligned.index[-1])}
    guard = max(4, min(2*int(parameters.get("max_lag",60))+3, min(parts[k]["rows"] for k in ("validation","test"))//3))
    split = {"protocol": "chronological_60_20_20_v2", "guard_samples": guard, "seconds": float(seconds), "partitions": parts}
    refs.append(persist(context, "FROZEN_SPLIT", split, "split_manifest.json"))
    return output(context, {"partitions": parts, "sampling_seconds": float(seconds)},
        [{"method": "DataCleaningSelectionAgent.align_timestamp", "split_before_processing": True, "requested_seconds": requested}],
        artifacts=refs, algorithm="DataCleaningSelectionAgent.align_timestamp")


def clean(context, inputs, parameters):
    refs, metrics = [], {}
    for label in ("TRAIN", "VALIDATION", "TEST"):
        frame = _frame(context, "ALIGNED_"+label)
        agent, _ = _agent(context, frame, parameters)
        cleaned = agent.detect_and_repair_anomalies(agent.process_missing_values(frame))
        refs.append(_write_frame(context, "CLEANED_"+label, cleaned))
        metrics[label.lower()] = {"rows": len(cleaned), "missing_rate": agent.raw_missing_rate,
                                  "target_observations": int(cleaned[context['scene_context']['target_column']].notna().sum())}
    return output(context, metrics, [{"method": "causal partition-local cleaning", "target_interpolated": False}],
        artifacts=refs, algorithm="DataCleaningSelectionAgent.process_missing_values + detect_and_repair_anomalies")


def segment(context, inputs, parameters):
    from core.services.segmentation_service import run_segmentation_stage
    train = _frame(context, "CLEANED_TRAIN")
    dictionary = context["resolver"].load_json("FIELD_DICTIONARY")
    split = context["resolver"].load_json("FROZEN_SPLIT")
    result = run_segmentation_stage(train, dictionary, Path(context["output_dir"]),
        primary_output=context["scene_context"].get("target_column"),
        window_length=parameters.get("window_length",30), step=parameters.get("step",15),
        split_version=split["protocol"], upstream_run_id=context["scene_context"].get("dataset_ref", ""))
    if result["status"] != "success":
        return output(context, {}, result.get("evidence",[]), status="unavailable", warnings=result.get("limitations",[]))
    result.pop("_segments_frame"); result.pop("_modeling_frame")
    # This shared algorithm computes window score and SNR together exactly once.
    # Downstream views consume this receipt rather than repeating the algorithm.
    ref = persist(context, "SEGMENTATION_REPORT", result, "segmentation_receipt.json")
    return output(context, result["metrics"], result["evidence"], artifacts=[ref],
        warnings=result["limitations"], algorithm="segmentation_service.run_segmentation_stage")


def select_segments(context, inputs, parameters):
    from core.services.segmentation_service import select_modeling_rows, select_modeling_windows
    train = _frame(context, "CLEANED_TRAIN")
    report = context["resolver"].load_json("SEGMENTATION_REPORT")
    segments = pd.DataFrame(report["segments"])
    if segments.empty:
        return output(context, {}, [], status="unavailable", warnings=["insufficient_data：无有效动态窗口"])
    strict = segments[segments.level == "优质动态段"]
    relaxed = bool(report.get("metrics", {}).get("relaxed_acceptance"))
    accepted = pd.DataFrame(report.get("selected_segments", [])) if relaxed else segments
    chosen = select_modeling_rows(train, accepted, top_k=parameters.get("top_k",5), strict_first=not relaxed)
    selected_windows = select_modeling_windows(accepted, parameters.get("top_k",5), strict_first=not relaxed)
    refs = [_write_frame(context,"MODELING_DATASET",chosen), persist(context,"SELECTED_SEGMENTS",selected_windows.to_dict("records"),"selected_segments.json")]
    return output(context, {"selected_rows":len(chosen),"strict_windows":len(strict),"accepted_windows":len(selected_windows),"relaxed_acceptance":relaxed,"degraded_candidate":strict.empty},
        [{"method":"select_modeling_rows", "window_score_and_snr_reused":True}], artifacts=refs,
        status="success" if (not strict.empty or relaxed) else "partial",
        warnings=["小样本自适应分层筛选已接纳工程可用段，严格段数量单独保留用于结果分级"] if relaxed else (["无严格优质动态段，沿用现有最高分候选策略；不能当作高质量证据"] if strict.empty else []), algorithm="segmentation_service.select_modeling_rows")


def rank(context, inputs, parameters):
    report = context["resolver"].load_json("SEGMENTATION_REPORT")
    rows = report["segment_scores"]
    ref = persist(context,"SEGMENT_RANKING",rows,"ranking.json")
    return output(context,{"ranked_windows":len(rows)},[{"method":"reuse select_dynamic_segments sorted score", "recomputed":False}],artifacts=[ref],status="read")


def assemble(context, inputs, parameters):
    frame = _frame(context,"MODELING_DATASET")
    report = context["resolver"].load_json("COLLINEARITY_REPORT")
    kept = [name.removesuffix("_aligned") for name in report["recommendation"]["keep"]]
    target = context["scene_context"].get("target_column")
    if not target:
        # Compatibility input roles are explicit in the persisted delay result.
        target = _frame(context,"TIME_DELAY_ESTIMATES").iloc[0]["output"]
    selected = frame[[*kept,target]].copy()
    ref = _write_frame(context,"MODEL_READY_DATASET",selected)
    return output(context,{"rows":len(selected),"inputs":kept,"target":target},
        [{"method":"reuse selected training rows and variable recommendation", "target_interpolated":False}],artifacts=[ref],status="read")


def train(context, inputs, parameters):
    from core.services.pipeline import INTEGRATIONS_DIR, _module_path
    selected = context["resolver"].load_json("ARX_SELECTED_STRUCTURE")
    state = selected["fitted_state"]
    test = _frame(context,"CLEANED_TEST").reset_index()
    if "timestamp" not in test or pd.to_datetime(test.timestamp).min() <= pd.Timestamp(selected["validation_end"]):
        return output(context, {}, [], status="unavailable", warnings=["测试时间范围必须晚于冻结验证集，禁止重叠评价"])
    with _module_path(INTEGRATIONS_DIR/"identification"):
        from validated_modeling import evaluation
        metrics, diagnostics, _, _ = evaluation(test,state,selected["guard_samples"],"test")
    all_metrics = {"train": selected["metrics"]["train"], "validation": selected["metrics"]["validation"], "test":metrics}
    full = {"config":{"family":state["family"]},"metrics":all_metrics,
            "diagnostics":{**selected["diagnostics"],"test":diagnostics},"fitted_state":state}
    refs = [persist(context,"MODEL_ARTIFACT",full,"model.json"),persist(context,"MODEL_METRICS",all_metrics,"metrics.json")]
    context["state"]["modeling"] = full
    return output(context,all_metrics,[{"method":"reuse selected fitted coefficients + one held-out test evaluation","retrained":False,"test_evaluations":1}],
        artifacts=refs,algorithm="validated_modeling.evaluation")


def diagnose(context, inputs, parameters):
    from core.skills.core_executors import ModelDiagnosticsCapabilityExecutor
    model = context["resolver"].load_json("MODEL_ARTIFACT")
    if isinstance(model,dict) and model.get("metrics"):
        context["state"]["modeling"] = model
    result = ModelDiagnosticsCapabilityExecutor().execute(context["skill_id"],[context["skill_id"]],context["task_spec"],context["data_context"],inputs,context)
    if result["status"] == "blocked":
        result["status"] = "unavailable"
    return result
