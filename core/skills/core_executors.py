from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from .artifacts import RuntimeArtifactResolver


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _result(skill_id: str, started: float, *, status: str = "success", capabilities: list[str] | None = None,
            facts: list[str] | None = None, findings: list[str] | None = None, hypotheses: list[str] | None = None,
            limitations: list[str] | None = None, metrics: dict[str, Any] | None = None, artifacts: list[str] | None = None,
            evidence: list[Any] | None = None, warnings: list[str] | None = None, trace: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "status": status, "skill_id": skill_id, "capabilities_executed": capabilities or [],
        "facts": facts or [], "findings": findings or [], "hypotheses": hypotheses or [],
        "limitations": limitations or [], "metrics": metrics or {}, "artifacts": artifacts or [],
        "evidence": evidence or [], "warnings": warnings or [], "execution_trace": trace or [],
        "duration_ms": round((perf_counter() - started) * 1000),
    }


def _artifact_path(snapshot: dict[str, Any], key: str) -> Path | None:
    ref = RuntimeArtifactResolver(snapshot).resolve(key)
    return Path(ref.path) if ref else None


class StandardizationExecutor:
    skill_id = "standardization"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_standardization_stage
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        source = inputs.get("data_path") or _artifact_path(snapshot, "source_csv")
        if source is None and snapshot.get("_dataframe") is not None:
            source = Path(runtime_context["output_dir"]) / "input" / "source.csv"
            source.parent.mkdir(parents=True, exist_ok=True)
            snapshot["_dataframe"].to_csv(source, index=False)
        if source is None:
            return _result(skill_id, started, status="blocked", limitations=["缺少源 CSV 或 DataFrame 文件引用。"])
        run_dir = Path(runtime_context["output_dir"]) / "standardization"
        frame, report = run_standardization_stage(Path(source), run_dir, "auto", task_spec.get("objective", ""), inputs.get("overrides"))
        state.update(standardized_data=frame, standardization=report, dictionary=report.get("dictionary", []), stage_run_dir=run_dir)
        mapping = report.get("mapping", {})
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"自动识别数据场景为 {report.get('scenario', {}).get('scenario_id', 'unknown')}。",
                   f"字段覆盖 {mapping.get('matched_count', 0)}/{report.get('source_column_count', len(frame.columns))}。"],
            limitations=[item.get("message", str(item)) for item in report.get("issues", [])],
            metrics={"scene": report.get("scenario", {}), "mapping": mapping, "data_decision": report.get("data_decision", {})},
            artifacts=list(report.get("artifacts", {}).values()), evidence=[report.get("runtime_trace", {})],
            trace=[{"step": "StandardizationAgent.standardize", "scenario_id": "auto", "status": "completed"}])


class CleaningExecutor:
    skill_id = "cleaning"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_cleaning_stage, _read_csv
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        standardized = state.get("standardized_data")
        if standardized is None:
            path = _artifact_path(snapshot, "standardized_csv")
            standardized = _read_csv(path) if path else None
        standard = state.get("standardization") or snapshot.get("results", {}).get("standardization", {})
        dictionary = state.get("dictionary") or standard.get("dictionary", [])
        if standardized is None or not dictionary:
            return _result(skill_id, started, status="blocked", limitations=["缺少标准化数据或字段字典。"])
        run_dir = Path(runtime_context["output_dir"]) / "cleaning"
        params = inputs.get("parameters", {})
        modeling, segments, report = run_cleaning_stage(
            standardized, dictionary, run_dir, params.get("resample_rule", "10s"), params.get("max_lag", 60),
            primary_output=standard.get("scenario", {}).get("primary_output"),
            selection_window=standard.get("scenario", {}).get("selection_window_samples", 30),
            selection_step=standard.get("scenario", {}).get("selection_step_samples", 15),
            include_segmentation=False,
        )
        partitions = report.pop("_partitions", {"train": modeling})
        state.update(train_data=partitions.get("train", modeling), validation_data=partitions.get("validation"), test_data=partitions.get("test"),
                     modeling_data=modeling, segments=segments, cleaning=report, dictionary=dictionary, stage_run_dir=run_dir)
        before = int(report.get("source_row_count") or len(standardized))
        after = int(report.get("cleaned_row_count") or 0)
        audit = {"rows_before": before, "rows_after": after, "rows_changed": abs(before - after),
                 "rules": report.get("logs", []), "missing_rate": report.get("missing_rate", {}),
                 "anomaly_rate": report.get("anomaly_rate", {})}
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"清洗前 {before} 行，清洗后 {after} 行。"],
            findings=[f"清洗质量评分 {report.get('overall_score', 'unknown')}；本节点没有执行动态分段。"],
            limitations=["窗口 SNR 是代理估计，不能视为仪表标定结果。"], metrics=audit,
            artifacts=list(report.get("artifacts", {}).values()), evidence=[audit],
            trace=[{"step": "DataCleaningSelectionAgent", "status": "completed", "rules": report.get("logs", [])}])


