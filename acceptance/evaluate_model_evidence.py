#!/usr/bin/env python3
"""Apply production-candidate evidence gates to a pipeline snapshot."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from django.conf import settings
if not settings.configured:
    settings.configure(BASE_DIR=ROOT)
from core.services.pipeline import get_run

def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    snapshot = get_run(run_id)
    if not snapshot:
        print("没有可验收的流水线任务。", file=sys.stderr)
        return 2
    model = snapshot.get("results", {}).get("modeling", {})
    review = snapshot.get("results", {}).get("review", {})
    diagnostic_root = model.get("diagnostics", {})
    diagnostics = diagnostic_root.get("test", diagnostic_root)
    multi = diagnostics.get("multi_step", {})
    free = diagnostics.get("free_simulation", {})
    improvement = diagnostics.get("rmse_improvement_over_persistence_pct")
    gates = {
        "review_passed": review.get("passed") is True,
        "external_inputs_fitted": bool(model.get("fitted_inputs")),
        "test_beats_persistence_by_1pct": improvement is not None and float(improvement) >= 1,
        "ten_step_prediction_available": bool(multi.get("metrics")) and not multi.get("diverged", False),
        "free_simulation_valid": bool(free.get("metrics")) and not free.get("diverged", False) and float(free.get("metrics", {}).get("r2", -1)) >= 0,
        "stable_ar_poles": diagnostic_root.get("stable_ar_poles") is True,
        "residual_diagnostics_available": bool(diagnostics.get("residual")),
        "single_final_test_evaluation": snapshot.get("results", {}).get("optimization", {}).get("test_evaluations") == 1,
    }
    report = {"run_id": snapshot["run_id"], "status": "candidate_passed" if all(gates.values()) else "blocked",
              "gates": gates, "blockers": [name for name, passed in gates.items() if not passed],
              "model_family": model.get("config", {}).get("family"), "fitted_inputs": model.get("fitted_inputs", []),
              "test_metrics": model.get("metrics", {}).get("test", {}),
              "baseline_improvement_pct": improvement,
              "review_conclusion": review.get("conclusion")}
    out = ROOT / "acceptance/reports/model_evidence_acceptance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "candidate_passed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
