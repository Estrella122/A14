from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from django.conf import settings


EXECUTOR_VERSION = "1.1.0"


def _variable_spec(dictionary: list[dict[str, Any]], columns: list[str]) -> dict[str, dict[str, Any]]:
    role_map = {"controlled": "output", "quality": "quality", "manipulated": "input", "disturbance": "input", "state": "input"}
    spec = {}
    for field in dictionary:
        name = field.get("standard_name")
        if name not in columns or field.get("data_type") not in {"float", "integer"} or field.get("role") not in role_map:
            continue
        lower, upper = field.get("lower_bound"), field.get("upper_bound")
        lower = float(lower) if lower is not None else -1e18
        upper = float(upper) if upper is not None else 1e18
        spec[name] = {"role": role_map[field["role"]], "unit": field.get("unit") or "", "min": lower, "max": upper,
                      "max_step": max((upper - lower) * .2, 1e-6)}
    return spec


def select_modeling_windows(segments: pd.DataFrame, top_k: int = 5, strict_first: bool = True, policy=None) -> pd.DataFrame:
    if segments.empty:
        return segments
    if policy and policy.get("sparse_output") and "output_observations" in segments:
        segments = segments[segments["output_observations"] >= policy.get("minimum_output_observations", 1)]
    chosen = segments[segments["level"] == "优质动态段"].head(top_k) if strict_first else segments.iloc[0:0]
    if chosen.empty and policy and policy.get("allow_usable_fallback"):
        chosen = segments[segments["level"].isin(["优质动态段", "可用数据段"])].head(top_k)
    if chosen.empty:
        chosen = segments.head(min(top_k, len(segments)))
    return chosen


def select_modeling_rows(train_data: pd.DataFrame, segments: pd.DataFrame, top_k: int = 5, strict_first: bool = True, policy=None) -> pd.DataFrame:
    if segments.empty:
        return train_data.iloc[0:0]
    chosen = select_modeling_windows(segments, top_k, strict_first, policy)
    pieces = [train_data.loc[pd.Timestamp(row.start_time):pd.Timestamp(row.end_time)] for row in chosen.itertuples(index=False)]
    return pd.concat(pieces).loc[lambda frame: ~frame.index.duplicated()].sort_index() if pieces else train_data.iloc[0:0]


