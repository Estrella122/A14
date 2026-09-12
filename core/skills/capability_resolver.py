from __future__ import annotations

from typing import Any

from .artifacts import EXECUTOR_ARTIFACT_CONTRACTS, canonical_artifact_types
from .task_understanding import understand_task


CAPABILITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "DATA_PROFILING": {"all": ("readable_data",), "any": (), "skills": ("dataset_scenario_profiler", "semantic_field_unit_standardizer"), "intents": ("inspect_data", "locate_abnormal_behavior")},
    "DATA_QUALITY_ANALYSIS": {"all": ("readable_data",), "any": (), "skills": ("time_axis_alignment_resampler", "missing_anomaly_cleaner"), "intents": ("inspect_data", "locate_abnormal_behavior")},
    "TREND_ANALYSIS": {"all": ("numeric_fields",), "any": ("ordered_data", "timestamp"), "skills": ("engineering_visualization_builder",), "intents": ("locate_abnormal_behavior", "prioritize_time_windows", "inspect_variation")},
    "TIME_SERIES_ANALYSIS": {"all": ("sufficient_samples",), "any": ("ordered_data", "timestamp"), "skills": ("steady_transient_state_detector", "time_delay_estimator_compensator"), "intents": ("prioritize_time_windows", "inspect_variation")},
    "ANOMALY_DETECTION": {"all": ("readable_data", "numeric_fields", "sufficient_samples"), "any": ("ordered_data", "timestamp"), "skills": ("missing_anomaly_cleaner",), "intents": ("locate_abnormal_behavior", "compare_normal_operation", "prioritize_time_windows", "inspect_variation")},
    "CORRELATION_ANALYSIS": {"all": ("multiple_numeric_fields", "sufficient_samples"), "any": (), "skills": ("collinearity_detector_reducer",), "intents": ("analyze_relationships",)},
    "PROCESS_STABILITY": {"all": ("process_variables",), "any": ("ordered_data", "timestamp"), "skills": ("steady_transient_state_detector", "model_diagnostics_evaluator"), "intents": ("compare_normal_operation", "inspect_variation")},
    "ENERGY_ANALYSIS": {"all": ("confirmed_energy_semantics",), "any": (), "skills": ("engineering_result_interpreter",), "intents": ("analyze_energy",)},
    "EQUIPMENT_HEALTH": {"all": ("equipment_context", "equipment_state_variables"), "any": (), "skills": ("engineering_result_interpreter",), "intents": ("assess_equipment",)},
    "QUALITY_ANALYSIS": {"all": ("confirmed_quality_semantics",), "any": (), "skills": ("engineering_result_interpreter",), "intents": ("analyze_quality",)},
    "OPERATING_STATE": {"all": ("operating_state_variables", "sufficient_samples"), "any": (), "skills": ("steady_transient_state_detector", "segment_quality_scorer_ranker"), "intents": ("compare_normal_operation", "prioritize_time_windows")},
    "BOTTLENECK_ANALYSIS": {"all": ("process_objective", "process_relationships", "multiple_numeric_fields"), "any": (), "skills": ("engineering_result_interpreter",), "intents": ("find_bottleneck",)},
    "MISSING_DATA_ANALYSIS": {"all": ("readable_data",), "any": (), "skills": ("missing_anomaly_cleaner",), "intents": ("inspect_missing_data", "inspect_data")},
    "ROOT_CAUSE_CANDIDATES": {"all": ("defined_anomaly", "related_variables", "temporal_or_process_relationships"), "any": (), "skills": ("time_delay_estimator_compensator", "engineering_result_interpreter"), "intents": ("find_root_cause",)},
    "SEGMENTATION": {"all": (), "any": (), "skills": ("high_snr_dynamic_segment_extractor",), "intents": ("selection",),
                     "required_artifacts": EXECUTOR_ARTIFACT_CONTRACTS["segmentation"]["requires"]},
    "MODELING": {"all": (), "any": (), "skills": ("system_identification_trainer",), "intents": ("modeling",),
                 "required_artifacts": EXECUTOR_ARTIFACT_CONTRACTS["modeling"]["requires"]},
    "OPTIMIZATION": {"all": (), "any": (), "skills": ("closed_loop_preprocessing_optimizer",), "intents": ("optimization",),
                     "required_artifacts": EXECUTOR_ARTIFACT_CONTRACTS["optimization"]["requires"],
                     "required_contract_fields": ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data")},
}