class SegmentationExecutor:
    skill_id = "segmentation"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import _read_csv
        from core.services.segmentation_service import run_segmentation_stage
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        train = state.get("train_data")
        resolver = RuntimeArtifactResolver(snapshot, state)
        if train is None:
            ref = resolver.resolve("train_csv", "cleaning")
            if ref:
                train = _read_csv(Path(ref.path))
                if "timestamp" in train:
                    train["timestamp"] = pd.to_datetime(train["timestamp"], errors="coerce")
                    train = train.set_index("timestamp")
        standard = state.get("standardization") or snapshot.get("results", {}).get("standardization", {})
        dictionary = state.get("dictionary") or standard.get("dictionary", [])
        cleaning = state.get("cleaning") or snapshot.get("results", {}).get("cleaning", {})
        split = cleaning.get("split", {})
        if train is None or not split:
            missing = []
            if train is None:
                missing.append("cleaned_training_data")
            if not split:
                missing.append("frozen_split")
            return _result(skill_id, started, status="blocked", limitations=["分段缺少前置条件：" + "、".join(missing)],
                           evidence=[{"dependency": "cleaning", "status": "missing"}])
        params = inputs.get("parameters", {})
        output = Path(runtime_context["output_dir"]) / "segmentation"
        result = run_segmentation_stage(
            train, dictionary, output, upstream_run_id=str(snapshot.get("run_id") or "skill-runtime"),
            split_version=split.get("protocol", ""), window_length=int(params.get("window_length", 30)),
            step=int(params.get("step", 15)), primary_output=standard.get("scenario", {}).get("primary_output"),
        )
        if result["status"] != "success":
            return _result(skill_id, started, status="blocked", limitations=result.get("limitations"), evidence=result.get("evidence"))
        state.update(segmentation=result, segments=result.pop("_segments_frame"), modeling_data=result.pop("_modeling_frame"))
        refs = [resolver.register(key, path, skill_id, str(runtime_context.get("execution_id", "segmentation"))).public()
                for key, path in result["artifacts"].items()]
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"只使用训练分区评估 {result['metrics']['candidate_count']} 个窗口。"],
            findings=[f"选中 {result['metrics']['selected_count']} 个优质动态段、{result['metrics']['selected_row_count']} 行建模数据。"],
            limitations=result["limitations"], metrics={**result["metrics"], "snr": result["snr_metrics"]},
            artifacts=refs, evidence=result["evidence"], warnings=result["warnings"],
            trace=[{"step": "run_segmentation_stage", "scope": "training_only", "validation_rows_read": 0, "test_rows_read": 0, "status": "completed"}])


