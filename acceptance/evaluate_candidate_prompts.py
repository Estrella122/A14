#!/usr/bin/env python3
"""Exploratory evaluation for authored prompts; never reports production accuracy."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from django.conf import settings
if not settings.configured:
    settings.configure(BASE_DIR=ROOT)
from core.skills.runtime import plan_skills
from acceptance.evaluate_real_routing import predicted_stop

source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "acceptance/vapor_pressure_candidate_prompts.jsonl"
rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
results = []
for row in rows:
    plan = plan_skills(row["text"])
    actual = plan.get("direct_skill_ids", [])
    item = {**row, "actual_labels": actual, "actual_mode": plan["mode"],
            "actual_stop_after": predicted_stop(plan),
            "needs_clarification": plan.get("analysis", {}).get("needs_clarification"),
            "labels_match": set(actual) == set(row["labels"]),
            "mode_match": plan["mode"] == row["mode"],
            "stage_match": predicted_stop(plan) == row["stop_after"]}
    results.append(item)
n = len(results)
report = {
    "dataset": source.name,
    "source_type": "assistant_authored_dataset_specific_candidate_prompts",
    "production_accuracy_claim": False,
    "purpose": "发现路由缺口；经中控人员改写和双人复核后才能进入真实验收集",
    "case_count": n,
    "metrics": {
        "labels_match": sum(r["labels_match"] for r in results) / n,
        "mode_match": sum(r["mode_match"] for r in results) / n,
        "stage_match": sum(r["stage_match"] for r in results) / n,
    },
    "mismatch_count": sum(not (r["labels_match"] and r["mode_match"] and r["stage_match"]) for r in results),
    "mismatches": [r for r in results if not (r["labels_match"] and r["mode_match"] and r["stage_match"])],
    "all_results": results,
}
out = ROOT / "acceptance/reports/vapor_pressure_candidate_prompt_results.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in {"mismatches", "all_results"}}, ensure_ascii=False, indent=2))
