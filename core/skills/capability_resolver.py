from __future__ import annotations

import re
from typing import Any


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


def understand_task(message: str) -> dict[str, Any]:
    text = str(message or "").strip()
    normalized = text.lower()
    knowledge = bool(re.search(r"(?:解释|介绍|说明).{0,16}(?:是什么|什么意思|概念|区别)|^(?:解释|介绍|说明)(?:一下)?(?:异常检测|趋势分析|相关性|因果)|(?:是什么|什么意思|有什么区别)[？?]?$", normalized))
    artifact = bool(re.search(r"导出|下载|打包|产物", normalized))
    execution = bool(re.search(r"(?:请|帮我|立即|重新|开始|继续)?(?:执行|重跑|训练|清洗|生成|提取|估计)|重新运行|运行(?:全流程|流水线|模型)", normalized)) and not knowledge
    task_kind = "knowledge_explanation" if knowledge else "artifact_request" if artifact else "execute_pipeline" if execution else "data_analysis"
    intents = []
    patterns = (
        ("locate_abnormal_behavior", r"异常|不正常|不一样|重点检查|波动.{0,6}(?:问题|异常)|哪里.{0,8}(?:问题|异常)"),
        ("compare_normal_operation", r"正常运行|和平时|不一样|偏离正常"),
        ("prioritize_time_windows", r"时间段|重点检查|哪些时候|哪段"),
        ("inspect_variation", r"波动|变化|走势|趋势"),
        ("analyze_relationships", r"相关|关联|因果|影响"),
        ("inspect_missing_data", r"缺失|空值|完整性"),
        ("analyze_energy", r"能耗|能源|电量|功率|燃料"),
        ("analyze_quality", r"产品质量|合格率|硅含量|水分"),
        ("assess_equipment", r"设备健康|故障|劣化|振动"),
        ("find_bottleneck", r"瓶颈|产能|卡点"),
        ("find_root_cause", r"根因|为什么|原因"),
    )
    for intent, pattern in patterns:
        if re.search(pattern, normalized):
            intents.append(intent)
    if task_kind == "data_analysis" and not intents and re.search(r"数据|字段|样本|工况|设备|过程|分析", normalized):
        intents.append("inspect_data")
    explicit = [name for name, terms in CAPABILITY_TERMS.items() if any(term in normalized for term in terms)]
    outputs = [name for name, pattern in (("time_windows", r"时间段|哪段"), ("explanation", r"解释|介绍|说明"), ("findings", r"找|看看|分析|检查")) if re.search(pattern, normalized)]
    negations = re.findall(r"(?:不要|不必|无需|禁止|别)\s*([^，。；]+)", text)
    return {"task_kind": task_kind, "semantic_intents": intents, "requested_outputs": outputs or ["findings"], "execution_requested": execution, "negations": negations, "constraints": {}, "explicit_capabilities": explicit}


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
    if trusted_semantics and semantics & {"quality", "product_quality", "controlled"}: flags.add("confirmed_quality_semantics")
    if context.get("equipment_context"): flags.update(("equipment_context", "equipment_state_variables"))
    if context.get("process_context"): flags.update(("process_variables", "process_relationships", "process_objective", "operating_state_variables"))
    return flags


