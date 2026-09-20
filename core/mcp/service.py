from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime

import pandas as pd
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import RuntimeJob
from core.services.jobs import enqueue, start_local_worker
from core.services.pipeline import PipelineError, get_run, list_runs, resolve_artifact
from core.skills.artifacts import LEGACY_ARTIFACT_TYPES, RuntimeArtifactResolver
from core.skills.contracts import SKILL_CONTRACTS


SCHEMA_VERSION = "processpilot-mcp-result-v1"
OBSERVABILITY_SCHEMA_VERSION = "processpilot-mcp-observability-v1"
CONTROL_MODE = "advisory_only"

PIPELINE_STAGE_LABELS = {
    "standardization": "数据与字段校验",
    "cleaning": "时间对齐、清洗与训练集冻结",
    "selection": "动态检测、SNR 估算与数据段评分",
    "modeling": "时滞补偿、共线性降维与辨识验证",
    "optimization": "预处理策略反馈搜索与最佳候选冻结",
}

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "run_dynamic_selection": {
        "stop_after": "selection",
        "stage": "selection",
        "skills": (
            "steady_transient_state_detector",
            "signal_noise_ratio_estimator",
            "high_snr_dynamic_segment_extractor",
            "segment_quality_scorer_ranker",
        ),
        "quality_gates": (
            "training_partition_only",
            "minimum_valid_samples",
            "score_components_available",
            "no_synthetic_fallback",
        ),
    },
    "run_decoupling_identification": {
        "stop_after": "modeling",
        "stage": "modeling",
        "skills": (
            "time_delay_estimator_compensator",
            "collinearity_detector_reducer",
            "arx_structure_order_selector",
            "system_identification_trainer",
            "multi_model_benchmark",
            "model_diagnostics_evaluator",
        ),
        "quality_gates": (
            "causal_delay",
            "maximum_lag_bound",
            "vif_or_correlation_evidence",
            "common_validation_targets",
            "reproducible_fit",
            "residual_diagnostics",
        ),
    },
    "run_closed_loop_optimization": {
        "stop_after": "optimization",
        "stage": "optimization",
        "skills": (
            "closed_loop_preprocessing_optimizer",
            "model_diagnostics_evaluator",
        ),
        "quality_gates": (
            "real_data_only",
            "frozen_split_unchanged",
            "validation_hash_identical_across_candidates",
            "test_not_in_objective",
            "single_final_test",
            "bounded_search",
            "stopping_reason_recorded",
        ),
    },
}


class MCPServiceError(ValueError):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

    def public(self) -> dict[str, Any]:
        return {"error_code": self.code, "message": str(self), "retryable": self.retryable}


def _fingerprint(caller_id: str, tool_name: str, idempotency_key: str) -> str | None:
    if not idempotency_key:
        return None
    material = f"{caller_id}\0{tool_name}\0{idempotency_key}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _validate_common(source_run_id: str, scene_id: str, resample_rule: str, max_lag: int) -> dict[str, Any]:
    if not source_run_id or not source_run_id.replace("_", "").isalnum():
        raise MCPServiceError("INVALID_ARGUMENT", "source_run_id 格式无效。")
    source = get_run(source_run_id)
    if not source:
        raise MCPServiceError("DATASET_NOT_FOUND", "源运行不存在。")
    try:
        resolve_artifact(source_run_id, "source_csv")
    except PipelineError as exc:
        raise MCPServiceError("ARTIFACT_PRECONDITION_MISSING", "源运行缺少可复用的 SOURCE_DATA。") from exc
    if scene_id != "auto" and not scene_id.replace("_", "").isalnum():
        raise MCPServiceError("INVALID_ARGUMENT", "scene_id 格式无效。")
    if resample_rule is not None and (not resample_rule or len(resample_rule) > 20):
        raise MCPServiceError("INVALID_ARGUMENT", "resample_rule 格式无效。")
    if max_lag is not None and (isinstance(max_lag, bool) or not isinstance(max_lag, int) or not 1 <= max_lag <= 600):
        raise MCPServiceError("INVALID_ARGUMENT", "max_lag 必须在 1 到 600 之间。")
    return source


