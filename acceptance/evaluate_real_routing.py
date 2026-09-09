#!/usr/bin/env python3
"""Evaluate human-approved real routing cases without modifying the model."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from django.conf import settings
if not settings.configured:
    settings.configure(BASE_DIR=ROOT)

from core.skills.catalog import SKILL_MAP
from core.skills.runtime import plan_skills

VALID_MODES = {"analyze", "execute"}
VALID_STOPS = {"evidence_only", "standardization", "cleaning", "selection", "modeling", "report"}
PIPELINE_STOPS = {
    "closed_loop_preprocessing_optimizer": "report",
    "system_identification_trainer": "modeling",
    "high_snr_dynamic_segment_extractor": "selection",
    "missing_anomaly_cleaner": "cleaning",
    "time_axis_alignment_resampler": "cleaning",
    "semantic_field_unit_standardizer": "standardization",
    "dataset_scenario_profiler": "standardization",
}

def predicted_stop(plan: dict) -> str:
    if plan["mode"] != "execute":
        return "evidence_only"
    if plan.get("analysis", {}).get("full_pipeline_requested"):
        return "report"
    direct = set(plan.get("direct_skill_ids", []))
    order = ["report", "modeling", "selection", "cleaning", "standardization"]
    found = {PIPELINE_STOPS[s] for s in direct if s in PIPELINE_STOPS}
    return next((stage for stage in order if stage in found), "evidence_only")

def load_cases(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids: set[str] = set()
    for row in rows:
        required = {"id", "session_group", "text", "labels", "mode", "stop_after", "critical_no_execute", "split", "review_status"}
        missing = required - row.keys()
        if missing:
            raise ValueError(f"{row.get('id', '?')} 缺少字段：{sorted(missing)}")
        if row["id"] in ids:
            raise ValueError(f"重复样本 ID：{row['id']}")
        ids.add(row["id"])
        unknown = set(row["labels"]) - SKILL_MAP.keys()
        if unknown:
            raise ValueError(f"{row['id']} 含未知 Skill：{sorted(unknown)}")
        if row["mode"] not in VALID_MODES or row["stop_after"] not in VALID_STOPS:
            raise ValueError(f"{row['id']} 的 mode/stop_after 无效")
    approved_groups: dict[str, str] = {}
    for row in rows:
        if row["review_status"] != "approved":
            continue
        old = approved_groups.setdefault(row["session_group"], row["split"])
        if old != row["split"]:
            raise ValueError(f"会话组 {row['session_group']} 跨越数据分区，存在泄漏")
    return rows

def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "acceptance/real_routing_gold.jsonl"
    if not source.exists():
        print(f"缺少 {source}；请复制并填写 real_routing_gold.template.jsonl。", file=sys.stderr)
        return 2
    all_rows = load_cases(source)
    rows = [r for r in all_rows if r["review_status"] == "approved" and r["split"] == "test"]
    results = []
    for row in rows:
        plan = plan_skills(row["text"])
        actual_labels = plan.get("direct_skill_ids", [])
        actual_mode = plan["mode"]
        actual_stop = predicted_stop(plan)
        results.append({**row, "actual_labels": actual_labels, "actual_mode": actual_mode,
                        "actual_stop_after": actual_stop,
                        "exact": set(actual_labels) == set(row["labels"]),
                        "critical_misexecution": bool(row["critical_no_execute"] and actual_mode == "execute")})
    n = len(results)
    unknown = [r for r in results if not r["labels"]]
    metric = lambda key: sum(bool(r[key]) for r in results) / n if n else None
    exact = metric("exact")
    stage = sum(r["actual_stop_after"] == r["stop_after"] for r in results) / n if n else None
    critical = sum(r["critical_misexecution"] for r in results)
    rejection = sum(not r["actual_labels"] for r in unknown) / len(unknown) if unknown else None
    gates = {
        "minimum_approved_test_cases": n >= 30,
        "exact_skill_set_accuracy_gte_095": exact is not None and exact >= .95,
        "stage_accuracy_gte_098": stage is not None and stage >= .98,
        "critical_misexecution_eq_0": critical == 0,
        "unknown_rejection_gte_095": rejection is not None and rejection >= .95,
    }
    report = {"source": str(source), "source_type": "human_approved_real_requests",
              "production_accuracy_claim": False, "approved_test_cases": n,
              "pending_or_non_test_cases": len(all_rows) - n,
              "metrics": {"exact_skill_set_accuracy": exact, "stage_accuracy": stage,
                          "critical_misexecution_count": critical, "unknown_rejection": rejection},
              "gates": gates,
              "status": "passed" if all(gates.values()) else "insufficient_evidence" if n < 30 else "failed",
              "errors": [r for r in results if not r["exact"] or r["actual_stop_after"] != r["stop_after"] or r["critical_misexecution"]]}
    out = ROOT / "acceptance/reports/real_routing_acceptance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1

if __name__ == "__main__":
    raise SystemExit(main())