CAPABILITY_TERMS = {
    "DATA_PROFILING": ("画像", "概览", "数据概况"), "DATA_QUALITY_ANALYSIS": ("数据质量", "完整性", "可用性"),
    "TREND_ANALYSIS": ("趋势", "走势", "变化"), "TIME_SERIES_ANALYSIS": ("时序", "周期", "滞后", "时间段"),
    "ANOMALY_DETECTION": ("异常", "离群", "不正常", "不一样", "重点检查", "波动", "有问题"),
    "CORRELATION_ANALYSIS": ("相关", "关联", "共线"), "PROCESS_STABILITY": ("稳定", "正常运行", "波动", "工况"),
    "ENERGY_ANALYSIS": ("能源", "能耗", "电量", "功率", "燃料"), "EQUIPMENT_HEALTH": ("设备健康", "设备故障", "劣化", "振动"),
    "QUALITY_ANALYSIS": ("产品质量", "合格率", "硅含量", "水分"), "OPERATING_STATE": ("工况", "运行状态", "动态段"),
    "BOTTLENECK_ANALYSIS": ("瓶颈", "产能", "卡点"), "MISSING_DATA_ANALYSIS": ("缺失", "空值"),
    "ROOT_CAUSE_CANDIDATES": ("根因", "原因", "为什么"),
}

SKILL_TO_CAPABILITIES: dict[str, set[str]] = {}
for _capability, _definition in CAPABILITY_DEFINITIONS.items():
    for _skill in _definition["skills"]:
        SKILL_TO_CAPABILITIES.setdefault(_skill, set()).add(_capability)
GENERIC_UNKNOWN_SAFE = {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "TIME_SERIES_ANALYSIS", "ANOMALY_DETECTION", "CORRELATION_ANALYSIS", "MISSING_DATA_ANALYSIS"}
COST_LEVELS = {
    "DATA_PROFILING": "LOW", "DATA_QUALITY_ANALYSIS": "LOW", "MISSING_DATA_ANALYSIS": "LOW",
    "TREND_ANALYSIS": "MEDIUM", "ENERGY_ANALYSIS": "MEDIUM", "CORRELATION_ANALYSIS": "MEDIUM",
    "TIME_SERIES_ANALYSIS": "MEDIUM", "ANOMALY_DETECTION": "MEDIUM", "PROCESS_STABILITY": "HIGH",
    "ROOT_CAUSE_CANDIDATES": "HIGH", "SEGMENTATION": "HIGH", "MODELING": "HIGH", "OPTIMIZATION": "HIGH",
}
COST_PENALTY = {"LOW": 0.03, "MEDIUM": 0.1, "HIGH": 0.22}


def evidence_flags(context: dict[str, Any]) -> set[str]:
    flags = set()
    if context.get("run_id") and context.get("sample_count", 0) > 0: flags.add("readable_data")
    if context.get("numeric_field_count", 0) > 0: flags.add("numeric_fields")
    if context.get("numeric_field_count", 0) > 1: flags.update(("multiple_numeric_fields", "related_variables"))
    if context.get("sample_count", 0) >= 30: flags.add("sufficient_samples")
    if context.get("timestamp"): flags.add("timestamp")
    if context.get("ordered_data"): flags.update(("ordered_data", "temporal_or_process_relationships"))
    semantics = set(context.get("semantic_types") or ())
    trusted_semantics = context.get("mapping_confidence") is None or context.get("mapping_confidence", 0) >= 0.6
    if trusted_semantics and semantics & {"energy", "power", "electricity", "fuel"}: flags.add("confirmed_energy_semantics")
    if trusted_semantics and context.get("detected_scene") == "steel_industry_energy": flags.add("confirmed_energy_semantics")
    if trusted_semantics and semantics & {"quality", "product_quality", "controlled"}: flags.add("confirmed_quality_semantics")
    if context.get("equipment_context"): flags.update(("equipment_context", "equipment_state_variables"))
    if context.get("process_context"): flags.update(("process_variables", "process_relationships", "process_objective", "operating_state_variables"))
    return flags