class ModelingExecutor:
    skill_id = "modeling"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_modeling_stage, _read_csv
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        modeling = state.get("modeling_data")
        if modeling is None:
            path = _artifact_path(snapshot, "modeling_csv")
            modeling = _read_csv(path) if path else None
        standard = state.get("standardization") or snapshot.get("results", {}).get("standardization", {})
        dictionary = state.get("dictionary") or standard.get("dictionary", [])
        if modeling is None or not dictionary:
            return _result(skill_id, started, status="blocked", limitations=["缺少建模数据或字段字典。"])
        run_dir = Path(runtime_context["output_dir"]) / "modeling"
        run_dir.mkdir(parents=True, exist_ok=True)
        # _model expects the frozen split artifacts beside its run directory. Copying is avoided;
        # a prior executor supplies its own stage directory, otherwise use the pipeline run directory.
        source_run_dir = state.get("stage_run_dir")
        if source_run_dir and (Path(source_run_dir) / "03_cleaning").exists():
            run_dir = Path(source_run_dir)
        elif snapshot.get("run_id"):
            from core.services.pipeline import RUNS_DIR
            run_dir = RUNS_DIR / str(snapshot["run_id"])
        params = inputs.get("parameters", {})
        modeling_path = run_dir / "03_cleaning" / "modeling_dataset.csv"
        if not modeling_path.exists() or state.get("modeling_data") is not None:
            modeling_path.parent.mkdir(parents=True, exist_ok=True)
            modeling.reset_index().to_csv(modeling_path, index=False, encoding="utf-8-sig")
        report = run_modeling_stage(modeling, dictionary, run_dir, params.get("max_lag", 60),
                        modeling_path=modeling_path, primary_output=standard.get("scenario", {}).get("primary_output"))
        state["modeling"] = report
        diagnostics = report.get("diagnostics", {}).get("test", {})
        baseline = {
            "persistence": diagnostics.get("persistence"),
            "rmse_improvement_over_persistence_pct": diagnostics.get("rmse_improvement_over_persistence_pct"),
            "multi_step_persistence": diagnostics.get("multi_step", {}).get("persistence"),
        }
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"模型族 {report.get('config', {}).get('family', 'unknown')}，训练样本 {report.get('training_rows', 0)}。"],
            findings=[f"独立测试相对持续值基线 RMSE 改善 {baseline['rmse_improvement_over_persistence_pct']}%。"],
            limitations=["模型结论仅适用于冻结的数据分区和已记录输入范围。"],
            metrics={"model": report.get("config", {}), "train": report.get("metrics", {}).get("train", {}),
                     "validation": report.get("metrics", {}).get("validation", {}), "test": report.get("metrics", {}).get("test", {}),
                     "baseline_comparison": baseline}, artifacts=list(report.get("artifacts", {}).values()),
            evidence=[report.get("order_search", []), report.get("diagnostics", {})],
            trace=[{"step": "run_validated_modeling", "status": "completed", "baseline_compared": True}])


