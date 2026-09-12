#!/usr/bin/env python3
"""Standalone industrial-analysis planner. Reads JSON from a file/stdin or exposes a Python API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


CAPABILITIES: dict[str, dict[str, Any]] = {
    "DATA_PROFILING": {"requires": {"all": ["readable_data"], "any": []}},
    "DATA_QUALITY_ANALYSIS": {"requires": {"all": ["readable_data"], "any": []}},
    "TREND_ANALYSIS": {"requires": {"all": ["numeric_fields"], "any": ["ordered_data", "timestamp"]}},
    "TIME_SERIES_ANALYSIS": {"requires": {"all": ["sufficient_samples"], "any": ["ordered_data", "timestamp"]}},
    "ANOMALY_DETECTION": {"requires": {"all": ["readable_data", "numeric_fields", "sufficient_samples"], "any": ["ordered_data", "timestamp"]}},
    "CORRELATION_ANALYSIS": {"requires": {"all": ["multiple_numeric_fields", "sufficient_samples"], "any": []}},
    "PROCESS_STABILITY": {"requires": {"all": ["process_variables"], "any": ["ordered_data", "timestamp"]}},
    "ENERGY_ANALYSIS": {"requires": {"all": ["confirmed_energy_semantics"], "any": []}},
    "EQUIPMENT_HEALTH": {"requires": {"all": ["equipment_context", "equipment_state_variables"], "any": []}},
    "QUALITY_ANALYSIS": {"requires": {"all": ["confirmed_quality_semantics"], "any": []}},
    "OPERATING_STATE": {"requires": {"all": ["operating_state_variables", "sufficient_samples"], "any": []}},
    "BOTTLENECK_ANALYSIS": {"requires": {"all": ["process_objective", "process_relationships", "multiple_numeric_fields"], "any": []}},
    "MISSING_DATA_ANALYSIS": {"requires": {"all": ["readable_data"], "any": []}},
    "ROOT_CAUSE_CANDIDATES": {"requires": {"all": ["defined_anomaly", "related_variables", "temporal_or_process_relationships"], "any": []}},
}

GENERIC_UNKNOWN_SAFE = {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "TIME_SERIES_ANALYSIS", "CORRELATION_ANALYSIS", "ANOMALY_DETECTION", "MISSING_DATA_ANALYSIS"}


def build_analysis_plan(
    message: str = "",
    direct_skill_ids: list[str] | None = None,
    *,
    scene: str | None = None,
    evidence: dict[str, Any] | None = None,
    capability_resolution: dict[str, Any] | None = None,
    task_understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(evidence or {})
    resolution = capability_resolution or context.get("capability_resolution") or {"selected": [], "candidates": []}
    task = task_understanding or context.get("task_understanding") or {"task_kind": "data_analysis"}
    scene_id = scene or context.get("detected_scene") or context.get("scene") or "unknown_scene"
    selected, skipped, blocked = [], [], []
    for candidate in resolution.get("candidates", []):
        item = {
            "capability": candidate["candidate"],
            "requires": candidate.get("requires", CAPABILITIES.get(candidate["candidate"], {}).get("requires", {})),
            "selected_skill_ids": candidate.get("selected_skill_ids", []),
            "reason": candidate.get("reason", ""),
            "confidence": candidate.get("final_score", 0),
            "resolution_trace": candidate,
        }
        if candidate.get("selected"):
            selected.append(item)
        elif candidate.get("status") == "blocked":
            blocked.append(item)
        else:
            skipped.append(item)
    documentation = resolution.get("documentation", [])
    return {
        "scene": scene_id,
        "task_kind": task.get("task_kind"),
        "data_quality": context.get("data_quality", "unknown"),
        "selected_capabilities": selected,
        "analysis_budget": (capability_resolution or {}).get("analysis_budget", {"max_capabilities": 6, "max_high_cost_capabilities": 1, "max_runtime_seconds": 15}),
        "skipped_capabilities": skipped,
        "blocked_capabilities": blocked,
        "documentation_capabilities": documentation,
        "capability_trace": resolution.get("candidates", []),
        "result_contract": {"layers": ["facts", "findings", "hypotheses", "limitations"], "root_cause_policy": "无独立因果证据时仅输出候选关联因素"},
        "lazy_loading": ["industrial_analysis"] if selected or documentation else [],
    }


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