def resolve_capabilities(task: dict[str, Any], context: dict[str, Any], recalled_skill_ids=(), lexical_candidates=()) -> dict[str, Any]:
    intents = set(task["semantic_intents"])
    flags = evidence_flags(context)
    recalled = {cap for sid in recalled_skill_ids for cap in SKILL_TO_CAPABILITIES.get(sid, ())}
    weak_recalled = set()
    lexical = set(task["explicit_capabilities"])
    for item in lexical_candidates:
        weak_recalled.update(SKILL_TO_CAPABILITIES.get(item.get("skill_id"), ()))
    if task["task_kind"] == "data_analysis" and intents & {"locate_abnormal_behavior", "compare_normal_operation", "prioritize_time_windows", "inspect_variation"}:
        recalled.update(("DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "ANOMALY_DETECTION"))
    candidates = recalled | weak_recalled | lexical
    if task["task_kind"] == "knowledge_explanation":
        candidates = lexical
    traces = []
    for capability in sorted(candidates):
        definition = CAPABILITY_DEFINITIONS[capability]
        all_results = {name: name in flags for name in definition["all"]}
        any_results = {name: name in flags for name in definition["any"]}
        hard_ready = all(all_results.values()) and (not any_results or any(any_results.values()))
        unknown_scene_blocked = not context.get("detected_scene") and capability not in GENERIC_UNKNOWN_SAFE
        hard_ready = hard_ready and not unknown_scene_blocked
        semantic = max((1.0 if intent in definition["intents"] else 0.0 for intent in intents), default=0.0)
        if capability in lexical: semantic = max(semantic, 0.55)
        quality = context.get("data_quality")
        quality_fit = max(0.0, min(float(quality) / 100, 1.0)) if isinstance(quality, (int, float)) else 0.5
        context_fit = min(1.0, 0.25 + 0.15 * int("readable_data" in flags) + 0.2 * int("numeric_fields" in flags) + 0.15 * int("ordered_data" in flags) + 0.1 * int(bool(context.get("detected_scene"))) + 0.15 * quality_fit)
        checks = list(all_results.values()) + ([any(any_results.values())] if any_results else [])
        precondition = sum(checks) / len(checks) if checks else 1.0
        scene_confidence = context.get("scene_confidence")
        scene_fit = max(0.5, min(float(scene_confidence), 1.0)) if isinstance(scene_confidence, (int, float)) else 0.8 if context.get("detected_scene") else 0.5
        dependency = 1.0 if hard_ready and context.get("available_artifacts") else 0.7 if hard_ready else 0.4
        lexical_score = 1.0 if capability in lexical else 0.6 if capability in recalled else 0.25 if capability in weak_recalled else 0.0
        final = round(.35*semantic + .20*context_fit + .20*precondition + .10*scene_fit + .10*dependency + .05*lexical_score, 3)
        knowledge = task["task_kind"] == "knowledge_explanation"
        selected = bool(not knowledge and hard_ready and semantic >= 0.5 and final >= 0.62)
        status = "reference" if knowledge else "selected" if selected else "blocked" if not hard_ready else "deferred"
        missing = [name for name, ok in all_results.items() if not ok]
        if any_results and not any(any_results.values()): missing.append("any:" + "|".join(any_results))
        if unknown_scene_blocked: missing.append("known_scene")
        reason = "知识解释仅加载能力文档，不进入数据分析计划" if knowledge else "语义目标匹配且数据与依赖前置条件满足" if selected else "缺少前置条件：" + "、".join(missing) if missing else "语义或综合评分不足"
        traces.append({"candidate": capability, "semantic_intent_score": semantic, "context_fit_score": round(context_fit,3), "data_precondition_score": round(precondition,3), "scene_fit_score": scene_fit, "dependency_readiness_score": dependency, "lexical_recall_score": lexical_score, "final_score": final, "preconditions": {**all_results, **any_results}, "selected": selected, "status": status, "reason": reason, "selected_skill_ids": list(definition["skills"]), "requires": {"all": list(definition["all"]), "any": list(definition["any"])}})
    selected = [item["candidate"] for item in traces if item["selected"]]
    resolved_skill_ids = {skill for item in traces if item["selected"] for skill in item["selected_skill_ids"]}
    evidence_skill_ids = set()
    if task["task_kind"] == "data_analysis" and context.get("available_artifacts"):
        evidence_skill_ids = set(recalled_skill_ids)
        resolved_skill_ids.update(evidence_skill_ids)
    return {"selected": selected, "documentation": [item["candidate"] for item in traces if item["status"] == "reference"], "candidates": traces, "available_evidence": sorted(flags), "resolved_skill_ids": sorted(resolved_skill_ids), "evidence_skill_ids": sorted(evidence_skill_ids)}
