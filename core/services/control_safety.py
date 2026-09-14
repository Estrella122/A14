from __future__ import annotations

from typing import Any


def assess_candidate(study, candidate_run) -> dict[str, Any]:
    payload = candidate_run.candidate_parameters or {}
    failures = list(payload.get("constraint_failures", []))
    checks = [
        {"id": "optimization_constraints", "passed": not failures, "detail": failures},
        {"id": "real_uploaded_dataset", "passed": study.dataset_mode == "uploaded_csv", "detail": study.dataset_mode},
        {"id": "frozen_validation_protocol", "passed": study.dataset_mode == "uploaded_csv", "detail": "60/20/20" if study.dataset_mode == "uploaded_csv" else "simulation"},
        {"id": "human_review_required", "passed": False, "detail": "待独立审批"},
        {"id": "plant_interlock_verified", "passed": False, "detail": "未连接现场联锁"},
        {"id": "shadow_operation_completed", "passed": False, "detail": "尚未完成影子运行"},
    ]
    return {
        "policy_version": "processpilot-control-safety-v1",
        "mode": "advisory_only",
        "candidate_delivery_allowed": not failures,
        "shadow_trial_eligible": not failures and study.dataset_mode == "uploaded_csv",
        "actuation_allowed": False,
        "checks": checks,
        "blocking_checks": [item["id"] for item in checks if not item["passed"]],
        "notice": "本系统只生成离线候选策略和审批记录，不包含 DCS/PLC 指令下发能力。",
    }