class OptimizationExecutor:
    skill_id = "optimization"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_optimization_stage
        started = perf_counter()
        request = dict(inputs.get("optimization_request") or {})
        state = runtime_context.get("state", {})
        # A planner/snapshot must declare the optimization policy. Upstream
        # executors may satisfy only artifact/data slots; they never invent an
        # objective, bounds, constraints or search policy.
        runtime_artifacts = {
            "model_artifact": state.get("modeling"),
            "frozen_split": state.get("cleaning", {}).get("split"),
            "training_data": state.get("train_data"),
            "validation_data": state.get("validation_data"),
            "test_data": state.get("test_data"),
            "segments": state.get("segments"),
            "field_dictionary": state.get("dictionary"),
            "primary_output": state.get("standardization", {}).get("scenario", {}).get("primary_output"),
        }
        for key, value in runtime_artifacts.items():
            if request.get(key) is None and value is not None:
                request[key] = value
        required = {"objective", "model_artifact", "frozen_split", "training_data", "validation_data", "test_data",
                    "segments", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "field_dictionary", "real_data"}
        def present(value):
            if value is None or isinstance(value, str) and not value.strip():
                return False
            if isinstance(value, (list, dict, tuple, set)):
                return bool(value)
            if isinstance(value, pd.DataFrame):
                return not value.empty
            return True
        missing = sorted(key for key in required if not present(request.get(key)))
        if missing:
            return _result(skill_id, started, status="blocked", limitations=["优化缺少前置条件：" + "、".join(missing)],
                           warnings=["没有生成或回退到 synthetic data。"], evidence=[{"synthetic_fallback": False, "missing": missing}])
        if request["optimization_policy"].get("mode") != "real_data":
            return _result(skill_id, started, status="blocked", limitations=["工业 Optimization Executor 只接受 real_data 模式。"],
                           warnings=["synthetic benchmark 必须通过独立显式入口请求。"], evidence=[{"synthetic_fallback": False}])
        def frame(value):
            data = value.copy() if isinstance(value, pd.DataFrame) else pd.read_csv(value)
            if "timestamp" in data.columns:
                data["timestamp"] = pd.to_datetime(data["timestamp"], errors="raise")
                data = data.set_index("timestamp")
            return data
        training, validation, test = frame(request["training_data"]), frame(request["validation_data"]), frame(request["test_data"])
        segments = request["segments"] if isinstance(request["segments"], pd.DataFrame) else pd.DataFrame(request["segments"])
        model = request["model_artifact"]
        if isinstance(model, (str, Path)):
            model = json.loads(Path(model).read_text(encoding="utf-8"))
        run_dir = Path(runtime_context["output_dir"]) / "optimization"
        clean_dir = run_dir / "03_cleaning"
        clean_dir.mkdir(parents=True, exist_ok=True)
        validation.reset_index().to_csv(clean_dir / "validation.csv", index=False)
        test.reset_index().to_csv(clean_dir / "test.csv", index=False)
        (clean_dir / "split_manifest.json").write_text(json.dumps(request["frozen_split"], ensure_ascii=False, indent=2), encoding="utf-8")
        standard = runtime_context.get("state", {}).get("standardization") or inputs.get("snapshot", {}).get("results", {}).get("standardization", {})
        report, best_model = run_optimization_stage(
            training, segments, request["field_dictionary"], model, run_dir,
            int(request.get("max_lag", 60)), primary_output=request.get("primary_output") or standard.get("scenario", {}).get("primary_output"),
            model_outputs=[request.get("primary_output") or standard.get("scenario", {}).get("primary_output")],
            objective=request["objective"], bounds=request["bounds"], constraints=request["constraints"],
            search_space=request["search_space"], optimization_policy=request["optimization_policy"],
        )
        feasible = any(item.get("status") == "completed" and item.get("feasible") for item in report["iterations"])
        status = "success" if feasible else "partial"
        runtime_context.get("state", {}).update(optimization=report, modeling=best_model)
        evidence = {"test_used_for_search": False, "test_evaluation_count": 1, "synthetic_fallback": False,
                    "validation_target_hash": report.get("validation_target_hash"), "decision_variables": request["decision_variables"]}
        return _result(skill_id, started, status=status, capabilities=capability_ids,
            facts=[f"在真实训练/验证数据上评估 {len(report['iterations'])} 个候选，冻结赢家后测试一次。"],
            findings=[f"最优候选为第 {report['best_round']} 轮，验证得分 {report['best_score']}。"],
            limitations=[] if feasible else ["搜索完成，但没有候选满足显式可行性约束。"],
            metrics={"objective": report["objective"], "best_candidate": report["best_parameters"], "validation_scores": report["best_metrics"],
                     "test_score": best_model.get("metrics", {}).get("test", {}), "feasibility": feasible,
                     "constraints": request["constraints"]}, artifacts=list(report.get("artifacts", {}).values()), evidence=[evidence],
            warnings=[], trace=[{"step": "run_optimization_stage", **evidence, "status": status}])


class ReviewExecutor:
    skill_id = "review"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_review_stage
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        results = snapshot.get("results", {})
        standard = state.get("standardization") or results.get("standardization")
        cleaning = state.get("cleaning") or results.get("cleaning")
        modeling = state.get("modeling") or results.get("modeling")
        if not all((standard, cleaning, modeling)):
            return _result(skill_id, started, status="blocked", limitations=["缺少标准化、清洗或建模证据；评审没有触发重算。"])
        output = Path(runtime_context["output_dir"]) / "review"
        report = run_review_stage(standard, cleaning, modeling, output)
        state["review"] = report
        return _result(skill_id, started, capabilities=capability_ids, findings=[report["conclusion"]],
                       limitations=list(report.get("blockers", [])), metrics={"passed": report.get("passed"), "deployment_readiness": report.get("deployment_readiness")},
                       artifacts=[str(output / "06_review" / "agent_review.json")], evidence=[report.get("evidence", {})], warnings=report.get("warnings", []),
                       trace=[{"step": "review_existing_evidence", "recomputed": False, "status": "completed"}])


