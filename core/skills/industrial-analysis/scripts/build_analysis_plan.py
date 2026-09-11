#!/usr/bin/env python3
"""Standalone industrial-analysis planner. Reads JSON from a file/stdin or exposes a Python API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


CAPABILITIES: dict[str, dict[str, Any]] = {
    "DATA_PROFILING": {"requires": ("readable_data",), "keywords": ("画像", "概览", "分析", "数据")},
    "DATA_QUALITY_ANALYSIS": {"requires": ("readable_data",), "keywords": ("质量", "完整", "可用", "分析", "数据")},
    "TREND_ANALYSIS": {"requires": ("numeric_fields", "ordered_data"), "keywords": ("趋势", "变化", "走势", "时序")},
    "TIME_SERIES_ANALYSIS": {"requires": ("ordered_data", "sufficient_samples"), "keywords": ("时序", "周期", "滞后", "预测")},
    "ANOMALY_DETECTION": {"requires": ("numeric_fields", "sufficient_samples"), "keywords": ("异常", "离群", "故障", "波动")},
    "CORRELATION_ANALYSIS": {"requires": ("multiple_numeric_fields", "sufficient_samples"), "keywords": ("相关", "关联", "共线", "影响因素")},
    "PROCESS_STABILITY": {"requires": ("ordered_data", "process_variables"), "keywords": ("稳定", "稳态", "波动", "工况")},
    "ENERGY_ANALYSIS": {"requires": ("confirmed_energy_semantics",), "keywords": ("能源", "能耗", "电量", "功率", "燃料", "煤耗")},
    "EQUIPMENT_HEALTH": {"requires": ("equipment_context", "equipment_state_variables"), "keywords": ("设备健康", "设备状态", "故障", "劣化", "振动")},
    "QUALITY_ANALYSIS": {"requires": ("confirmed_quality_semantics",), "keywords": ("质量", "产品指标", "合格率", "硅含量", "水分")},
    "OPERATING_STATE": {"requires": ("operating_state_variables", "sufficient_samples"), "keywords": ("工况", "运行状态", "稳态", "动态段")},
    "BOTTLENECK_ANALYSIS": {"requires": ("process_objective", "process_relationships", "multiple_numeric_fields"), "keywords": ("瓶颈", "产能", "约束", "卡点")},
    "MISSING_DATA_ANALYSIS": {"requires": ("readable_data",), "keywords": ("缺失", "空值", "完整性", "质量", "数据")},
    "ROOT_CAUSE_CANDIDATES": {"requires": ("defined_anomaly", "related_variables", "temporal_or_process_relationships"), "keywords": ("根因", "原因", "为什么", "影响因素")},
}

GENERIC_UNKNOWN_SAFE = {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "CORRELATION_ANALYSIS", "ANOMALY_DETECTION", "MISSING_DATA_ANALYSIS"}

CAPABILITY_SKILLS = {
    "DATA_PROFILING": ("dataset_scenario_profiler", "semantic_field_unit_standardizer"),
    "DATA_QUALITY_ANALYSIS": ("time_axis_alignment_resampler", "missing_anomaly_cleaner"),
    "TREND_ANALYSIS": ("engineering_visualization_builder",),
    "TIME_SERIES_ANALYSIS": ("steady_transient_state_detector", "time_delay_estimator_compensator"),
    "ANOMALY_DETECTION": ("missing_anomaly_cleaner",),
    "CORRELATION_ANALYSIS": ("collinearity_detector_reducer",),
    "PROCESS_STABILITY": ("steady_transient_state_detector", "model_diagnostics_evaluator"),
    "ENERGY_ANALYSIS": ("engineering_result_interpreter",), "EQUIPMENT_HEALTH": ("engineering_result_interpreter",),
    "QUALITY_ANALYSIS": ("engineering_result_interpreter",),
    "OPERATING_STATE": ("steady_transient_state_detector", "segment_quality_scorer_ranker"),
    "BOTTLENECK_ANALYSIS": ("engineering_result_interpreter",), "MISSING_DATA_ANALYSIS": ("missing_anomaly_cleaner",),
    "ROOT_CAUSE_CANDIDATES": ("time_delay_estimator_compensator", "engineering_result_interpreter"),
}


def _normalize(value: str) -> str:
    return (value or "").lower().replace(" ", "")


def _available_evidence(context: dict[str, Any]) -> set[str]:
    available = set(context.get("evidence_flags", ()))
    if context.get("data") is not None or context.get("dataset_ref"):
        available.add("readable_data")
    fields = context.get("fields") or []
    numeric = [field for field in fields if field.get("data_type") in {"number", "float", "integer", "int"}]
    semantics = {field.get("semantic_type") for field in fields if field.get("mapping_confidence", 1) >= 0.6}
    if numeric:
        available.add("numeric_fields")
    if len(numeric) >= 2:
        available.update({"multiple_numeric_fields", "related_variables"})
    if context.get("timestamp") or "time" in semantics or context.get("ordered_data"):
        available.update({"ordered_data", "temporal_or_process_relationships"})
    if context.get("sample_size", 0) >= context.get("minimum_sample_size", 30):
        available.add("sufficient_samples")
    if semantics & {"energy", "power", "electricity", "fuel"}:
        available.add("confirmed_energy_semantics")
    if semantics & {"quality", "product_quality"}:
        available.add("confirmed_quality_semantics")
    if context.get("equipment_context"):
        available.add("equipment_context")
    if context.get("process_context"):
        available.update({"process_variables", "process_relationships", "temporal_or_process_relationships"})
    return available


def build_analysis_plan(message: str = "", direct_skill_ids: list[str] | None = None, *, scene: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(evidence or {})
    scene_id = scene or context.get("scene") or "unknown_scene"
    text = _normalize(message or context.get("objective", ""))
    direct = set(direct_skill_ids or ())
    available = _available_evidence(context)
    mapping_confidence = context.get("mapping_confidence")
    uncertain = context.get("semantic_type") == "uncertain" or (isinstance(mapping_confidence, (int, float)) and mapping_confidence < 0.6)
    selected, skipped = [], []
    for capability, definition in CAPABILITIES.items():
        hits = [word for word in definition["keywords"] if word.lower() in text]
        requested = bool(hits or set(CAPABILITY_SKILLS[capability]) & direct or capability in {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "MISSING_DATA_ANALYSIS"})
        missing = [requirement for requirement in definition["requires"] if requirement not in available]
        if not context:  # Legacy host calls have no dataset context at planning time.
            missing = []
        reason = ""
        if scene_id in {"unknown", "unknown_scene"} and capability not in GENERIC_UNKNOWN_SAFE:
            requested, reason = False, "未知场景缺少设备/工艺知识，仅允许安全的通用数据分析"
        elif uncertain and capability in {"ENERGY_ANALYSIS", "EQUIPMENT_HEALTH", "QUALITY_ANALYSIS", "BOTTLENECK_ANALYSIS", "ROOT_CAUSE_CANDIDATES"}:
            requested, reason = False, "字段语义或映射置信度不足"
        elif requested and missing:
            requested, reason = False, "缺少执行证据：" + "、".join(missing)
        elif not requested:
            reason = "当前目标未请求该能力"
        item = {"capability": capability, "requires": list(definition["requires"]), "selected_skill_ids": list(CAPABILITY_SKILLS[capability])}
        if requested:
            item.update(reason="；".join(hits[:3]) or "通用分析基线", confidence="low" if uncertain else "medium")
            selected.append(item)
        else:
            item["reason"] = reason
            skipped.append(item)
    lazy_loading = ["industrial_analysis", "data_pipeline"]
    if any(item["capability"] in {"ENERGY_ANALYSIS", "EQUIPMENT_HEALTH", "QUALITY_ANALYSIS", "BOTTLENECK_ANALYSIS", "ROOT_CAUSE_CANDIDATES"} for item in selected):
        lazy_loading.append("scene_system")
    if any(item["capability"] in {"ENERGY_ANALYSIS", "EQUIPMENT_HEALTH", "QUALITY_ANALYSIS"} for item in selected):
        lazy_loading.append("field_system")
    return {"scene": scene_id, "data_quality": context.get("data_quality", "unknown"), "selected_capabilities": selected, "skipped_capabilities": skipped,
            "result_contract": {"layers": ["facts", "findings", "hypotheses", "limitations"], "root_cause_policy": "无独立因果证据时仅输出候选关联因素"},
            "lazy_loading": sorted(lazy_loading)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="Input JSON file; omit for stdin")
    args = parser.parse_args()
    payload = json.load(open(args.input, encoding="utf-8")) if args.input else json.load(sys.stdin)
    json.dump(build_analysis_plan(payload.get("objective", ""), scene=payload.get("scene"), evidence=payload), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