def enqueue_modeling_tool(
    tool_name: str,
    source_run_id: str,
    *,
    caller_id: str = "local-agent",
    idempotency_key: str = "",
    scene_id: str = "auto",
    resample_rule: str | None = None,
    max_lag: int | None = None,
    parameters: dict | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    if tool_name not in TOOL_SPECS:
        raise MCPServiceError("INVALID_ARGUMENT", f"未知 MCP 工具：{tool_name}")
    source = _validate_common(source_run_id, scene_id, resample_rule, max_lag)
    from core.services.algorithm_policy import snapshot_policy, PolicyError
    requested = dict(parameters or {})
    if resample_rule is not None:
        requested["resample_rule"] = resample_rule
    if max_lag is not None:
        requested["max_lag"] = max_lag
    try:
        snapshot_policy(source, requested)
    except PolicyError as exc:
        raise MCPServiceError("INVALID_ARGUMENT", str(exc)) from exc
    if not caller_id or len(caller_id) > 160:
        raise MCPServiceError("INVALID_ARGUMENT", "caller_id 格式无效。")
    if len(idempotency_key) > 200:
        raise MCPServiceError("INVALID_ARGUMENT", "idempotency_key 不能超过 200 个字符。")
    if overrides is not None and (
        not isinstance(overrides, dict)
        or not all(isinstance(key, str) and isinstance(value, str) for key, value in overrides.items())
    ):
        raise MCPServiceError("INVALID_ARGUMENT", "overrides 必须是字符串到字符串的对象。")

    spec = TOOL_SPECS[tool_name]
    fingerprint = _fingerprint(caller_id, tool_name, idempotency_key)
    if fingerprint:
        existing = RuntimeJob.objects.filter(idempotency_fingerprint=fingerprint).first()
        if existing:
            return job_result(existing, reused=True)

    request_id = f"req_{uuid4().hex[:16]}"
    target_run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8]
    payload = {
        "source_run_id": source_run_id,
        "target_run_id": target_run_id,
        "stop_after": spec["stop_after"],
        "scene_id": scene_id,
        "resample_rule": resample_rule,
        "max_lag": max_lag,
        "parameters": parameters,
        "overrides": overrides,
    }
    try:
        with transaction.atomic():
            job = enqueue(
                "mcp_pipeline",
                payload,
                result_ref=target_run_id,
                request_id=request_id,
                caller_id=caller_id,
                tool_name=tool_name,
                idempotency_fingerprint=fingerprint,
                max_attempts=2,
            )
    except IntegrityError:
        job = RuntimeJob.objects.get(idempotency_fingerprint=fingerprint)
        return job_result(job, reused=True)
    start_local_worker()
    return job_result(job)


def cancel_job(job_id: str, *, caller_id: str = "local-agent") -> dict[str, Any]:
    job = RuntimeJob.objects.filter(job_id=job_id).first()
    if not job:
        raise MCPServiceError("JOB_NOT_FOUND", "任务不存在。")
    if job.caller_id and job.caller_id != caller_id:
        raise MCPServiceError("ACCESS_DENIED", "无权取消其他调用方创建的任务。")
    if job.status in {"completed", "blocked", "failed", "cancelled"}:
        return job_result(job)
    now = timezone.now()
    updates: dict[str, Any] = {"cancel_requested_at": now}
    if job.status == "queued":
        updates.update(status="cancelled", finished_at=now, error_code="CANCELLED", error="任务在开始前已取消。")
    RuntimeJob.objects.filter(pk=job.pk).update(**updates)
    return job_result(RuntimeJob.objects.get(pk=job.pk))


def _progress_from_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {"completed": 0, "total": 0, "percent": 0}
    stages = [row for row in snapshot.get("stages", []) if row.get("status") != "skipped"]
    completed = sum(row.get("status") == "completed" for row in stages)
    total = len(stages)
    return {"completed": completed, "total": total, "percent": round(100 * completed / total, 1) if total else 0}