class ReportExecutor:
    skill_id = "report"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.report_service import render_execution_report
        started = perf_counter()
        try:
            report = render_execution_report(inputs["snapshot"], runtime_context.get("results", []), Path(runtime_context["output_dir"]) / "report")
        except ValueError as exc:
            return _result(skill_id, started, status="blocked", limitations=[str(exc)])
        return _result(skill_id, started, capabilities=capability_ids, facts=["报告仅格式化既有结果，没有重跑 Pipeline。"],
                       metrics={"title": report["title"], "sections": report["sections"]}, artifacts=[report["path"]],
                       evidence=[{"source_run": inputs["snapshot"].get("run_id"), "recomputed": False}],
                       trace=[{"step": "render_existing_results", "recomputed": False, "status": "completed"}])


class SimulationExecutor:
    skill_id = "simulation"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        """Generate a deterministic, downloadable dynamic-process CSV without a pipeline fallback."""
        started = perf_counter()
        params = inputs.get("parameters", {})
        rows = max(150, min(int(params.get("rows", 360)), 10_000))
        seed = int(params.get("seed", 20260912))
        rng = random.Random(seed)
        scenario = data_context.get("detected_scene") or task_spec.get("scenario") or "generic_process"
        output = Path(runtime_context["output_dir"]) / "simulation" / f"{scenario}_simulation.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        y = 50.0
        start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "manipulated_input", "disturbance", "process_output", "quality_flag"])
            for index in range(rows):
                block = (index // max(30, rows // 6)) % 4
                manipulated = 40 + (0, 8, -5, 4)[block] + 2 * math.sin(index / 17) + rng.gauss(0, .25)
                disturbance = 20 + 1.5 * math.sin(index / 31) + rng.gauss(0, .18)
                target = 48 + .42 * manipulated - .18 * disturbance
                y += .13 * (target - y) + rng.gauss(0, .12)
                anomalous = index > 0 and index % 127 == 0
                writer.writerow([(start_at + timedelta(minutes=index)).isoformat(), round(manipulated, 5), round(disturbance, 5), round(y + (6 if anomalous else 0), 5), "injected_anomaly" if anomalous else "ok"])
        return _result(skill_id, started, capabilities=capability_ids, facts=[f"已生成 {rows} 行可复现工业动态数据。"],
                       metrics={"rows": rows, "seed": seed, "scenario": scenario, "synthetic": True},
                       artifacts=[str(output)], evidence=[{"generator": "deterministic_first_order_process_v1", "seed": seed}],
                       warnings=["该产物明确标记为仿真数据，不代表现场测量。"],
                       trace=[{"step": "generate_dynamic_csv", "status": "completed"}])


class VisualizationExecutor:
    skill_id = "visualization"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        started = perf_counter()
        snapshot = inputs.get("snapshot", {})
        preview = snapshot.get("results", {}).get("modeling", {}).get("prediction_preview", [])
        if not preview:
            path = _artifact_path(snapshot, "test_predictions_csv")
            if path:
                preview = pd.read_csv(path).head(240).to_dict("records")
        points = [(float(row.get("y_true")), float(row.get("y_pred"))) for row in preview
                  if pd.notna(row.get("y_true")) and pd.notna(row.get("y_pred"))]
        if not points:
            return _result(skill_id, started, status="blocked", limitations=["缺少真实预测序列，未生成占位图。"])
        values = [value for point in points for value in point]
        low, high = min(values), max(values)
        span = high - low or 1.0
        width, height, margin = 900, 360, 42
        def polyline(index):
            return " ".join(f"{margin + i * (width - 2 * margin) / max(1, len(points)-1):.1f},{height-margin-(point[index]-low)*(height-2*margin)/span:.1f}" for i, point in enumerate(points))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
               '<rect width="100%" height="100%" fill="white"/><text x="42" y="24" font-family="sans-serif" font-size="16">Measured vs predicted</text>'
               f'<polyline fill="none" stroke="#172033" stroke-width="2" points="{polyline(0)}"/>'
               f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{polyline(1)}"/>'
               '<text x="690" y="24" fill="#172033" font-family="sans-serif" font-size="11">measured</text>'
               '<text x="770" y="24" fill="#2563eb" font-family="sans-serif" font-size="11">predicted</text></svg>')
        output = Path(runtime_context["output_dir"]) / "visualization" / "prediction_comparison.svg"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(svg, encoding="utf-8")
        return _result(skill_id, started, capabilities=capability_ids, facts=[f"由真实预测产物生成 {len(points)} 点工程曲线。"],
                       metrics={"point_count": len(points), "source": "pipeline_prediction"}, artifacts=[str(output)],
                       evidence=[snapshot.get("run_id")], trace=[{"step": "render_prediction_svg", "status": "completed"}])


