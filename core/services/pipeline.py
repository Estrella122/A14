from __future__ import annotations

import json
import hashlib
import importlib.metadata
import math
import shutil
import sys
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pandas as pd
from django.conf import settings


BASE_DIR = Path(settings.BASE_DIR)
INTEGRATIONS_DIR = BASE_DIR / "integrations"
RUNS_DIR = BASE_DIR / "runtime" / "pipeline_runs"
LATEST_PATH = RUNS_DIR / "latest.json"
MAX_PREVIEW_ROWS = 12
_RUN_LOCK = threading.Lock()


STAGES = [
    ("standardization", "字段标准化"),
    ("cleaning", "数据清洗"),
    ("selection", "动态优选"),
    ("modeling", "系统辨识"),
    ("optimization", "闭环寻优"),
    ("review", "Agent 评审"),
    ("report", "分析报告"),
]


class PipelineError(RuntimeError):
    pass


@contextmanager
def _module_path(path: Path) -> Iterator[None]:
    value = str(path)
    sys.path.insert(0, value)
    try:
        yield
    finally:
        if value in sys.path:
            sys.path.remove(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if value is pd.NA or (not isinstance(value, (dict, list, tuple, str)) and pd.isna(value)):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise PipelineError(f"CSV 无法读取：{last_error}")


def _set_stage(snapshot: dict[str, Any], run_dir: Path, key: str, status: str, message: str = "") -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for stage in snapshot["stages"]:
        if stage["key"] == key:
            stage["status"] = status
            stage["message"] = message
            if status == "running":
                stage["started_at"] = now
            if status in {"completed", "failed", "skipped"}:
                stage["finished_at"] = now
            break
    snapshot["current_stage"] = key
    snapshot["updated_at"] = now
    _write_json(run_dir / "snapshot.json", snapshot)


def _artifact(run_dir: Path, path: Path) -> str:
    return str(path.relative_to(run_dir))


def _standardize(source_path: Path, run_dir: Path, scenario_id: str, instruction: str, overrides: dict[str, str] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    module_dir = INTEGRATIONS_DIR / "standardization"
    with _module_path(module_dir):
        from standard_agent import ScenarioRepository, StandardizationAgent

        frame = _read_csv(source_path)
        repository = ScenarioRepository()
        result = StandardizationAgent(repository).standardize(
            frame,
            scenario_id=scenario_id or "auto",
            instruction=instruction,
            overrides=overrides,
        )
        effective_scene_id = result["scenario"]["scenario_id"]
        effective_template = repository.get(effective_scene_id)
        template_path = repository.root / "scenarios" / effective_scene_id / "template.json"
        loaded_scenes = [template.scenario_id for template in repository.list()]
        point_semantics_scenes = sorted({
            row.get("point_resolution", {}).get("scene")
            for row in result["mapping"]["mappings"]
            if row.get("point_resolution", {}).get("scene")
        })
        recognition_required_features = list(effective_template.recognition["required_features"])
        modeling_required_features = [
            field.standard_name for field in effective_template.fields if field.required
        ]

    output_path = run_dir / "02_standardization" / "standardized.csv"
    mapping_path = run_dir / "02_standardization" / "mapping_report.csv"
    report_path = run_dir / "02_standardization" / "standardization_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result["standardized_data"].to_csv(output_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(result["mapping"]["mappings"]).to_csv(mapping_path, index=False, encoding="utf-8-sig")
    report = {
        "source_row_count": len(frame),
        "source_column_count": len(frame.columns),
        "scenario": result["scenario"],
        "detection": result["detection"],
        "mapping": result["mapping"],
        "conversions": result["conversions"],
        "issues": result["issues"],
        "data_decision": result["data_decision"],
        "schema_validation": result["schema_validation"],
        "dictionary": result["dictionary"],
        "runtime_trace": {
            "scene_id": scenario_id or "auto",
            "agent_scene": result["detection"]["auto_selected"]["scenario_id"],
            "selected_scene": result["detection"]["selected"]["scenario_id"],
            "final_scene": result["detection"].get("final_scene"),
            "status": result["detection"].get("status"),
            "confidence": result["detection"].get("confidence"),
            "confidence_margin": result["detection"].get("auto_confidence_margin"),
            "registry_scene_id": effective_scene_id,
            "loaded_scenes": loaded_scenes,
            "point_semantics_scenes": point_semantics_scenes,
            "template_path": str(template_path),
            "required_features_source": f"{template_path.parent / 'fields.csv'}#required=true",
            "required_features": modeling_required_features,
            "recognition_required_features_source": f"{template_path}#recognition.required_features",
            "recognition_required_features": recognition_required_features,
            "modeling_gate": {
                "scene_id": effective_scene_id,
                "template_path": str(template_path),
                "required_features_source": f"{template_path.parent / 'fields.csv'}#required=true",
                "required_features": modeling_required_features,
            },
        },
        "preview": result["standardized_data"].head(MAX_PREVIEW_ROWS).where(pd.notna(result["standardized_data"]), None).to_dict("records"),
    }
    _write_json(report_path, report)
    report["artifacts"] = {
        "standardized_csv": _artifact(run_dir, output_path),
        "mapping_csv": _artifact(run_dir, mapping_path),
        "report_json": _artifact(run_dir, report_path),
    }
    return result["standardized_data"], report


def _cleaning_spec(dictionary: list[dict[str, Any]], columns: list[str]) -> dict[str, dict[str, Any]]:
    role_map = {
        "controlled": "output",
        "quality": "quality",
        "manipulated": "input",
        "disturbance": "input",
        "state": "input",
    }
    spec = {}
    for field in dictionary:
        name = field["standard_name"]
        if name not in columns or field.get("data_type") not in {"float", "integer"}:
            continue
        role = role_map.get(field.get("role"))
        if not role:
            continue
        lower = field.get("lower_bound")
        upper = field.get("upper_bound")
        lower = float(lower) if lower is not None else -1e18
        upper = float(upper) if upper is not None else 1e18
        physical_range = upper - lower if math.isfinite(upper - lower) else 1000.0
        spec[name] = {
            "role": role,
            "unit": field.get("unit") or "",
            "min": lower,
            "max": upper,
            "max_step": max(physical_range * 0.2, 1e-6),
        }
    return spec


def _effective_max_lag(requested: int, scenario: dict[str, Any]) -> int:
    delay = scenario.get("measurement_delay_minutes")
    if isinstance(delay, dict):
        try:
            return max(int(requested), int(delay.get("max") or 0))
        except (TypeError, ValueError):
            return int(requested)
    return int(requested)


def _select_modeling_rows(cleaned: pd.DataFrame, segments: pd.DataFrame, top_k: int = 5, strict_first: bool = True) -> pd.DataFrame:
    if segments.empty:
        return cleaned
    chosen = segments[segments["level"] == "优质动态段"].head(top_k) if strict_first else segments.iloc[0:0]
    if chosen.empty:
        chosen = segments.head(min(top_k, len(segments)))
    pieces = []
    for row in chosen.itertuples(index=False):
        pieces.append(cleaned.loc[pd.Timestamp(row.start_time):pd.Timestamp(row.end_time)])
    if not pieces:
        return cleaned
    return pd.concat(pieces).loc[lambda frame: ~frame.index.duplicated()].sort_index()


def _clean(
    standardized: pd.DataFrame,
    dictionary: list[dict[str, Any]],
    run_dir: Path,
    resample_rule: str,
    max_lag_for_split: int = 60,
    primary_output: str | None = None,
    selection_window: int = 30,
    selection_step: int = 15,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    module_dir = INTEGRATIONS_DIR / "data_cleaning" / "src"
    with _module_path(module_dir):
        from data_cleaning_agent import DataCleaningSelectionAgent

        spec = _cleaning_spec(dictionary, list(standardized.columns))
        if "timestamp" not in standardized.columns:
            raise PipelineError("标准化结果缺少 timestamp，无法执行时序清洗。")
        if not any(item["role"] == "output" for item in spec.values()):
            raise PipelineError("没有识别到可用于建模的被控输出变量。")
        agent = DataCleaningSelectionAgent(
            spec,
            resample_rule=resample_rule,
            primary_output=primary_output,
            selection_window=selection_window,
            selection_step=selection_step,
        )
        # Freeze the chronological partitions before cleaning or scoring.
        ordered = standardized.sort_values("timestamp").reset_index(drop=True)
        requested_rule = resample_rule
        intervals = pd.to_datetime(ordered.timestamp).diff().dt.total_seconds()
        native_seconds = float(intervals[intervals > 0].median())
        if math.isfinite(native_seconds) and pd.Timedelta(resample_rule).total_seconds() < native_seconds:
            resample_rule = f"{native_seconds:g}s"
        n = len(ordered)
        if n < 150:
            raise PipelineError("至少需要150行数据以保留独立训练、验证和测试分区。")
        boundaries = (int(n * .6), int(n * .8))
        parts, train_segments, report = {}, None, None
        for label, part in (("train", ordered.iloc[:boundaries[0]]),
                            ("validation", ordered.iloc[boundaries[0]:boundaries[1]]),
                            ("test", ordered.iloc[boundaries[1]:])):
            part_agent = DataCleaningSelectionAgent(
                spec,
                resample_rule=resample_rule,
                primary_output=primary_output,
                selection_window=selection_window,
                selection_step=selection_step,
            )
            aligned = part_agent.align_timestamp(part)
            processed = part_agent.process_missing_values(aligned)
            frame = part_agent.detect_and_repair_anomalies(processed)
            if parts:
                # A bin ending at the prior partition boundary belongs only to it.
                frame = frame.loc[frame.index > list(parts.values())[-1].index[-1]]
            parts[label] = frame
            if label == "train":
                train_segments = part_agent.select_dynamic_segments(frame)
                report = part_agent.build_quality_report(aligned, frame, train_segments)
                snr_evidence = part_agent.snr_evidence
        if requested_rule != resample_rule:
            report["logs"].append(f"请求周期{requested_rule}短于原始典型周期，实际采用{resample_rule}，避免插值制造输出真值。")
        report["config"] = {"requested_resample_rule": requested_rule, "resample_rule": resample_rule}
        segments = train_segments
        cleaned = pd.concat(parts.values()).sort_index()
        split_dir = run_dir / "03_cleaning"
        split_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(snr_evidence).to_csv(split_dir / "snr_estimates.csv", index=False, encoding="utf-8-sig")
        for label, frame in parts.items():
            frame.reset_index().to_csv(split_dir / f"{label}.csv", index=False, encoding="utf-8-sig")
        seconds = pd.Timedelta(resample_rule).total_seconds()
        guard = max(4, min(2 * int(max_lag_for_split) + 3, min(len(parts["validation"]), len(parts["test"])) // 3))
        split = {"protocol": "chronological_60_20_20_v2", "guard_samples": guard, "seconds": seconds,
                 "partitions": {k: {"rows": len(v), "start": str(v.index[0]), "end": str(v.index[-1])} for k,v in parts.items()}}
        _write_json(split_dir / "split_manifest.json", split)
        report["snr"] = {"method": "robust_second_difference_white_noise_proxy", "threshold_db": 10,
            "status": "estimated", "scope": "training_windows_only", "calibrated": False,
            "assumptions": "局部平滑信号与加性白噪声；有色噪声、曲率及量化会影响估计",
            "passed_windows": int((segments["level"] == "优质动态段").sum()),
            "window_overlap": f"{selection_window}点窗口，{selection_step}点步长；重叠窗口不是独立激励次数"}
        report["split"] = split

    clean_dir = run_dir / "03_cleaning"
    cleaned_path = clean_dir / "cleaned.csv"
    segments_path = clean_dir / "selected_dynamic_segments.csv"
    modeling_path = clean_dir / "modeling_dataset.csv"
    report_path = clean_dir / "quality_report.json"
    clean_dir.mkdir(parents=True, exist_ok=True)
    cleaned.reset_index().to_csv(cleaned_path, index=False, encoding="utf-8-sig")
    segments.to_csv(segments_path, index=False, encoding="utf-8-sig")
    modeling = _select_modeling_rows(parts["train"], segments)
    modeling.reset_index().to_csv(modeling_path, index=False, encoding="utf-8-sig")
    output_field = next((item for item in dictionary if item.get("standard_name") == primary_output and item["standard_name"] in cleaned.columns), None)
    if output_field is None:
        output_field = next((item for item in dictionary if item.get("role") == "controlled" and item["standard_name"] in cleaned.columns), None)
    input_field = next((item for item in dictionary if item.get("role") == "manipulated" and item["standard_name"] in cleaned.columns), None)
    if input_field is None:
        input_field = next((item for item in dictionary if item.get("role") == "disturbance" and item["standard_name"] in cleaned.columns), None)
    timeseries_preview = {"input": None, "output": None, "points": []}
    if input_field and output_field and len(cleaned):
        sample_step = max(1, math.ceil(len(cleaned) / 120))
        sampled = cleaned.iloc[::sample_step]
        if sampled.index[-1] != cleaned.index[-1]:
            sampled = pd.concat([sampled, cleaned.iloc[[-1]]])
        input_name = input_field["standard_name"]
        output_name = output_field["standard_name"]
        timeseries_preview = {
            "input": {
                "name": input_name,
                "label": input_field.get("display_name") or input_name,
                "unit": input_field.get("unit") or "",
                "role": input_field.get("role"),
            },
            "output": {
                "name": output_name,
                "label": output_field.get("display_name") or output_name,
                "unit": output_field.get("unit") or "",
                "role": output_field.get("role"),
            },
            "points": [
                {
                    "timestamp": timestamp.isoformat(),
                    "input": row.get(input_name),
                    "output": row.get(output_name),
                }
                for timestamp, row in sampled.iterrows()
            ],
        }
    report.update({
        "variable_spec": spec,
        "cleaned_row_count": len(cleaned),
        "modeling_row_count": len(modeling),
        "segments_preview": segments.head(MAX_PREVIEW_ROWS).to_dict("records"),
        "timeseries_preview": timeseries_preview,
    })
    _write_json(report_path, report)
    report["artifacts"] = {
        "snr_csv": "03_cleaning/snr_estimates.csv",
        "split_json": "03_cleaning/split_manifest.json",
        "cleaned_csv": _artifact(run_dir, cleaned_path),
        "segments_csv": _artifact(run_dir, segments_path),
        "modeling_csv": _artifact(run_dir, modeling_path),
        "report_json": _artifact(run_dir, report_path),
    }
    return modeling, segments, report


def _model(
    modeling: pd.DataFrame,
    dictionary: list[dict[str, Any]],
    run_dir: Path,
    max_lag: int,
    modeling_path: Path | None = None,
    output_dir: Path | None = None,
    primary_output: str | None = None,
) -> dict[str, Any]:
    numeric = set(modeling.select_dtypes(include="number").columns)
    fields = {item["standard_name"]: item for item in dictionary}
    output_col = primary_output if primary_output in numeric else None
    if output_col is None:
        output_col = next((name for name in numeric if fields.get(name, {}).get("role") == "controlled"), None)
    if output_col is None:
        raise PipelineError("无法从标准字段中确定系统辨识输出变量。")
    input_roles = {"manipulated", "disturbance", "state"}
    input_cols = [
        name for name in modeling.columns
        if name in numeric
        and fields.get(name, {}).get("role") in input_roles
        and modeling[name].notna().sum() >= 20
        and modeling[name].nunique(dropna=True) >= 4
        and float(modeling[name].std(skipna=True) or 0) > 1e-12
    ]
    if not input_cols:
        input_cols = [name for name in modeling.columns if name in numeric and name != output_col]
    if not input_cols:
        raise PipelineError("没有足够的数值输入变量用于系统辨识。")

    modeling_path = modeling_path or run_dir / "03_cleaning" / "modeling_dataset.csv"
    output_dir = output_dir or run_dir / "04_modeling"
    module_dir = INTEGRATIONS_DIR / "identification"
    with _module_path(module_dir):
        from validated_modeling import run_validated_modeling

        split = _read_json(run_dir / "03_cleaning" / "split_manifest.json")
        result = run_validated_modeling(
            input_csv=modeling_path, output_col=output_col, input_cols=input_cols,
            output_dir=output_dir, validation_csv=run_dir / "03_cleaning" / "validation.csv",
            guard=split["guard_samples"], seconds=split["seconds"], max_lag=max_lag,
        )

    metrics_path = output_dir / "03_system_identification" / "model_metrics.json"
    delays_path = output_dir / "01_time_delay" / "delay_estimates.csv"
    correlation_path = output_dir / "02_collinearity" / "correlation_matrix.csv"
    vif_path = output_dir / "02_collinearity" / "vif_table.csv"
    recommendation_path = output_dir / "02_collinearity" / "variable_recommendation.json"
    metrics = _read_json(metrics_path, {})
    delays = _read_csv(delays_path).head(MAX_PREVIEW_ROWS).to_dict("records") if delays_path.exists() else []
    correlation = _read_csv(correlation_path) if correlation_path.exists() else pd.DataFrame()
    if not correlation.empty:
        correlation = correlation.rename(columns={correlation.columns[0]: "variable"})
        correlation_labels = correlation["variable"].astype(str).head(7).tolist()
        correlation_matrix = correlation.loc[: len(correlation_labels) - 1, correlation_labels].fillna(0).astype(float).values.tolist()
    else:
        correlation_labels, correlation_matrix = [], []
    vif = _read_csv(vif_path).head(MAX_PREVIEW_ROWS).to_dict("records") if vif_path.exists() else []
    recommendations = _read_json(recommendation_path, {})
    report = {
        "output_col": output_col,
        "training_rows": len(modeling),
        "diagnostics": result.get("diagnostics", {}),
        "response_analysis": result.get("response_analysis", {}),
        "order_search": result.get("order_search", []),
        "fitted_inputs": result.get("fitted_inputs", []),
        "modeling_path": _artifact(run_dir, modeling_path),
        "output_dir": str(output_dir.relative_to(run_dir)),
        "input_cols": input_cols,
        "selected_inputs": result.get("selected_inputs_after_collinearity", []),
        "config": result.get("config", {}),
        "metrics": metrics,
        "lags": delays,
        "collinearity": {
            "labels": correlation_labels,
            "matrix": correlation_matrix,
            "vif": vif,
            "recommendations": recommendations,
        },
        "artifacts": {
            "summary_json": _artifact(run_dir, output_dir / "pipeline_summary.json"),
            "final_vif_csv": _artifact(run_dir, output_dir / "02_collinearity" / "final_vif_table.csv"),
            "modeling_csv": _artifact(run_dir, modeling_path),
            "diagnostics_json": _artifact(run_dir, output_dir / "03_system_identification" / "diagnostics.json"),
            "response_analysis_json": _artifact(run_dir, output_dir / "03_system_identification" / "response_analysis.json"),
            "order_search_json": _artifact(run_dir, output_dir / "03_system_identification" / "order_search.json"),
            "fitted_state_json": _artifact(run_dir, output_dir / "03_system_identification" / "fitted_state.json"),
            "metrics_json": _artifact(run_dir, metrics_path),
            "delays_csv": _artifact(run_dir, delays_path),
        },
    }
    _write_json(output_dir / "api_report.json", report)
    return report


def _candidate_score(metrics: dict[str, Any], coverage: float) -> float:
    r2 = float(metrics.get("r2") or 0)
    rmse = max(float(metrics.get("rmse") or 0), 0)
    r2_score = max(0.0, min(1.0, (r2 + 0.2) / 1.2))
    error_score = 1.0 / (1.0 + rmse)
    return round(100 * (0.68 * r2_score + 0.17 * error_score + 0.15 * max(0.0, min(coverage, 1.0))), 3)


def _optimize_real_data(
    cleaned: pd.DataFrame,
    segments: pd.DataFrame,
    dictionary: list[dict[str, Any]],
    baseline_model: dict[str, Any],
    run_dir: Path,
    max_lag: int,
    primary_output: str | None = None,
    model_outputs: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    exploration_candidates = [
        {"round": 1, "top_k": 5, "max_lag": max_lag, "label": "基线策略"},
        {"round": 2, "top_k": 3, "max_lag": max(10, max_lag // 2), "label": "精炼动态段"},
        {"round": 3, "top_k": 8, "max_lag": min(600, max_lag + max(10, max_lag // 2)), "label": "扩大覆盖与时滞"},
        {"round": 4, "top_k": 6, "max_lag": max(10, round(max_lag * 0.75)), "label": "中等覆盖短时滞"},
        {"round": 5, "top_k": 10, "max_lag": min(600, max_lag * 2), "label": "高覆盖长时滞"},
        {"round": 6, "top_k": 4, "max_lag": min(600, max(10, round(max_lag * 1.25))), "label": "低覆盖稳健辨识"},
    ]
    iterations = []
    best_model = baseline_model

    def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
        try:
            # Every round uses exactly its declared selection, including round 1.
            data = _select_modeling_rows(cleaned, segments, top_k=candidate["top_k"], strict_first=True)
            candidate_dir = run_dir / "05_optimization" / f"candidate_{candidate['round']:02d}"
            candidate_path = candidate_dir / "modeling_dataset.csv"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            data.reset_index().to_csv(candidate_path, index=False, encoding="utf-8-sig")
            model = _model(data, dictionary, run_dir, candidate["max_lag"],
                           modeling_path=candidate_path, output_dir=candidate_dir / "modeling",
                           primary_output=primary_output)
            row_count = len(data)
            test = model.get("metrics", {}).get("validation", {})
            coverage = row_count / max(len(cleaned), 1)
            iteration = {
                **candidate,
                "status": "completed",
                "row_count": row_count,
                "evaluation_split": "validation",
                "evaluation_target_hash": model["diagnostics"]["evaluation_target_hash"],
                "validation_samples": test.get("n_samples"),
                "modeling_csv": model["modeling_path"],
                "effective_max_lag": model["config"]["max_lag"],
                "coverage": round(coverage, 4),
                "r2": float(test.get("r2") or 0),
                "rmse": float(test.get("rmse") or 0),
                "mae": float(test.get("mae") or 0),
                "score": _candidate_score(test, coverage),
                "model": model,
            }
        except Exception as exc:
            iteration = {**candidate, "status": "failed", "error": str(exc), "score": -1.0}
        iterations.append(iteration)
        return iteration

    for candidate in exploration_candidates:
        evaluate(candidate)

    min_rounds = 8
    max_rounds = 16
    patience = 3
    min_improvement = 0.2
    no_improvement_rounds = 0
    early_stopped = False
    stop_reason = ""
    explored = [item for item in iterations if item["status"] == "completed"]
    if explored:
        initial_anchor = max(explored, key=lambda item: item["score"])
        best_so_far = initial_anchor
        refinement_step = max(10, max_lag // 4)
        seen = {(item["top_k"], item["max_lag"]) for item in iterations}
        directions = [(2, -1), (-1, 1), (3, -2), (-2, 2), (1, -3), (-3, 3), (4, -1), (-4, 1), (2, -2), (-2, 2)]
        for round_number in range(7, max_rounds + 1):
            anchor = initial_anchor if round_number <= 8 else best_so_far
            top_delta, lag_direction = directions[round_number - 7]
            candidate_top_k = min(20, max(2, anchor["top_k"] + top_delta))
            candidate_max_lag = min(600, max(10, anchor["max_lag"] + lag_direction * refinement_step))
            while (candidate_top_k, candidate_max_lag) in seen:
                candidate_top_k = 2 + (candidate_top_k - 1) % 19
                candidate_max_lag = min(600, candidate_max_lag + 5)
            seen.add((candidate_top_k, candidate_max_lag))
            suffix = "A" if round_number == 7 else "B" if round_number == 8 else f"R{round_number}"
            previous_best_score = float(best_so_far["score"])
            iteration = evaluate({
                "round": round_number,
                "top_k": candidate_top_k,
                "max_lag": candidate_max_lag,
                "label": f"围绕第{anchor['round']}轮反馈精搜{suffix}",
            })
            if iteration["status"] == "completed" and float(iteration["score"]) > previous_best_score:
                best_so_far = iteration
            improvement = float(best_so_far["score"]) - previous_best_score
            no_improvement_rounds = 0 if improvement >= min_improvement else no_improvement_rounds + 1
            feasible = float(best_so_far.get("r2") or 0) >= 0 and float(best_so_far.get("coverage") or 0) >= 0.05
            if round_number >= min_rounds and feasible and no_improvement_rounds >= patience:
                early_stopped = True
                stop_reason = f"最优候选通过可行性门槛，连续{no_improvement_rounds}轮综合分改善低于{min_improvement}分"
                break

    completed = [item for item in iterations if item["status"] == "completed"]
    if not completed:
        _write_json(run_dir / "05_optimization/optimization_report.json", {"status": "failed", "iterations": iterations})
        reasons = list(dict.fromkeys(item.get("error", "未知错误") for item in iterations))
        raise PipelineError("所有候选均失败：" + "；".join(reasons[:3]))
    best = max(completed, key=lambda item: item["score"])
    if not stop_reason:
        best_feasible = float(best.get("r2") or 0) >= 0 and float(best.get("coverage") or 0) >= 0.05
        stop_reason = f"达到最大轮次{max_rounds}轮；{'已获得可行候选' if best_feasible else '最优候选仍未通过R²与覆盖率门槛，建议返回数据优选或辨识阶段'}"
    hashes = {item["evaluation_target_hash"] for item in completed}
    if len(hashes) != 1:
        raise PipelineError("候选验证目标不一致，拒绝比较。")
    best_model = best["model"]
    # Test is touched only after the winner and all hyperparameters are frozen.
    with _module_path(INTEGRATIONS_DIR / "identification"):
        from validated_modeling import finalize_test
        metrics, diagnostics = finalize_test(run_dir / best_model["output_dir"], run_dir / "03_cleaning" / "test.csv")
    prediction_path = run_dir / best_model["output_dir"] / "03_system_identification/test_prediction_residuals.csv"
    prediction = _read_csv(prediction_path)
    step = max(1, math.ceil(len(prediction) / 150))
    best_model["prediction_preview"] = prediction.iloc[::step].to_dict("records")
    best_model["artifacts"]["test_predictions_csv"] = _artifact(run_dir, prediction_path)
    best_model["artifacts"]["test_residuals_csv"] = _artifact(run_dir, run_dir / best_model["output_dir"] / "03_system_identification/test_residual_autocorrelation.csv")
    best_model["metrics"] = metrics
    best_model["diagnostics"] = diagnostics
    requested_outputs = list(dict.fromkeys(model_outputs or [primary_output]))
    secondary_models = []
    for output_name in requested_outputs:
        if not output_name or output_name == best_model.get("output_col"):
            continue
        try:
            secondary_dir = run_dir / "05_optimization" / "mimo_outputs" / output_name
            secondary = _model(
                _read_csv(run_dir / best_model["modeling_path"]), dictionary, run_dir,
                best["max_lag"], modeling_path=run_dir / best_model["modeling_path"],
                output_dir=secondary_dir, primary_output=output_name,
            )
            secondary_metrics, secondary_diagnostics = finalize_test(secondary_dir, run_dir / "03_cleaning" / "test.csv")
            secondary.update({"metrics": secondary_metrics, "diagnostics": secondary_diagnostics, "status": "completed"})
            _write_json(secondary_dir / "api_report.json", secondary)
            secondary_models.append(secondary)
        except (PipelineError, ValueError, KeyError, OSError) as exc:
            secondary_models.append({"output_col": output_name, "status": "failed", "error": str(exc)})
    best_model["mimo"] = {
        "method": "shared-input multi-output ARX model bank",
        "outputs": [{"output_col": best_model.get("output_col"), "status": "completed", "primary": True,
                     "family": best_model.get("config", {}).get("family"),
                     "fitted_inputs": best_model.get("fitted_inputs", []),
                     "test": best_model.get("metrics", {}).get("test"),
                     "response": best_model.get("diagnostics", {}).get("test", {}),
                     "response_analysis": best_model.get("response_analysis", {})}]
                   + [{"output_col": item.get("output_col"), "status": item.get("status"),
                       "family": item.get("config", {}).get("family"),
                       "fitted_inputs": item.get("fitted_inputs", []),
                       "test": item.get("metrics", {}).get("test"),
                       "response": item.get("diagnostics", {}).get("test", {}),
                       "response_analysis": item.get("response_analysis", {}),
                       "error": item.get("error")}
                      for item in secondary_models],
        "completed_outputs": 1 + sum(item.get("status") == "completed" for item in secondary_models),
        "response_ready_outputs": sum(
            item.get("status") == "completed"
            and item.get("config", {}).get("family") == "ARX"
            and bool(item.get("fitted_inputs"))
            and bool(item.get("response_analysis", {}).get("channels"))
            for item in [best_model, *secondary_models]
        ),
        "requested_outputs": requested_outputs,
    }
    _write_json(run_dir / best_model["output_dir"] / "api_report.json", best_model)
    public_iterations = [{key: value for key, value in item.items() if key != "model"} for item in iterations]
    report = {
        "method": "real_data_space_filling_and_feedback_search",
        "evaluation_split": "validation",
        "coverage_denominator": "training_partition_rows",
        "validation_target_hash": best["evaluation_target_hash"],
        "test_evaluations": 1,
        "best_training_rows": best["row_count"],
        "search_strategy": "前6轮覆盖动态段数量与时滞空间，第7轮起围绕当前最优反馈精搜；最少8轮、最多16轮，自适应收敛",
        "stopping": {
            "min_rounds": min_rounds,
            "max_rounds": max_rounds,
            "patience": patience,
            "min_score_improvement": min_improvement,
            "executed_rounds": len(iterations),
            "no_improvement_rounds": no_improvement_rounds,
            "early_stopped": early_stopped,
            "stop_reason": stop_reason,
        },
        "objective": "0.68×R²得分 + 0.17×误差得分 + 0.15×数据覆盖率",
        "iterations": public_iterations,
        "best_round": best["round"],
        "best_label": best["label"],
        "best_score": best["score"],
        "best_parameters": {"top_k": best["top_k"], "max_lag": best["max_lag"]},
        "best_metrics": {"r2": best["r2"], "rmse": best["rmse"], "mae": best["mae"], "coverage": best["coverage"]},
    }
    report_path = run_dir / "05_optimization" / "optimization_report.json"
    _write_json(report_path, report)
    report["artifacts"] = {"optimization_json": _artifact(run_dir, report_path)}
    return report, best_model


def _review(standardization: dict[str, Any], cleaning: dict[str, Any], modeling: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    test_metrics = modeling.get("metrics", {}).get("test", {})
    r2 = float(test_metrics.get("r2") or 0)
    quality = float(cleaning.get("overall_score") or 0)
    decision = standardization.get("data_decision", {}).get("status", "review")
    blockers = []
    if decision == "reject":
        blockers.append("字段标准化结果被拒绝")
    if quality < 60:
        blockers.append("数据质量评分低于60")
    if r2 < 0:
        blockers.append("验证集R²小于0，模型不具备预测价值")
    diagnostics = modeling.get("diagnostics", {})
    test_diag = diagnostics.get("test", {})
    improvement = test_diag.get("rmse_improvement_over_persistence_pct")
    if improvement is None:
        blockers.append("未提供独立测试集与持续值基线对比")
    elif improvement < 1:
        blockers.append("独立测试相较持续值基线的RMSE改善不足1%")
    if modeling.get("config", {}).get("family") == "AR":
        blockers.append("仅自回归基线胜出，尚未证明外部输入到输出的动态模型")
    if diagnostics.get("stable_ar_poles") is not True:
        blockers.append("未通过AR极点稳定性检查")
    multi = test_diag.get("multi_step", {})
    if not multi.get("metrics") or multi["metrics"]["rmse"] >= multi.get("persistence", {}).get("rmse", 0):
        blockers.append("10步预测未优于同跨度持续值基线或证据不足")
    simulation = test_diag.get("free_simulation", {})
    if simulation.get("diverged") or not simulation.get("metrics") or simulation["metrics"].get("r2", -1) < 0:
        blockers.append("自由仿真未通过有效性检查")
    passed = not blockers and decision != "reject" and quality >= 60 and r2 >= 0
    required_coverage = float(standardization.get("mapping", {}).get("required_coverage") or 0)
    residual = test_diag.get("residual", {})
    acf = residual.get("acf_max_abs")
    acf_bound = residual.get("heuristic_95pct_bound")
    offline_gates = [
        {"id": "field_contract", "passed": decision != "reject" and required_coverage >= 1,
         "evidence": f"required_coverage={required_coverage:.1%}, decision={decision}"},
        {"id": "data_quality", "passed": quality >= 60, "evidence": f"quality_score={quality:.2f}"},
        {"id": "independent_test", "passed": r2 >= 0 and improvement is not None and improvement >= 1,
         "evidence": f"test_r2={r2:.4f}, persistence_improvement_pct={improvement}"},
        {"id": "dynamic_validity", "passed": diagnostics.get("stable_ar_poles") is True and bool(multi.get("metrics"))
         and bool(simulation.get("metrics")) and not simulation.get("diverged"),
         "evidence": "稳定极点、10步预测和自由仿真必须同时有效"},
    ]
    requested_model_outputs = standardization.get("scenario", {}).get("model_outputs") or []
    if len(requested_model_outputs) > 1:
        mimo = modeling.get("mimo", {})
        offline_gates.append({
            "id": "multi_output_identification",
            "passed": mimo.get("response_ready_outputs") == len(requested_model_outputs),
            "evidence": (
                f"completed_outputs={mimo.get('completed_outputs', 0)}/{len(requested_model_outputs)}, "
                f"arx_response_ready={mimo.get('response_ready_outputs', 0)}/{len(requested_model_outputs)}"
            ),
        })
    soft_sensor_gates = offline_gates + [
        {"id": "external_inputs_used", "passed": modeling.get("config", {}).get("family") == "ARX" and bool(modeling.get("fitted_inputs")),
         "evidence": f"family={modeling.get('config', {}).get('family')}, fitted_inputs={modeling.get('fitted_inputs', [])}"},
        {"id": "residual_whiteness", "passed": bool(acf is not None and acf_bound is not None and acf <= acf_bound),
         "evidence": f"acf_max_abs={acf}, heuristic_95pct_bound={acf_bound}; 上线前仍需正式显著性检验"},
        {"id": "verified_physical_time", "passed": standardization.get("scenario", {}).get("time_axis_type", "wall_clock") == "wall_clock",
         "evidence": f"time_axis_type={standardization.get('scenario', {}).get('time_axis_type', 'wall_clock')}"},
        {"id": "external_operating_period", "passed": False,
         "evidence": "需提供不同时间段或不同工况的冻结外部验证集"},
        {"id": "measurement_traceability", "passed": False,
         "evidence": "需提供目标化验/仪表方法、采样延迟、校准与质量标志"},
        {"id": "online_monitoring", "passed": False,
         "evidence": "需定义输入越界、漂移、缺测、模型失效监测及回退策略"},
    ]
    closed_loop_gates = soft_sensor_gates + [
        {"id": "causal_control_validation", "passed": False,
         "evidence": "需通过受控阶跃/历史准实验确认操纵量到输出的因果方向与有效时滞"},
        {"id": "constraints_and_interlocks", "passed": False,
         "evidence": "需由工艺与自控专业确认约束、联锁独立性、速率限制和异常回退"},
        {"id": "shadow_and_operator_acceptance", "passed": False,
         "evidence": "需完成影子运行、操作员验收和分阶段投运记录"},
    ]
    readiness = {
        "offline_model": {"passed": all(g["passed"] for g in offline_gates), "gates": offline_gates},
        "soft_sensor_candidate": {"passed": all(g["passed"] for g in soft_sensor_gates), "gates": soft_sensor_gates},
        "closed_loop_candidate": {"passed": all(g["passed"] for g in closed_loop_gates), "gates": closed_loop_gates},
        "policy": "离线通过只表示可继续工程验证；软测量与闭环必须分别通过全部准入门。",
    }
    time_axis_warning = []
    if standardization.get("scenario", {}).get("time_axis_type") == "ordered_samples":
        time_axis_warning.append("公开数据未提供真实日历时间和采样周期；派生时间轴只保存顺序，时滞单位只能解释为采样点。")
    report = {
        "passed": passed,
        "conclusion": "通过离线候选模型门槛，仍需外部工况验证" if passed else "未通过，需要复核或调整数据",
        "blockers": blockers,
        "warnings": [item["message"] for item in standardization.get("issues", []) if item.get("level") == "warning"] + time_axis_warning + [
            "SNR为二阶差分白噪声假设下的估计值，未经过仪表噪声标定。",
            "共同验证集用于结构与参数选择；最终测试只评估一次。",
            "残差仅提供ACF诊断，未完成白噪声显著性检验或输入残差独立性检验。"],
        "evidence": {
            "scenario": standardization.get("scenario", {}).get("scenario_name"),
            "standardization_decision": decision,
            "quality_score": quality,
            "selected_segments": cleaning.get("selected_segment_count", 0),
            "test_r2": r2,
            "test_rmse": test_metrics.get("rmse"),
        },
        "deployment_readiness": readiness,
    }
    _write_json(run_dir / "06_review" / "agent_review.json", report)
    return report


def _analysis_report(snapshot, standardization, cleaning, modeling, review, run_dir):
    optimization = snapshot["results"]["optimization"]
    metrics = modeling.get("metrics", {})
    diagnostics = modeling.get("diagnostics", {})
    td = diagnostics.get("test", {})
    lines = ["# 工业时序数据智能优选与系统辨识分析报告", "",
        f"任务：`{snapshot['run_id']}`；文件：{snapshot['original_name']}；场景：{standardization.get('scenario', {}).get('scenario_name', '未知')}",
        f"结论：**{review['conclusion']}**", "",
        "## 总控与子Agent执行链", "",
        "实际执行由本地流水线完成：字段标准化 → 分区与因果清洗 → 训练段SNR估计与评分 → 候选时滞/共线性/结构训练 → 共同验证集寻优 → 独立测试 → 评审。Skill界面展示规划与对应证据读取，不代表每个标签各启动一次算法。", "",
        "## 数据与SNR", "",
        ("时间轴为公开样本顺序派生轴，物理采样周期未知；所有时滞只表示采样点数。" if standardization.get("scenario", {}).get("time_axis_type") == "ordered_samples" else "时间轴按源数据日历时间解释。"),
        f"原始规整数据 {cleaning['cleaned_row_count']} 行；训练分区内达标窗口 {cleaning['selected_segment_count']} 个；选中候选训练数据 {modeling['training_rows']} 行。",
        "30点窗口、15点步长，有重叠。达标条件为动态综合分≥80且SNR代理估计≥10 dB；不表示独立激励次数或已证明持续激励。",
        "SNR使用稳健二阶差分估计白噪声方差，以总方差扣除噪声方差估计信号功率；局部曲率、有色噪声和量化会破坏假设。无有效估计的窗口不能标为高SNR。", "",
        "## 验证协议", "",
        "按原始时间先固定60%训练、20%验证、20%测试。各分区分别清洗，仅有限前向填充输入；异常/缺失输出不作为真值。输入筛选、时滞、共线性、系数均只学习训练分区。结构与寻优共用相同验证目标；选定后只测试一次。",
        "滞后特征在连续段内生成，只使用历史输入输出，禁止负向移位。10步预测与自由仿真以观测输入为条件，不能直接等同于未来输入未知的在线预测。",
        f"分区清单：`03_cleaning/split_manifest.json`；覆盖率分母为训练分区行数。", "",
        "## 时滞与共线性", "",
        "|输入|因果时滞/点|训练相关系数|搜索边界|", "|---|---:|---:|---|"]
    for row in modeling.get("lags", []):
        lines.append(f"|{row['input']}|{row['delay_samples']}|{row['correlation']:.4f}|{row.get('boundary_hit', False)}|")
    lines += ["", "时滞是训练段相关性估计，不是因果证明；命中搜索上界应复核。",
        f"诊断保留：{', '.join(modeling['selected_inputs'])}；最终{modeling['config']['family']}模型实际输入：{', '.join(modeling.get('fitted_inputs', [])) or '无，仅自回归输出'}。", "",
        "## 闭环寻优过程", "", "这里的闭环指离线预处理—建模—验证反馈搜索。最佳仅指本次候选范围内验证得分最高。",
        "|轮次|top_k|最大时滞请求|实际训练行|验证R²|验证RMSE|训练覆盖率|得分|", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in optimization['iterations']:
        if row['status'] == 'completed':
            lines.append(f"|{row['round']}|{row['top_k']}|{row['max_lag']}|{row['row_count']}|{row['r2']:.4f}|{row['rmse']:.4f}|{row['coverage']:.1%}|{row['score']:.3f}|")
        else: lines.append(f"|{row['round']}|{row['top_k']}|{row['max_lag']}|失败：{row.get('error')}|||||")
    lines += ["", f"选中第 {optimization['best_round']} 轮；验证得分 {optimization['best_score']}。", "",
        "## 系统辨识结果", "", f"模型：{modeling['config']['family']}，阶次 {modeling['config']['output_order']}；阶次1/2/3及AR/ARX在共同验证集比较。",
        "|数据分区|有效样本|R²|RMSE|MAE|", "|---|---:|---:|---:|---:|"]
    for label, metric in metrics.items():
        lines.append(f"|{label}|{metric['n_samples']:.0f}|{metric['r2']:.5f}|{metric['rmse']:.5f}|{metric['mae']:.5f}|")
    baseline = td.get('persistence', {})
    lines += ["", f"独立测试持续值基线：R²={baseline.get('r2')}，RMSE={baseline.get('rmse')}。",
        f"单步RMSE相对基线改善：{td.get('rmse_improvement_over_persistence_pct')}%。",
        f"10步结果：{json.dumps(td.get('multi_step', {}), ensure_ascii=False)}",
        f"自由仿真：{json.dumps(td.get('free_simulation', {}), ensure_ascii=False)}",
        f"AR极点稳定：{diagnostics.get('stable_ar_poles')}；残差诊断：{json.dumps(td.get('residual', {}), ensure_ascii=False)}", "",
        "## 评审与证据缺口", ""]
    lines += [f"- {message}" for message in review.get('blockers', []) + review.get('warnings', [])]
    lines += ["", "## 上线准入结论", "",
              "|级别|结论|未通过项|", "|---|---|---|"]
    for level, assessment in review.get("deployment_readiness", {}).items():
        if level == "policy" or not isinstance(assessment, dict):
            continue
        failed = [gate["id"] for gate in assessment.get("gates", []) if not gate.get("passed")]
        lines.append(f"|{level}|{'通过' if assessment.get('passed') else '阻断'}|{', '.join(failed) or '无'}|")
    lines += ["", review.get("deployment_readiness", {}).get("policy", "")]
    lines += ["", "## 交付产物", ""]
    lines += [f"- {key}：`{path}`" for key, path in snapshot['artifacts'].items()]
    report_path = run_dir / '07_delivery' / 'analysis_report.md'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return {'title': '工业时序数据智能优选与系统辨识分析报告', 'format': 'markdown',
            'path': _artifact(run_dir, report_path), 'summary': review['conclusion']}


def run_pipeline(source_path: Path, original_name: str, scenario_id: str = "auto", project_scene: str = "", instruction: str = "", resample_rule: str = "10s", max_lag: int = 60, stop_after: str = "report", overrides: dict[str, str] | None = None) -> dict[str, Any]:
    if stop_after not in dict(STAGES):
        raise PipelineError("未知的流水线停止阶段。")
    with _RUN_LOCK:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8]
        run_dir = RUNS_DIR / run_id
        input_dir = run_dir / "01_input"
        input_dir.mkdir(parents=True, exist_ok=True)
        stored_path = input_dir / "source.csv"
        source_path.replace(stored_path)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        snapshot = {
            "run_id": run_id,
            "status": "running",
            "current_stage": "standardization",
            "original_name": original_name,
            "project_scene": project_scene or None,
            "scenario_request": scenario_id or "auto",
            "instruction": instruction,
            "mapping_overrides": overrides or {},
            "created_at": now,
            "updated_at": now,
            "stages": [{"key": key, "label": label, "status": "pending", "message": ""} for key, label in STAGES],
            "artifacts": {"source_csv": "01_input/source.csv"},
            "results": {},
        }
        _write_json(run_dir / "snapshot.json", snapshot)
        _write_json(LATEST_PATH, {"run_id": run_id})

        def finish_requested_stage(stage: str) -> bool:
            if stop_after != stage:
                return False
            for node in snapshot["stages"]:
                if node["status"] == "pending":
                    node.update(status="skipped", message="不在本次请求范围内")
            snapshot.update(status="completed", current_stage="completed",
                            execution_scope={"stop_after": stop_after},
                            updated_at=datetime.now().astimezone().isoformat(timespec="seconds"))
            _write_json(run_dir / "snapshot.json", snapshot)
            return True

        current_stage = "standardization"
        try:
            _set_stage(snapshot, run_dir, current_stage, "running", "正在识别场景、字段和单位")
            _, standardization = _standardize(stored_path, run_dir, scenario_id, instruction, overrides)
            effective_max_lag = _effective_max_lag(max_lag, standardization.get("scenario", {}))
            if effective_max_lag != max_lag:
                snapshot["effective_max_lag"] = effective_max_lag
                standardization["scenario"]["effective_max_lag"] = effective_max_lag
                standardization["scenario"]["requested_max_lag"] = max_lag
            snapshot["results"]["standardization"] = standardization
            snapshot["runtime_trace"] = standardization.get("runtime_trace", {})
            snapshot["artifacts"].update(standardization["artifacts"])
            _set_stage(snapshot, run_dir, current_stage, "completed", "字段标准化完成")
            if finish_requested_stage("standardization"):
                return snapshot
            decision = standardization.get("data_decision", {})
            requires_mapping_review = bool(
                standardization.get("detection", {}).get("is_ambiguous")
                or standardization.get("mapping", {}).get("review_count")
                or standardization.get("mapping", {}).get("missing_required")
            )
            if decision.get("status") == "reject" or requires_mapping_review:
                reason = "；".join(decision.get("reasons", [])) or "字段标准化未通过"
                for stage in snapshot["stages"]:
                    if stage["status"] == "pending":
                        stage.update(status="skipped", message="字段标准化未通过，未执行下游阶段")
                snapshot.update(
                    status="needs_review",
                    current_stage="standardization",
                    execution_scope={"stop_after": "standardization", "reason": f"data_decision_{decision.get('status', 'unknown')}"},
                    updated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                )
                snapshot["error"] = None
                snapshot["review_required"] = {
                    "stage": "standardization",
                    "message": reason,
                    "reasons": decision.get("reasons", []),
                }
                _write_json(run_dir / "snapshot.json", snapshot)
                return snapshot

            current_stage = "cleaning"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在对齐时间戳并修复缺失、异常值")
            standardized = _read_csv(run_dir / standardization["artifacts"]["standardized_csv"])
            primary_output = standardization.get("scenario", {}).get("primary_output")
            model_outputs = standardization.get("scenario", {}).get("model_outputs") or [primary_output]
            modeling_data, segments, cleaning = _clean(
                standardized, standardization["dictionary"], run_dir, resample_rule, effective_max_lag,
                primary_output=primary_output,
                selection_window=standardization.get("scenario", {}).get("selection_window_samples", 30),
                selection_step=standardization.get("scenario", {}).get("selection_step_samples", 15),
            )
            snapshot["results"]["cleaning"] = cleaning
            snapshot["artifacts"].update(cleaning["artifacts"])
            _set_stage(snapshot, run_dir, current_stage, "completed", f"质量评分 {cleaning['overall_score']}")
            if finish_requested_stage("cleaning"):
                return snapshot

            current_stage = "selection"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在冻结优质动态数据段")
            snapshot["results"]["selection"] = {
                "selected_segment_count": cleaning["selected_segment_count"],
                "modeling_row_count": len(modeling_data),
                "segments": cleaning["segments_preview"],
            }
            _set_stage(snapshot, run_dir, current_stage, "completed", f"建模数据 {len(modeling_data)} 行")
            if finish_requested_stage("selection"):
                return snapshot

            current_stage = "modeling"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在执行时滞、共线性和ARX辨识")
            # Actual fitting is performed per candidate in the optimization stage.
            modeling = {"status": "pending_candidate_search", "artifacts": {}}
            snapshot["results"]["modeling"] = modeling
            snapshot["artifacts"].update(modeling["artifacts"])
            _set_stage(snapshot, run_dir, current_stage, "completed", "已冻结分区，辨识随候选搜索执行")
            if stop_after == "modeling":
                modeling = _model(modeling_data, standardization["dictionary"], run_dir, effective_max_lag,
                                  primary_output=primary_output)
                snapshot["results"]["modeling"] = modeling
                snapshot["artifacts"].update(modeling["artifacts"])
                _set_stage(snapshot, run_dir, current_stage, "completed", "系统辨识完成；未执行候选寻优")
                if finish_requested_stage("modeling"):
                    return snapshot

            current_stage = "optimization"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在基于真实数据比较多组候选策略")
            cleaned_frame = _read_csv(run_dir / "03_cleaning" / "train.csv")
            cleaned_frame["timestamp"] = pd.to_datetime(cleaned_frame["timestamp"], errors="raise")
            cleaned_frame = cleaned_frame.set_index("timestamp")
            optimization, modeling = _optimize_real_data(
                cleaned_frame,
                segments,
                standardization["dictionary"],
                modeling,
                run_dir,
                effective_max_lag,
                primary_output=primary_output,
                model_outputs=model_outputs,
            )
            cleaning["modeling_row_count"] = optimization["best_training_rows"]
            cleaning["artifacts"]["modeling_csv"] = modeling["modeling_path"]
            snapshot["results"]["selection"]["modeling_row_count"] = optimization["best_training_rows"]
            _write_json(run_dir / "03_cleaning" / "quality_report.json", cleaning)
            snapshot["results"]["optimization"] = optimization
            snapshot["results"]["modeling"] = modeling
            snapshot["artifacts"].update(optimization["artifacts"])
            snapshot["artifacts"].update(modeling["artifacts"])
            _set_stage(
                snapshot,
                run_dir,
                current_stage,
                "completed",
                f"第 {optimization['best_round']} 轮最优，综合得分 {optimization['best_score']}",
            )
            if finish_requested_stage("optimization"):
                return snapshot

            current_stage = "review"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在核对字段、质量与模型证据")
            review = _review(standardization, cleaning, modeling, run_dir)
            snapshot["results"]["review"] = review
            snapshot["artifacts"]["review_json"] = "06_review/agent_review.json"
            _set_stage(snapshot, run_dir, current_stage, "completed", review["conclusion"])
            if finish_requested_stage("review"):
                return snapshot

            current_stage = "report"
            _set_stage(snapshot, run_dir, current_stage, "running", "正在汇总子Agent证据并生成报告")
            report = _analysis_report(snapshot, standardization, cleaning, modeling, review, run_dir)
            snapshot["results"]["report"] = report
            snapshot["artifacts"]["analysis_report_md"] = report["path"]
            _set_stage(snapshot, run_dir, current_stage, "completed", "Markdown分析报告已生成")
            paths = {key: run_dir / relative for key, relative in snapshot["artifacts"].items()}
            code_paths = list((BASE_DIR / "core").rglob("*.py")) + list((BASE_DIR / "integrations" / "identification").glob("*.py")) + [BASE_DIR / "integrations/data_cleaning/src/data_cleaning_agent.py"]
            audit = {"protocol": "chronological_60_20_20_v2", "source_run": run_id,
                "artifacts": {key: {"path": str(path.relative_to(run_dir)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for key, path in paths.items() if path.is_file()},
                "code_sha256": {str(path.relative_to(BASE_DIR)): hashlib.sha256(path.read_bytes()).hexdigest() for path in code_paths},
                "dependencies": {name: importlib.metadata.version(name) for name in ("Django", "numpy", "pandas")},
                "deterministic": True, "selection_scope": "validation_only", "test_evaluations": 1}
            _write_json(run_dir / "07_delivery/audit_manifest.json", audit)
            snapshot["artifacts"]["audit_json"] = "07_delivery/audit_manifest.json"
            snapshot["results"]["audit"] = {"artifact_count": len(audit["artifacts"]), "code_file_count": len(code_paths), "hash_algorithm": "sha256"}
            snapshot["status"] = "completed"
            snapshot["current_stage"] = "completed"
            snapshot["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            _write_json(run_dir / "snapshot.json", snapshot)
            return snapshot
        except Exception as exc:
            _set_stage(snapshot, run_dir, current_stage, "failed", str(exc))
            snapshot["status"] = "failed"
            snapshot["error"] = {"stage": current_stage, "message": str(exc), "type": type(exc).__name__}
            for stage in snapshot["stages"]:
                if stage["status"] == "pending":
                    stage["status"] = "skipped"
                    stage["message"] = "前序阶段失败，未执行"
            _write_json(run_dir / "snapshot.json", snapshot)
            raise PipelineError(str(exc)) from exc


def get_run(run_id: str | None = None) -> dict[str, Any] | None:
    if not run_id:
        run_id = (_read_json(LATEST_PATH, {}) or {}).get("run_id")
    if not run_id or not run_id.replace("_", "").isalnum():
        return None
    return _read_json(RUNS_DIR / run_id / "snapshot.json")


def list_runs(limit: int = 100, scenario_id: str | None = None) -> list[dict[str, Any]]:
    """Return newest pipeline snapshots for experiment tracking."""
    if not RUNS_DIR.exists():
        return []
    snapshots = []
    paths = sorted(RUNS_DIR.glob("*/snapshot.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in paths:
        snapshot = _read_json(path)
        if not snapshot:
            continue
        actual_scenario = (
            snapshot.get("results", {}).get("standardization", {}).get("scenario", {}).get("scenario_id")
            or snapshot.get("scenario_request")
        )
        if scenario_id and actual_scenario != scenario_id:
            continue
        snapshots.append(snapshot)
        if len(snapshots) >= max(1, min(int(limit), 500)):
            break
    return snapshots


def resolve_artifact(run_id: str, artifact_key: str) -> tuple[Path, str]:
    snapshot = get_run(run_id)
    if not snapshot:
        raise PipelineError("运行任务不存在。")
    relative = snapshot.get("artifacts", {}).get(artifact_key)
    if not relative:
        raise PipelineError("该任务没有请求的产物。")
    run_dir = (RUNS_DIR / run_id).resolve()
    path = (run_dir / relative).resolve()
    if run_dir not in path.parents or not path.is_file():
        raise PipelineError("产物路径无效。")
    return path, path.name


def rerun_pipeline(run_id: str, resample_rule: str = "10s", max_lag: int = 60, stop_after: str = "report", scenario_id: str | None = None, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    previous = get_run(run_id)
    if not previous:
        raise PipelineError("运行任务不存在。")
    source, _ = resolve_artifact(run_id, "source_csv")
    handle = tempfile.NamedTemporaryFile(prefix="processpilot_rerun_", suffix=".csv", delete=False)
    temporary = Path(handle.name)
    handle.close()
    shutil.copy2(source, temporary)
    return run_pipeline(
        temporary,
        original_name=previous.get("original_name", "source.csv"),
        scenario_id=scenario_id or previous.get("scenario_request", "auto"),
        project_scene=previous.get("project_scene") or "",
        instruction=previous.get("instruction", ""),
        resample_rule=resample_rule,
        max_lag=max_lag,
        stop_after=stop_after,
        overrides=overrides if overrides is not None else previous.get("mapping_overrides", {}),
    )