def _execution_timeline(tool_name: str, snapshot: dict[str, Any] | None, job: RuntimeJob) -> list[dict[str, Any]]:
    """Return a stable, UI-ready operational trace without exposing Agent reasoning."""
    stop_after = TOOL_SPECS.get(tool_name, {}).get("stop_after")
    ordered_keys = list(PIPELINE_STAGE_LABELS)
    if stop_after in ordered_keys:
        ordered_keys = ordered_keys[: ordered_keys.index(stop_after) + 1]
    snapshot_rows = {row.get("key"): row for row in (snapshot or {}).get("stages", [])}
    timeline = []
    for index, key in enumerate(ordered_keys, start=1):
        source = snapshot_rows.get(key, {})
        status = source.get("status")
        if not status:
            if job.status == "queued":
                status = "queued" if index == 1 else "pending"
            elif job.status == "running":
                status = "running" if index == 1 else "pending"
            else:
                status = "pending"
        if status == "skipped" and (snapshot or {}).get("status") == "completed":
            status = "not_requested"
        timeline.append({
            "sequence": index,
            "stage": key,
            "label": PIPELINE_STAGE_LABELS[key],
            "status": status,
            "message": source.get("message") or ("等待前序阶段完成" if status == "pending" else ""),
            "started_at": source.get("started_at"),
            "finished_at": source.get("finished_at"),
            "elapsed_ms": source.get("elapsed_ms"),
        })
    return timeline