class ExperimentExecutor:
    skill_id = "experiment"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import list_runs
        started = perf_counter()
        scenario = data_context.get("detected_scene")
        runs = list_runs(limit=100, scenario_id=scenario) if scenario else list_runs(limit=100)
        comparable = []
        for run in runs:
            model = run.get("results", {}).get("modeling", {})
            test = model.get("metrics", {}).get("test", {})
            if test.get("r2") is not None:
                comparable.append({"run_id": run.get("run_id"), "created_at": run.get("created_at"),
                                   "model_family": model.get("config", {}).get("family"), "r2": test.get("r2"),
                                   "rmse": test.get("rmse"), "mae": test.get("mae"),
                                   "parameters": model.get("config", {})})
        if not comparable:
            return _result(skill_id, started, status="blocked", limitations=["运行注册表中没有带独立测试指标的真实实验。"])
        best = max(comparable, key=lambda item: float(item["r2"]))
        output = Path(runtime_context["output_dir"]) / "experiment" / "comparison.json"
        payload = {"source": "pipeline_run_registry", "synthetic": False, "run_count": len(comparable), "best_run": best, "runs": comparable}
        _write_json(output, payload)
        return _result(skill_id, started, capabilities=capability_ids, findings=[f"按独立测试 R²，当前最佳实验为 {best['run_id']}。"],
                       metrics={"run_count": len(comparable), "best_run_id": best["run_id"], "best_r2": best["r2"]},
                       artifacts=[str(output)], evidence=[item["run_id"] for item in comparable],
                       trace=[{"step": "compare_registered_runs", "status": "completed"}])


class SupervisionExecutor:
    skill_id = "supervision"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        started = perf_counter()
        prior = runtime_context.get("results", [])
        snapshot = inputs.get("snapshot", {})
        failed = [row.get("skill_id") for row in prior if row.get("status") in {"failed", "blocked", "unavailable"}]
        stages = snapshot.get("stages", [])
        failed_stages = [row.get("key") for row in stages if row.get("status") == "failed"]
        actions = []
        for name in failed + failed_stages:
            actions.append({"target": name, "action": "retry_after_input_repair", "max_attempts": 1})
        decision = "replan" if actions else "continue"
        output = Path(runtime_context["output_dir"]) / "supervision" / "replan.json"
        payload = {"automatic_replanning": True, "decision": decision, "failed_targets": failed + failed_stages, "actions": actions}
        _write_json(output, payload)
        return _result(skill_id, started, capabilities=capability_ids, findings=["检测到失败并生成重规划动作。" if actions else "所有已执行节点通过监督门禁。"],
                       metrics=payload, artifacts=[str(output)], evidence=[snapshot.get("run_id")],
                       trace=[{"step": "inspect_execution_results", "status": "completed", "decision": decision}])
