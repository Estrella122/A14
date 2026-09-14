"""Standalone executor for the industrial-analysis Skill."""
from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd


def _conclusion(statement: str, confidence: float | str, evidence: list[Any]) -> dict[str, Any]:
    return {"statement": statement, "confidence": confidence, "evidence": evidence}


def _numeric(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)


def _confidence(context: dict[str, Any], sample_count: int) -> float:
    values = [value for value in (context.get("mapping_confidence"), context.get("scene_confidence")) if isinstance(value, (int, float))]
    base = min(values) if values else 0.7
    return round(max(0.2, min(0.98, base * min(1.0, sample_count / 100))), 3)


def _matching_columns(columns, *terms: str) -> list[str]:
    return [str(column) for column in columns if any(term in str(column).lower() for term in terms)]


def _role_columns(context: dict[str, Any], role_names: set[str]) -> list[str]:
    roles = context.get("variable_roles") or {}
    if isinstance(roles, dict):
        return [str(name) for role in role_names for name in roles.get(role, [])]
    return []


def execute_capability(capability_id: str, frame: pd.DataFrame, context: dict[str, Any], policy: dict[str, Any], shared: dict[str, Any] | None = None) -> dict[str, Any]:
    started = perf_counter()
    shared = shared if shared is not None else {}
    numeric = shared.get("numeric")
    if numeric is None:
        numeric = shared["numeric"] = _numeric(frame)
    confidence = _confidence(context, len(frame))
    facts: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    evidence = [f"rows:{len(frame)}", f"numeric_fields:{len(numeric.columns)}", f"method:{capability_id.lower()}"]

    if capability_id == "DATA_PROFILING":
        metrics = {"row_count": len(frame), "column_count": len(frame.columns), "numeric_field_count": len(numeric.columns)}
        facts.append(_conclusion(f"数据包含 {len(frame)} 行、{len(frame.columns)} 列，其中 {len(numeric.columns)} 个数值字段。", confidence, evidence))
    elif capability_id in {"DATA_QUALITY_ANALYSIS", "MISSING_DATA_ANALYSIS"}:
        rates = shared.get("missing_rates")
        if rates is None:
            rates = shared["missing_rates"] = frame.isna().mean().sort_values(ascending=False)
        worst = str(rates.index[0]) if len(rates) else None
        worst_rate = float(rates.iloc[0]) if len(rates) else 0.0
        metrics = {"overall_missing_rate": float(frame.isna().sum().sum() / max(1, frame.size)), "worst_field": worst, "worst_missing_rate": worst_rate}
        findings.append(_conclusion(f"缺失率最高字段为 {worst or '无'}，缺失率 {worst_rate:.2%}。", confidence, evidence + [f"missing_rate:{worst_rate:.6f}"]))
    elif capability_id in {"TREND_ANALYSIS", "TIME_SERIES_ANALYSIS"}:
        slopes = {}
        x = np.arange(len(frame), dtype=float)
        for column in numeric.columns:
            series = numeric[column].dropna()
            if len(series) >= 2:
                slopes[str(column)] = float(np.polyfit(x[series.index.to_numpy()] if np.issubdtype(series.index.dtype, np.integer) else np.arange(len(series)), series.to_numpy(), 1)[0])
        strongest = max(slopes, key=lambda key: abs(slopes[key])) if slopes else None
        metrics = {"slopes": slopes, "strongest_trend_field": strongest}
        findings.append(_conclusion(f"绝对趋势最明显的字段为 {strongest or '无可分析字段'}。", confidence, evidence + ([f"slope:{slopes[strongest]:.6g}"] if strongest else [])))
    elif capability_id == "ANOMALY_DETECTION":
        threshold = float(policy.get("anomaly_zscore_threshold", 3.0))
        mean = numeric.mean()
        std = numeric.std(ddof=0).replace(0, np.nan)
        scores = ((numeric - mean) / std).abs()
        counts = (scores > threshold).sum().sort_values(ascending=False)
        total = int((scores > threshold).sum().sum())
        metrics = {"method": "absolute_zscore", "threshold": threshold, "anomaly_count": total, "field_counts": {str(k): int(v) for k, v in counts.items()}}
        findings.append(_conclusion(f"按 |z|>{threshold:g} 检出 {total} 个统计异常点。", confidence, evidence + [f"threshold:{threshold:g}", f"anomaly_count:{total}"]))
        if policy.get("single_anomaly_is_not_equipment_failure", True):
            limitations.append(_conclusion("统计异常不等同于设备故障，需要结合工况和仪表证据复核。", "high", ["evidence-rule:single-anomaly-is-not-equipment-failure"]))
    elif capability_id == "PROCESS_STABILITY":
        cv = {}
        drift = {}
        split = max(1, len(numeric) // 2)
        for column in numeric.columns:
            series = numeric[column].dropna()
            if len(series) < 4:
                continue
            cv[str(column)] = float(series.std(ddof=0) / max(abs(series.mean()), 1e-12))
            drift[str(column)] = float(series.iloc[split:].mean() - series.iloc[:split].mean()) if len(series) > split else 0.0
        unstable = max(cv, key=cv.get) if cv else None
        metrics = {"coefficient_of_variation": cv, "half_window_drift": drift, "least_stable_field": unstable}
        findings.append(_conclusion(f"相对波动最大的字段为 {unstable or '无可分析字段'}。", confidence, evidence + ([f"cv:{cv[unstable]:.6g}"] if unstable else [])))
    elif capability_id == "CORRELATION_ANALYSIS":
        usable = numeric.loc[:, numeric.nunique(dropna=True) > 1]
        correlation = shared.get("correlation")
        if correlation is None:
            correlation = shared["correlation"] = usable.corr().abs()
        pairs = []
        for i, left in enumerate(correlation.columns):
            for right in correlation.columns[i + 1:]:
                value = correlation.loc[left, right]
                if pd.notna(value):
                    pairs.append((str(left), str(right), float(value)))
        pairs.sort(key=lambda item: item[2], reverse=True)
        metrics = {"method": "pearson", "strongest_pairs": pairs[:8]}
        findings.append(_conclusion(f"最强线性相关变量对为 {pairs[0][0] + '/' + pairs[0][1] if pairs else '无'}。", confidence, evidence + ([f"abs_r:{pairs[0][2]:.6g}"] if pairs else [])))
        if policy.get("correlation_is_not_causation", True):
            limitations.append(_conclusion("相关关系不能单独证明因果。", "high", ["evidence-rule:correlation-is-not-causation"]))
    elif capability_id == "ENERGY_ANALYSIS":
        energy_fields = _matching_columns(numeric.columns, "energy", "power", "fuel", "gas", "coal", "steam", "electric", "能耗", "煤", "气", "电", "蒸汽")
        totals = {name: float(numeric[name].dropna().sum()) for name in energy_fields}
        variability = {name: float(numeric[name].dropna().std(ddof=0)) for name in energy_fields}
        metrics = {"method": "energy_field_inventory_and_variability", "energy_fields": energy_fields, "totals": totals, "standard_deviation": variability}
        if energy_fields:
            dominant = max(variability, key=variability.get)
            findings.append(_conclusion(f"能耗相关字段中波动最大的为 {dominant}。", confidence, evidence + [f"std:{variability[dominant]:.6g}"]))
        else:
            limitations.append(_conclusion("字段字典未提供可确认的能源计量字段，不能计算真实能耗。", "high", evidence))
    elif capability_id == "EQUIPMENT_HEALTH":
        z = ((numeric - numeric.mean()) / numeric.std(ddof=0).replace(0, np.nan)).abs()
        anomaly_rate = (z > float(policy.get("anomaly_zscore_threshold", 3.0))).mean().fillna(0)
        cv = (numeric.std(ddof=0) / numeric.mean().abs().replace(0, np.nan)).abs().fillna(0)
        risk = (anomaly_rate.clip(upper=1) * .65 + cv.clip(upper=1) * .35).sort_values(ascending=False)
        metrics = {"method": "statistical_health_indicator", "risk_score": {str(k): float(v) for k, v in risk.items()}, "not_a_fault_diagnosis": True}
        if len(risk):
            findings.append(_conclusion(f"统计健康风险最高的测点为 {risk.index[0]}，需结合检修与报警记录复核。", confidence, evidence + [f"risk:{risk.iloc[0]:.6g}"]))
        limitations.append(_conclusion("健康分仅由过程数据波动与异常率构成，不等同于设备故障诊断。", "high", ["evidence-rule:health-is-not-diagnosis"]))
    elif capability_id == "QUALITY_ANALYSIS":
        quality_fields = [name for name in _role_columns(context, {"quality", "controlled"}) if name in numeric]
        quality_fields += [name for name in _matching_columns(numeric.columns, "quality", "moisture", "content", "purity", "质量", "含量", "水分") if name not in quality_fields]
        stats = {name: {"mean": float(numeric[name].mean()), "std": float(numeric[name].std(ddof=0)), "missing_rate": float(numeric[name].isna().mean())} for name in quality_fields}
        metrics = {"method": "quality_variable_statistics", "quality_fields": quality_fields, "statistics": stats}
        if quality_fields:
            worst = max(quality_fields, key=lambda name: stats[name]["std"])
            findings.append(_conclusion(f"质量变量中绝对波动最大的为 {worst}。", confidence, evidence + [f"std:{stats[worst]['std']:.6g}"]))
        else:
            limitations.append(_conclusion("未识别到质量变量，需在场景注册字段中明确 quality/controlled 角色。", "high", evidence))
    elif capability_id == "OPERATING_STATE":
        scaled = (numeric - numeric.median()) / numeric.std(ddof=0).replace(0, np.nan)
        activity = scaled.diff().abs().median(axis=1).fillna(0)
        low, high = activity.quantile([.5, .85]) if len(activity) else (0.0, 0.0)
        labels = np.where(activity > high, "transient", np.where(activity > low, "adjusting", "steady"))
        counts = pd.Series(labels).value_counts().to_dict()
        metrics = {"method": "robust_multivariate_activity_quantiles", "thresholds": {"steady": float(low), "transient": float(high)}, "state_counts": {str(k): int(v) for k, v in counts.items()}}
        findings.append(_conclusion(f"识别到稳态 {counts.get('steady', 0)}、调节态 {counts.get('adjusting', 0)}、瞬态 {counts.get('transient', 0)} 个采样点。", confidence, evidence))
    elif capability_id == "BOTTLENECK_ANALYSIS":
        missing = numeric.isna().mean()
        variability = (numeric.std(ddof=0) / numeric.mean().abs().replace(0, np.nan)).abs().fillna(0).clip(upper=5) / 5
        score = (missing * .45 + variability * .55).sort_values(ascending=False)
        metrics = {"method": "data_constraint_bottleneck_ranking", "ranking": [{"field": str(k), "score": float(v)} for k, v in score.head(8).items()]}
        if len(score):
            findings.append(_conclusion(f"当前数据约束瓶颈最高的字段为 {score.index[0]}。", confidence, evidence + [f"score:{score.iloc[0]:.6g}"]))
        limitations.append(_conclusion("该排名反映数据质量和波动约束，不直接代表装置产能瓶颈。", "high", ["scope:data-bottleneck-only"]))
    elif capability_id == "ROOT_CAUSE_CANDIDATES":
        usable = numeric.loc[:, numeric.nunique(dropna=True) > 1]
        target_candidates = [name for name in _role_columns(context, {"quality", "controlled"}) if name in usable]
        target = target_candidates[0] if target_candidates else (str(usable.columns[-1]) if len(usable.columns) else None)
        correlations = usable.corr()[target].drop(target).abs().sort_values(ascending=False) if target else pd.Series(dtype=float)
        candidates = [{"field": str(name), "abs_correlation": float(value)} for name, value in correlations.head(8).items()]
        metrics = {"method": "target_correlation_candidate_screen", "target": target, "candidates": candidates, "causal_claim": False}
        if candidates:
            findings.append(_conclusion(f"与目标 {target} 统计关联最强的候选因素为 {candidates[0]['field']}。", confidence, evidence + [f"abs_r:{candidates[0]['abs_correlation']:.6g}"]))
        limitations.append(_conclusion("根因候选仅用于缩小排查范围，必须结合时序、机理或干预证据验证因果。", "high", ["evidence-rule:root-cause-requires-causal-evidence"]))
    else:
        return {
            "status": "blocked", "capability_id": capability_id,
            "outputs": {"facts": [], "findings": [], "hypotheses": [], "limitations": []},
            "metrics": {}, "artifacts": [], "evidence": evidence,
            "warnings": ["unsupported_capability"], "limitations": [],
            "execution_trace": [{"operation": "reject_unsupported_capability"}],
            "duration_ms": round((perf_counter() - started) * 1000, 3),
        }

    return {
        "status": "success", "capability_id": capability_id,
        "outputs": {"facts": facts, "findings": findings, "hypotheses": hypotheses, "limitations": limitations},
        "metrics": metrics, "artifacts": [], "evidence": evidence, "warnings": [],
        "limitations": limitations, "execution_trace": [{"operation": "execute_capability", "method": metrics.get("method", capability_id.lower())}],
        "duration_ms": round((perf_counter() - started) * 1000, 3),
    }


def execute_analysis(task_spec: dict[str, Any], analysis_plan: dict[str, Any], data_context: dict[str, Any], *, data: pd.DataFrame | None = None, data_path: str | Path | None = None, runtime_context: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime_context = runtime_context or {}
    policy = {**(runtime_context.get("evidence_policy") or {}), **(runtime_context.get("execution_policy") or {})}
    load_started = perf_counter()
    frame = data if data is not None else pd.read_csv(data_path)
    load_ms = round((perf_counter() - load_started) * 1000, 3)
    prepare_started = perf_counter()
    shared = {"numeric": _numeric(frame)}
    prepare_ms = round((perf_counter() - prepare_started) * 1000, 3)
    executions = []
    budget = (analysis_plan.get("analysis_budget") or {})
    max_runtime_seconds = float(budget.get("max_runtime_seconds", 15))
    analysis_started = perf_counter()
    for item in analysis_plan.get("selected_capabilities", []):
        if perf_counter() - analysis_started >= max_runtime_seconds:
            executions.append({"status": "skipped", "capability_id": item["capability"], "outputs": {"facts": [], "findings": [], "hypotheses": [], "limitations": []}, "metrics": {}, "artifacts": [], "evidence": [], "warnings": ["analysis_budget_exceeded"], "limitations": [], "execution_trace": [], "duration_ms": 0, "timeout_reason": f"analysis budget {max_runtime_seconds:g}s exceeded"})
            continue
        executions.append(execute_capability(item["capability"], frame, data_context, policy, shared))
    result = {
        "analysis_plan": analysis_plan,
        "facts": [row for execution in executions for row in execution["outputs"]["facts"]],
        "findings": [row for execution in executions for row in execution["outputs"]["findings"]],
        "hypotheses": [row for execution in executions for row in execution["outputs"]["hypotheses"]],
        "limitations": [row for execution in executions for row in execution["outputs"]["limitations"]],
        "capability_executions": executions,
        "task_spec": task_spec,
        "timing_trace": {"csv_load_ms": load_ms, "shared_feature_preparation_ms": prepare_ms, "capabilities_ms": {item["capability_id"]: item["duration_ms"] for item in executions}, "total_ms": round((perf_counter() - analysis_started) * 1000, 3)},
        "cache": {"shared_numeric_matrix": True, "shared_missing_rates": "missing_rates" in shared, "shared_correlation_matrix": "correlation" in shared},
    }
    output_dir = runtime_context.get("output_dir")
    if output_dir:
        path = Path(output_dir) / "industrial_analysis_result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        result["artifact"] = str(path)
    return result
