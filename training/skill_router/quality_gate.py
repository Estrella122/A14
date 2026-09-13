#!/usr/bin/env python3
"""Fail closed when the frozen Skill-router acceptance report is stale or below target."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = Path(__file__).parent / "reports" / "acceptance.json"
MODEL_PATH = ROOT / "core" / "skills" / "models" / "skill_router.json.gz"
TEST_PATH = Path(__file__).parent / "data" / "test.jsonl"
THRESHOLDS = {
    "exact_skill_set_accuracy": 0.95,
    "micro_precision": 0.95,
    "micro_recall": 0.95,
    "out_of_scope_rejection": 0.95,
    "minimum_per_skill_f1": 0.75,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(report_path: Path = DEFAULT_REPORT) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report["trained_router"]
    checks = {
        key: float(metrics[key]) >= threshold
        for key, threshold in THRESHOLDS.items()
        if key != "minimum_per_skill_f1"
    }
    minimum = min((float(row["f1"]) for row in metrics["per_skill"] if int(row.get("support", 0)) > 0), default=0.0)
    checks["minimum_per_skill_f1"] = minimum >= THRESHOLDS["minimum_per_skill_f1"]
    checks["model_report_is_current"] = report.get("model_sha256") == sha256(MODEL_PATH)
    checks["holdout_report_is_current"] = report.get("test_sha256") == sha256(TEST_PATH)
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "thresholds": THRESHOLDS,
        "observed": {**{key: metrics[key] for key in THRESHOLDS if key != "minimum_per_skill_f1"},
                     "minimum_per_skill_f1": minimum},
        "production_accuracy_claim": False,
        "limitations": report.get("limitations", []),
    }


def main() -> int:
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