def resolve_capabilities(task: dict[str, Any], context: dict[str, Any], recalled_skill_ids=(), lexical_candidates=()) -> dict[str, Any]:
    intent_aliases = {
        "scene_identification": "inspect_data",
        "anomaly_detection": "locate_abnormal_behavior", "process_stability": "compare_normal_operation",
        "trend_analysis": "inspect_variation", "time_window_analysis": "prioritize_time_windows",
        "relationship_analysis": "analyze_relationships", "missing_data_analysis": "inspect_missing_data",
        "energy_analysis": "analyze_energy", "quality_analysis": "analyze_quality",
        "equipment_health": "assess_equipment", "bottleneck_analysis": "find_bottleneck",
        "root_cause_analysis": "find_root_cause", "data_profiling": "inspect_data",
    }
    intents = {intent_aliases.get(item, item) for item in task["semantic_intents"]}
    intents.update(task.get("response_intents") or ())
    flags = evidence_flags(context)
    recalled = {cap for sid in recalled_skill_ids for cap in SKILL_TO_CAPABILITIES.get(sid, ())}
    weak_recalled = set()
    lexical = set(task.get("requested_capabilities") or task.get("explicit_capabilities") or ())
    for item in lexical_candidates:
        weak_recalled.update(SKILL_TO_CAPABILITIES.get(item.get("skill_id"), ()))
    if task["task_kind"] in {"data_analysis", "execute_pipeline"} and intents & {"locate_abnormal_behavior", "compare_normal_operation", "prioritize_time_windows"}:
        recalled.update(("DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "ANOMALY_DETECTION"))
    elif task["task_kind"] in {"data_analysis", "execute_pipeline"} and "inspect_variation" in intents:
        recalled.update(("DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS"))
    candidates = recalled | weak_recalled | lexical
    if task["task_kind"] == "knowledge_explanation":
        candidates = lexical
    for intent, capability in (("selection", "SEGMENTATION"), ("modeling", "MODELING"), ("optimization", "OPTIMIZATION")):
        if intent in intents:
            candidates.add(capability)
    available_artifacts = canonical_artifact_types(context.get("available_artifacts") or ())
    available_contract_fields = set(context.get("available_contract_fields") or ())
    planned_groups = set()
    if task.get("execution_mode") == "execute" and task.get("constraints", {}).get("allow_upstream_execution", True):
        if "cleaning" in intents: planned_groups.update(("standardization", "cleaning"))
        if "selection" in intents: planned_groups.update(("standardization", "cleaning", "segmentation"))
        if "modeling" in intents: planned_groups.update(("standardization", "cleaning", "segmentation", "modeling"))
        if "optimization" in intents and "modeling" in intents: planned_groups.add("optimization")
    planned_artifacts = {artifact for group in planned_groups for artifact in EXECUTOR_ARTIFACT_CONTRACTS.get(group, {}).get("produces", ())}
    traces = []
    for capability in sorted(candidates):
        definition = CAPABILITY_DEFINITIONS[capability]
        all_results = {name: name in flags for name in definition["all"]}
        any_results = {name: name in flags for name in definition["any"]}
        hard_ready = all(all_results.values()) and (not any_results or any(any_results.values()))
        unknown_scene_blocked = not context.get("detected_scene") and capability not in GENERIC_UNKNOWN_SAFE
        hard_ready = hard_ready and not unknown_scene_blocked
        required_artifacts = tuple(definition.get("required_artifacts", ()))
        artifact_checks = {item: item in available_artifacts for item in required_artifacts}
        missing_artifacts = [item for item, present in artifact_checks.items() if not present]
        producible_artifacts = [item for item in missing_artifacts if item in planned_artifacts]
        unproducible_artifacts = [item for item in missing_artifacts if item not in planned_artifacts]
        artifact_score = round(sum(artifact_checks.values()) / len(artifact_checks), 3) if artifact_checks else 1.0
        required_contract = tuple(definition.get("required_contract_fields", ()))
        missing_contract = [item for item in required_contract if item not in available_contract_fields]
        semantic = max((1.0 if intent in definition["intents"] else 0.0 for intent in intents), default=0.0)
        if capability in lexical: semantic = max(semantic, 0.55)
        quality = context.get("data_quality")
        quality_fit = max(0.0, min(float(quality) / 100, 1.0)) if isinstance(quality, (int, float)) else 0.5
        context_fit = min(1.0, 0.25 + 0.15 * int("readable_data" in flags) + 0.2 * int("numeric_fields" in flags) + 0.15 * int("ordered_data" in flags) + 0.1 * int(bool(context.get("detected_scene"))) + 0.15 * quality_fit)
        checks = list(all_results.values()) + ([any(any_results.values())] if any_results else [])
        precondition = sum(checks) / len(checks) if checks else 1.0
        scene_confidence = context.get("scene_confidence")
        scene_fit = max(0.5, min(float(scene_confidence), 1.0)) if isinstance(scene_confidence, (int, float)) else 0.8 if context.get("detected_scene") else 0.5
        dependency = (round(.7 * artifact_score + .3 * (1.0 if hard_ready else 0.0), 3)
                      if required_artifacts else 1.0 if hard_ready and context.get("available_artifacts") else 0.7 if hard_ready else 0.4)
        lexical_score = 1.0 if capability in lexical else 0.6 if capability in recalled else 0.25 if capability in weak_recalled else 0.0
        final = round(.35*semantic + .20*context_fit + .20*precondition + .10*scene_fit + .10*dependency + .05*lexical_score, 3)
        knowledge = task["task_kind"] == "knowledge_explanation"
        artifact_ready = not missing_artifacts
        selected = bool(not knowledge and hard_ready and artifact_ready and not missing_contract and semantic >= 0.5 and final >= 0.62)
        blocked_by_artifacts = bool(unproducible_artifacts or missing_contract)
        deferred_by_artifacts = bool(missing_artifacts and not blocked_by_artifacts and producible_artifacts)
        status = "reference" if knowledge else "selected" if selected else "blocked" if not hard_ready or blocked_by_artifacts else "deferred"
        missing = [name for name, ok in all_results.items() if not ok]
        if any_results and not any(any_results.values()): missing.append("any:" + "|".join(any_results))
        if unknown_scene_blocked: missing.append("known_scene")
        if knowledge:
            reason = "知识解释仅加载能力文档，不进入数据分析计划"
        elif selected:
            reason = "语义目标匹配，数据、artifact 与合同前置条件满足"
        elif missing_contract:
            reason = "缺少显式执行合同：" + "、".join(missing_contract)
        elif unproducible_artifacts:
            reason = "缺少且当前 DAG 无法生成 artifact：" + "、".join(unproducible_artifacts)
        elif deferred_by_artifacts:
            reason = "等待上游 Executor 生成：" + "、".join(producible_artifacts)
        elif missing:
            reason = "缺少前置条件：" + "、".join(missing)
        else:
            reason = "语义或综合评分不足"
        cost = COST_LEVELS.get(capability, "MEDIUM")
        expected_value = round(max(0.0, min(1.0, .55 * semantic + .25 * context_fit + .20 * dependency)), 3)
        traces.append({"candidate": capability, "semantic_intent_score": semantic, "context_fit_score": round(context_fit,3), "data_precondition_score": round(precondition,3), "scene_fit_score": scene_fit, "dependency_readiness_score": dependency, "lexical_recall_score": lexical_score, "final_score": final, "estimated_cost": cost, "expected_value": expected_value, "planning_value": round(expected_value - COST_PENALTY[cost], 3), "preconditions": {**all_results, **any_results}, "artifact_readiness": artifact_checks, "artifact_readiness_score": artifact_score, "required_artifacts": list(required_artifacts), "missing_artifacts": missing_artifacts, "producible_artifacts": producible_artifacts, "missing_contract_fields": missing_contract, "selected": selected, "status": status, "reason": reason, "selected_skill_ids": list(definition["skills"]), "requires": {"all": list(definition["all"]), "any": list(definition["any"])}})
    objective_text = str(task.get("objective") or "")
    deep_analysis_requested = bool(task.get("constraints", {}).get("deep_analysis")) or any(term in objective_text for term in ("完整深度分析", "全面深度分析", "所有能力", "full deep analysis"))
    budget = ({"max_capabilities": 10, "max_high_cost_capabilities": 4, "max_runtime_seconds": 60}
              if deep_analysis_requested else
              {"max_capabilities": 6, "max_high_cost_capabilities": 1, "max_runtime_seconds": 15})
    budget["mode"] = "extended" if deep_analysis_requested else "fast"
    selected_traces = sorted((item for item in traces if item["selected"]), key=lambda item: (item["planning_value"], item["final_score"]), reverse=True)
    kept = []
    high_cost = 0
    for item in selected_traces:
        over_budget = len(kept) >= budget["max_capabilities"] or (item["estimated_cost"] == "HIGH" and high_cost >= budget["max_high_cost_capabilities"])
        if over_budget:
            item.update(selected=False, status="deferred", reason="已满足基础分析预算，转入按需深度分析")
            continue
        kept.append(item)
        high_cost += int(item["estimated_cost"] == "HIGH")
    selected = [item["candidate"] for item in traces if item["selected"]]
    resolved_skill_ids = {skill for item in traces if item["selected"] for skill in item["selected_skill_ids"]}
    evidence_skill_ids = set()
    if task["task_kind"] == "data_analysis" and context.get("available_artifacts"):
        evidence_skill_ids = set(recalled_skill_ids)
        resolved_skill_ids.update(evidence_skill_ids)
    return {"selected": selected, "documentation": [item["candidate"] for item in traces if item["status"] == "reference"], "candidates": traces, "analysis_budget": budget, "available_evidence": sorted(flags), "resolved_skill_ids": sorted(resolved_skill_ids), "evidence_skill_ids": sorted(evidence_skill_ids)}