def _artifact_refs(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    resolver = RuntimeArtifactResolver(snapshot)
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for legacy_key in snapshot.get("artifacts", {}):
        artifact_type = LEGACY_ARTIFACT_TYPES.get(legacy_key)
        if not artifact_type or artifact_type in seen:
            continue
        ref = resolver.resolve(artifact_type)
        if ref:
            public = ref.public()
            public.pop("path", None)
            refs.append(public)
            seen.add(artifact_type)
    return refs


def _gate_results(tool_name: str, snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not snapshot:
        return [{"gate": gate, "status": "pending"} for gate in TOOL_SPECS.get(tool_name, {}).get("quality_gates", ())]
    results = snapshot.get("results", {})
    modeling = results.get("modeling", {})
    optimization = results.get("optimization", {})
    diagnostics = modeling.get("diagnostics", {})
    lags = modeling.get("lags", [])
    collinearity = modeling.get("collinearity", {})
    split = results.get("cleaning", {}).get("split", {})
    selection = results.get("selection", {})
    facts: dict[str, bool | None] = {
        "training_partition_only": bool(results.get("cleaning", {}).get("split")),
        "minimum_valid_samples": int(selection.get("selected_segment_count") or 0) > 0,
        "score_components_available": bool(results.get("cleaning", {}).get("segments_preview")),
        "no_synthetic_fallback": optimization.get("synthetic_fallback") is not True,
        "causal_delay": bool(lags) and all(int(row.get("delay_samples", -1)) >= 0 for row in lags),
        "maximum_lag_bound": bool(lags) and all(int(row.get("delay_samples", 0)) <= int(row.get("max_lag", -1)) for row in lags),
        "vif_or_correlation_evidence": bool(collinearity.get("vif") or collinearity.get("matrix")),
        "common_validation_targets": bool(diagnostics.get("evaluation_target_hash") or optimization.get("validation_target_hash")),
        "reproducible_fit": bool(modeling.get("config")),
        "residual_diagnostics": bool(diagnostics),
        "real_data_only": optimization.get("synthetic_fallback") is False,
        "frozen_split_unchanged": bool(split.get("protocol") and optimization.get("validation_target_hash")),
        "validation_hash_identical_across_candidates": optimization.get("validation_target_hash") is not None,
        "test_not_in_objective": optimization.get("test_used_for_search") is False,
        "single_final_test": optimization.get("test_evaluation_count") == 1,
        "bounded_search": bool(optimization.get("stopping", {}).get("max_rounds")),
        "stopping_reason_recorded": bool(optimization.get("stopping", {}).get("stop_reason")),
    }
    return [{
        "gate": gate,
        "status": "passed" if facts.get(gate) is True else "failed" if facts.get(gate) is False else "unknown",
    } for gate in TOOL_SPECS.get(tool_name, {}).get("quality_gates", ())]


def _metrics(tool_name: str, snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    results = snapshot.get("results", {})
    if tool_name == "run_dynamic_selection":
        return {
            "selection": results.get("selection", {}),
            "overall_quality_score": results.get("cleaning", {}).get("overall_score"),
        }
    if tool_name == "run_decoupling_identification":
        modeling = results.get("modeling", {})
        return {"config": modeling.get("config", {}), "metrics": modeling.get("metrics", {})}
    if tool_name == "run_closed_loop_optimization":
        optimization = results.get("optimization", {})
        return {
            "best_round": optimization.get("best_round"),
            "best_score": optimization.get("best_score"),
            "best_parameters": optimization.get("best_parameters", {}),
            "best_metrics": optimization.get("best_metrics", {}),
            "stopping": optimization.get("stopping", {}),
        }
    return {}


def job_result(job: RuntimeJob, *, reused: bool = False) -> dict[str, Any]:
    snapshot = get_run(job.result_ref) if job.result_ref else None
    status = job.status
    if snapshot and snapshot.get("status") == "needs_review":
        status = "blocked"
    elif snapshot and snapshot.get("status") == "failed":
        status = "failed"
    elif job.tool_name == "run_dynamic_selection" and status == "completed":
        selection = snapshot.get("results", {}).get("selection", {}) if snapshot else {}
        if int(selection.get("selected_segment_count") or 0) == 0 and int(selection.get("modeling_row_count") or 0) > 0:
            status = "partial"
    spec = TOOL_SPECS.get(job.tool_name, {})
    skills = []
    stage_rows = {row.get("key"): row.get("status") for row in (snapshot or {}).get("stages", [])}
    target_stage_status = stage_rows.get(spec.get("stage"))
    if target_stage_status == "completed":
        execution_state = "executed"
    elif status == "blocked":
        execution_state = "blocked"
    elif status == "failed":
        execution_state = "failed"
    else:
        execution_state = "skipped"
    for skill_id in spec.get("skills", ()):
        contract = SKILL_CONTRACTS.get(skill_id)
        skills.append({
            "skill_id": skill_id,
            "contract_version": contract.version if contract else "unknown",
            "executor": contract.executor if contract else "unknown",
            "execution_state": execution_state,
            "status": "pending" if status in {"queued", "running"} else status,
        })
    progress = _progress_from_snapshot(snapshot) if snapshot else (job.progress or {"completed": 0, "total": 1, "percent": 0})
    warnings = []
    if job.tool_name == "run_closed_loop_optimization":
        warnings.append("闭环仅指离线预处理—建模—验证反馈搜索，不代表生产控制闭环。")
    if job.tool_name == "run_dynamic_selection" and status == "partial":
        warnings.append("严格优质动态段为 0；仅保留降级候选建模数据，不能将其表述为高信噪比优质数据。")
    if status == "blocked" and job.error:
        warnings.append(job.error)
    timeline = _execution_timeline(job.tool_name, snapshot, job)
    current = next((row for row in timeline if row["status"] == "running"), None)
    if current is None:
        current = next((row for row in timeline if row["status"] in {"queued", "pending"}), None)
    if current is None and timeline:
        current = timeline[-1]
    return {
        "schema_version": SCHEMA_VERSION,
        "observability_schema_version": OBSERVABILITY_SCHEMA_VERSION,
        "request_id": job.request_id or None,
        "job_id": job.job_id,
        "run_id": job.result_ref or None,
        "source_run_id": job.payload.get("source_run_id"),
        "tool_name": job.tool_name or None,
        "status": status,
        "stage": (snapshot or {}).get("current_stage") or job.current_stage or spec.get("stage"),
        "current_stage": {
            "key": current.get("stage") if current else None,
            "label": current.get("label") if current else None,
            "status": current.get("status") if current else status,
            "message": current.get("message") if current else "",
        },
        "progress": progress,
        "execution_timeline": timeline,
        "reused_idempotent_request": reused,
        "invoked_skills": skills,
        "output_artifacts": _artifact_refs(snapshot),
        "metrics": _metrics(job.tool_name, snapshot),
        "quality_gates": _gate_results(job.tool_name, snapshot),
        "warnings": warnings,
        "limitations": ["计算完成不等于具备生产投运资格。"],
        "error": {"code": job.error_code or "EXECUTION_FAILED", "message": job.error} if job.error else None,
        "provenance": {
            "code_version": os.getenv("PROCESSPILOT_CODE_VERSION", "development"),
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        },
        "control_mode": CONTROL_MODE,
        "actuation_allowed": False,
    }


def get_job(job_id: str, *, caller_id: str = "local-agent") -> dict[str, Any]:
    job = RuntimeJob.objects.filter(job_id=job_id).first()
    if not job:
        raise MCPServiceError("JOB_NOT_FOUND", "任务不存在。")
    if job.caller_id and job.caller_id != caller_id:
        raise MCPServiceError("ACCESS_DENIED", "无权读取其他调用方创建的任务。")
    return job_result(job)


def list_run_artifacts(run_id: str) -> dict[str, Any]:
    snapshot = get_run(run_id)
    if not snapshot:
        raise MCPServiceError("RUN_NOT_FOUND", "运行不存在。")
    return {"run_id": run_id, "artifacts": _artifact_refs(snapshot), "control_mode": CONTROL_MODE, "actuation_allowed": False}


def list_registered_runs(limit: int = 20, scene_id: str = "") -> dict[str, Any]:
    if not 1 <= int(limit) <= 100:
        raise MCPServiceError("INVALID_ARGUMENT", "limit 必须在 1 到 100 之间。")
    runs = []
    for snapshot in list_runs(int(limit), scenario_id=scene_id or None):
        standard = snapshot.get("results", {}).get("standardization", {})
        runs.append({
            "run_id": snapshot.get("run_id"),
            "status": snapshot.get("status"),
            "current_stage": snapshot.get("current_stage"),
            "original_name": snapshot.get("original_name"),
            "scene": standard.get("scenario", {}),
            "created_at": snapshot.get("created_at"),
            "updated_at": snapshot.get("updated_at"),
            "has_source_data": "source_csv" in snapshot.get("artifacts", {}),
        })
    return {"runs": runs, "count": len(runs), "control_mode": CONTROL_MODE, "actuation_allowed": False}


def search_approved_knowledge(query: str, scene_id: str = "", limit: int = 8) -> dict[str, Any]:
    if not query.strip():
        raise MCPServiceError("INVALID_ARGUMENT", "知识检索 query 不能为空。")
    if len(query) > 1000 or not 1 <= int(limit) <= 20:
        raise MCPServiceError("INVALID_ARGUMENT", "query 或 limit 超出允许范围。")
    from core.services.knowledge_base import search_knowledge

    result = search_knowledge(query, scene_id, int(limit))
    result.update(control_mode=CONTROL_MODE, actuation_allowed=False)
    return result


def artifact_summary(run_id: str, artifact_key: str) -> dict[str, Any]:
    try:
        path, name = resolve_artifact(run_id, artifact_key)
    except PipelineError as exc:
        raise MCPServiceError("ARTIFACT_NOT_FOUND", str(exc)) from exc
    summary: dict[str, Any] = {
        "run_id": run_id,
        "artifact_key": artifact_key,
        "name": name,
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "content_returned": False,
    }
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, nrows=100)
        summary.update(columns=list(frame.columns), preview_rows=min(len(frame), 100), preview_truncated=True)
    elif path.suffix.lower() == ".json" and path.stat().st_size <= 256 * 1024:
        value = json.loads(path.read_text(encoding="utf-8"))
        summary["top_level_keys"] = list(value) if isinstance(value, dict) else []
    return summary


def capabilities_resource() -> str:
    payload = {
        "server": "processpilot-modeling",
        "schema_version": SCHEMA_VERSION,
        "tools": [
            {"name": name, "stage": spec["stage"], "skills": list(spec["skills"]), "quality_gates": list(spec["quality_gates"])}
            for name, spec in TOOL_SPECS.items()
        ],
        "control_mode": CONTROL_MODE,
        "actuation_allowed": False,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def skill_catalog_resource() -> str:
    return json.dumps(
        {skill_id: contract.public() for skill_id, contract in SKILL_CONTRACTS.items()},
        ensure_ascii=False,
        indent=2,
    )


def skill_contract_resource(skill_id: str) -> str:
    contract = SKILL_CONTRACTS.get(skill_id)
    if not contract:
        raise MCPServiceError("SKILL_NOT_FOUND", "Skill 不存在。")
    return json.dumps(contract.public(), ensure_ascii=False, indent=2)


def scene_contract_resource(scene_id: str) -> str:
    from core.services.scene_registry import get_scene_config

    scene = get_scene_config(scene_id)
    if not scene:
        raise MCPServiceError("SCENE_NOT_FOUND", "场景不存在。")
    return json.dumps(scene, ensure_ascii=False, indent=2, default=str)


def run_resource(run_id: str, *, evidence: bool = False) -> str:
    snapshot = get_run(run_id)
    if not snapshot:
        raise MCPServiceError("RUN_NOT_FOUND", "运行不存在。")
    payload = {
        "run_id": run_id,
        "status": snapshot.get("status"),
        "current_stage": snapshot.get("current_stage"),
        "scenario": snapshot.get("results", {}).get("standardization", {}).get("scenario", {}),
        "stages": snapshot.get("stages", []),
        "artifacts": _artifact_refs(snapshot),
    }
    if evidence:
        payload["results"] = snapshot.get("results", {})
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