def run_segmentation_stage(train_data: pd.DataFrame, field_dictionary: list[dict[str, Any]], output_dir: Path,
                           *, upstream_run_id: str = "", split_version: str = "chronological_60_20_20_v2",
                           window_length: int | None = None, step: int | None = None, primary_output: str | None = None,
                           policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run selection on the frozen training partition only."""
    from .algorithm_policy import resolve_algorithm_policy, PolicyError
    request = {"selection": policy or {}}
    if window_length is not None:
        request["window_length"] = window_length
    if step is not None:
        request["step"] = step
    try:
        policy = resolve_algorithm_policy(requested=request)["effective_parameters"]["selection"]
    except PolicyError as exc:
        return {"status": "blocked", "missing": [], "warnings": [], "limitations": [str(exc)],
                "ignored_or_rejected_parameters": exc.rejected, "evidence": []}
    window_length, step = policy["window_samples"], policy["step_samples"]
    missing = []
    if train_data is None or train_data.empty:
        missing.append("cleaned_training_data")
    if train_data is None or not isinstance(train_data.index, pd.DatetimeIndex):
        missing.append("valid_time_axis")
    numeric = list(train_data.select_dtypes(include="number").columns) if train_data is not None else []
    if len(numeric) < 2:
        missing.append("numeric_process_fields")
    if window_length < 15 or train_data is not None and len(train_data) < window_length:
        missing.append("sufficient_samples/window_length")
    if step < 1 or step > window_length:
        missing.append("valid_step")
    if not split_version:
        missing.append("frozen_split")
    if missing:
        return {"status": "blocked", "missing": missing, "warnings": [], "limitations": ["缺少分段前置条件：" + "、".join(missing)], "evidence": []}

    spec = _variable_spec(field_dictionary, list(train_data.columns))
    if not any(item["role"] == "output" for item in spec.values()):
        return {"status": "blocked", "missing": ["controlled_output"], "warnings": [], "limitations": ["字段字典没有可用于分段评分的输出变量。"], "evidence": []}
    module_dir = Path(settings.BASE_DIR) / "integrations" / "data_cleaning" / "src"
    sys.path.insert(0, str(module_dir))
    try:
        from data_cleaning_agent import DataCleaningSelectionAgent
        agent = DataCleaningSelectionAgent(
            spec, primary_output=primary_output, selection_window=window_length,
            selection_step=step, selection_policy=policy,
        )
        segments = agent.select_dynamic_segments(train_data)
        snr_rows = pd.DataFrame(agent.snr_evidence)
    finally:
        if str(module_dir) in sys.path:
            sys.path.remove(str(module_dir))
    active_policy = policy or {"strict_score": 80, "usable_score": 60, "snr_db": 10}
    strict_selected = segments[segments["level"] == "优质动态段"] if not segments.empty else segments
    usable_score = float(active_policy.get("usable_score", 60))
    usable_selected = segments[segments["level"].isin(["优质动态段", "可用数据段"])] if not segments.empty else segments
    relaxed_acceptance = bool(active_policy.get("allow_usable_fallback")) and strict_selected.empty and not usable_selected.empty
    selected = usable_selected if relaxed_acceptance else strict_selected
    modeling_top_k = max(1, int(active_policy.get("modeling_top_k", 5)))
    eligible = segments
    if active_policy.get("sparse_output") and not segments.empty:
        eligible = segments[segments["output_observations"] >= active_policy["minimum_output_observations"]]
    actual = select_modeling_windows(selected if not selected.empty else eligible, modeling_top_k, strict_first=False)
    modeling = select_modeling_rows(train_data, actual, modeling_top_k, strict_first=False)
    acceptance_mode = "engineering_usable" if relaxed_acceptance else "strict" if not strict_selected.empty else "highest_score_fallback" if not actual.empty else "insufficient_data"
    selection_reason = {"strict": "严格评分与SNR门槛通过", "engineering_usable": "有效策略允许接纳可用候选", "highest_score_fallback": "沿用最高分候选兜底；不代表工程可用", "insufficient_data": "无满足目标观测条件的候选"}[acceptance_mode]
    dynamic = strict_selected
    steady = segments[segments["segment_score"] < usable_score] if not segments.empty else segments
    selected_ids = [str(value) for value in modeling.index]
    provenance = {"upstream_cleaning_run": upstream_run_id, "split_version": split_version,
                  "segmentation_policy": active_policy,
                  "acceptance_mode": acceptance_mode,
                  "modeling_top_k": modeling_top_k,
                  "window_length": window_length, "step": step, "source_columns": list(train_data.columns),
                  "executed_at": datetime.now().astimezone().isoformat(timespec="seconds"), "executor_version": EXECUTOR_VERSION,
                  "selection_scope": "training_only", "validation_rows_read": 0, "test_rows_read": 0}
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {"snr_csv": output_dir / "snr_estimates.csv", "segments_csv": output_dir / "selected_dynamic_segments.csv",
             "segment_scores_csv": output_dir / "segment_scores.csv", "modeling_csv": output_dir / "modeling_dataset.csv",
             "segmentation_report_json": output_dir / "segmentation_report.json"}
    snr_rows.to_csv(paths["snr_csv"], index=False, encoding="utf-8-sig")
    selected.to_csv(paths["segments_csv"], index=False, encoding="utf-8-sig")
    segments.to_csv(paths["segment_scores_csv"], index=False, encoding="utf-8-sig")
    modeling.reset_index().to_csv(paths["modeling_csv"], index=False, encoding="utf-8-sig")
    warnings = [] if acceptance_mode == "strict" else [selection_reason]
    if relaxed_acceptance:
        warnings.append("小样本自适应策略已启用：严格优质段不足，工程可用段已进入后续辨识链。")
    report = {"status": "success" if not modeling.empty else "blocked", "segments": segments.to_dict("records"), "steady_segments": steady.to_dict("records"),
              "dynamic_segments": dynamic.to_dict("records"), "usable_segments": usable_selected.to_dict("records"), "snr_metrics": {"method": "robust_second_difference_white_noise_proxy", "rows": len(snr_rows)},
              "segment_scores": segments.to_dict("records"), "selected_segments": selected.to_dict("records"),
              "actual_selected_segments": actual.to_dict("records"), "selected_row_ids": selected_ids, "metrics": {"candidate_count": len(segments), "dynamic_count": len(dynamic),
              "steady_count": len(steady), "strict_selected_count": len(strict_selected), "usable_count": len(usable_selected),
              "selected_count": len(selected), "selected_row_count": len(modeling),
              "actual_selected_window_count": len(actual), "effective_top_k": modeling_top_k,
              "selection_reason": selection_reason,
              "target_observation_count": int(modeling[primary_output].notna().sum()) if primary_output in modeling else None, "relaxed_acceptance": relaxed_acceptance,
              "acceptance_mode": acceptance_mode},
              "warnings": warnings, "limitations": ["SNR 是白噪声假设下的代理估计；重叠窗口不等于独立激励。可用数据段是质量接纳，不等于动态激励已证实。",
              "工程可用段按分层阈值接纳，结论需结合独立测试和模型评审指标解释。"] if relaxed_acceptance else ["SNR 是白噪声假设下的代理估计；重叠窗口不等于独立激励。可用数据段是质量接纳，不等于动态激励已证实。"],
              "evidence": [provenance], "provenance": provenance, "artifacts": {key: str(path) for key, path in paths.items()}}
    paths["segmentation_report_json"].write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report["_segments_frame"] = segments
    report["_modeling_frame"] = modeling
    return report
