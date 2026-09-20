from __future__ import annotations

import socket
import shutil
import tempfile
import threading
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from core.models import RuntimeJob


WORKER_ID = f"{socket.gethostname()}:{threading.get_native_id()}"


def enqueue(job_type: str, payload: dict[str, Any], *, result_ref: str = "", max_attempts: int = 3,
            request_id: str = "", caller_id: str = "", tool_name: str = "",
            idempotency_fingerprint: str | None = None) -> RuntimeJob:
    return RuntimeJob.objects.create(
        job_id=f"job_{uuid4().hex[:16]}", job_type=job_type, payload=payload,
        result_ref=result_ref, max_attempts=max_attempts, request_id=request_id,
        caller_id=caller_id, tool_name=tool_name,
        idempotency_fingerprint=idempotency_fingerprint,
    )


def recover_stale_jobs(stale_after_seconds: int = 900) -> int:
    cutoff = timezone.now() - timedelta(seconds=stale_after_seconds)
    return RuntimeJob.objects.filter(status="running", locked_at__lt=cutoff).update(
        status="queued", locked_by="", locked_at=None, error="执行节点失联，任务已自动重新排队。",
    )


def claim_next() -> RuntimeJob | None:
    with transaction.atomic():
        job = (
            RuntimeJob.objects.select_for_update(skip_locked=True)
            .filter(status="queued", available_at__lte=timezone.now(), attempts__lt=models_f("max_attempts"))
            .order_by("created_at")
            .first()
        )
        if not job:
            return None
        job.status = "running"
        job.attempts += 1
        job.locked_by = WORKER_ID
        job.locked_at = timezone.now()
        job.started_at = job.started_at or timezone.now()
        job.save(update_fields=("status", "attempts", "locked_by", "locked_at", "started_at", "updated_at"))
        return job


def models_f(field: str):
    # Kept behind a helper so the queue query remains readable.
    from django.db.models import F
    return F(field)


def execute(job: RuntimeJob) -> None:
    try:
        if job.job_type == "pipeline":
            _execute_pipeline(job)
        elif job.job_type == "agent_chat":
            _execute_agent_chat(job)
        elif job.job_type == "mcp_pipeline":
            _execute_mcp_pipeline(job)
        else:
            raise ValueError(f"未知后台任务类型：{job.job_type}")
        refreshed_status = RuntimeJob.objects.filter(pk=job.pk).values_list("status", flat=True).first()
        if refreshed_status not in {"blocked", "cancelled", "failed", "timed_out"}:
            RuntimeJob.objects.filter(pk=job.pk).update(status="completed", error="", error_code="")
        RuntimeJob.objects.filter(pk=job.pk).update(
            finished_at=timezone.now(), locked_by="", locked_at=None,
        )
    except Exception as exc:
        refreshed = RuntimeJob.objects.get(pk=job.pk)
        terminal = refreshed.job_type in {"pipeline", "mcp_pipeline"} or refreshed.attempts >= refreshed.max_attempts
        failure_status = "failed"
        if refreshed.job_type in {"pipeline", "mcp_pipeline"}:
            from .pipeline import get_run
            result_id = refreshed.payload.get('target_run_id') or refreshed.payload.get('run_id') or refreshed.result_ref
            recorded = get_run(result_id) if result_id else None
            if recorded and recorded.get('status') in {'cancelled', 'timed_out'}:
                failure_status = recorded['status']
        RuntimeJob.objects.filter(pk=job.pk).update(
            status=failure_status if terminal else "queued", error=str(exc), error_code="TIMEOUT" if failure_status == "timed_out" else "EXECUTION_FAILED",
            finished_at=timezone.now() if terminal else None, locked_by="", locked_at=None,
            available_at=timezone.now() + timedelta(seconds=min(30, 2 ** refreshed.attempts)),
        )


def _execute_pipeline(job: RuntimeJob) -> None:
    from core.services.pipeline import run_pipeline
    payload = dict(job.payload)
    source_path = Path(payload.pop("source_path"))
    run_id = payload.pop("run_id")
    if not source_path.is_file():
        raise FileNotFoundError("排队任务的上传文件不存在。")
    # The canonical pipeline moves its input into the run directory. Execute on
    # a private copy so the queued source remains available for bounded retries.
    handle = tempfile.NamedTemporaryFile(prefix=f"processpilot_job_{job.job_id}_", suffix=".csv", delete=False)
    attempt_source = Path(handle.name)
    handle.close()
    shutil.copy2(source_path, attempt_source)
    try:
        snapshot = run_pipeline(attempt_source, run_id=run_id, cancel_check=lambda: RuntimeJob.objects.filter(pk=job.pk, cancel_requested_at__isnull=False).exists(), **payload)
    finally:
        attempt_source.unlink(missing_ok=True)
    source_path.unlink(missing_ok=True)
    RuntimeJob.objects.filter(pk=job.pk).update(result_ref=run_id, status="blocked" if snapshot.get("status") == "needs_review" else snapshot.get("status", "completed"), error=snapshot.get("stop_reason", ""))


def _execute_agent_chat(job: RuntimeJob) -> None:
    from core.services.agent_chat import chat
    from core.skills.runtime_events import RuntimeEventStore
    payload = job.payload
    skill_run_id = job.result_ref
    store = RuntimeEventStore(skill_run_id, payload.get("run_id"))
    try:
        result = chat(
            payload.get("message", ""), payload.get("run_id"), payload.get("previous_intent"),
            payload.get("previous_intents"), skill_run_id=skill_run_id, event_sink=store.emit,
            llm_config=payload.get("llm"), parameters=payload.get("parameters"),
        )
        store.finish("completed", result=result)
    except Exception as exc:
        store.emit("run_failed", stage="runtime", status="failed", message=str(exc), metadata={"error_type": type(exc).__name__})
        store.finish("failed", error=str(exc))
        raise


def _execute_mcp_pipeline(job: RuntimeJob) -> None:
    """Run a bounded pipeline stage requested through MCP.

    The source run is immutable. ``rerun_pipeline`` copies its registered source
    into a fresh run, so an MCP request cannot overwrite prior evidence.
    """
    from core.services.pipeline import rerun_pipeline

    if job.cancel_requested_at:
        RuntimeJob.objects.filter(pk=job.pk).update(status="cancelled", finished_at=timezone.now())
        return
    payload = dict(job.payload)
    RuntimeJob.objects.filter(pk=job.pk).update(
        current_stage=payload["stop_after"],
        progress={"completed": 0, "total": 1, "percent": 0},
    )
    snapshot = rerun_pipeline(
        payload["source_run_id"],
        resample_rule=payload.get("resample_rule"),
        max_lag=payload.get("max_lag"),
        parameters=payload.get("parameters"),
        stop_after=payload["stop_after"],
        scenario_id=payload.get("scene_id") or None,
        overrides=payload.get("overrides"),
        new_run_id=payload.get("target_run_id"),
        cancel_check=lambda: RuntimeJob.objects.filter(pk=job.pk, cancel_requested_at__isnull=False).exists(),
    )
    terminal_status = (
        "blocked" if snapshot.get("status") == "needs_review"
        else snapshot["status"] if snapshot.get("status") in {"cancelled", "timed_out", "failed"}
        else "completed"
    )
    RuntimeJob.objects.filter(pk=job.pk).update(
        status=terminal_status,
        result_ref=snapshot["run_id"],
        current_stage=snapshot.get("current_stage", payload["stop_after"]),
        progress={"completed": 1, "total": 1, "percent": 100},
        error_code="QUALITY_GATE_BLOCKED" if terminal_status == "blocked" else "CANCELLED" if terminal_status == "cancelled" else "",
        error=(snapshot.get("review_required") or {}).get("message", "") if terminal_status == "blocked" else "任务已在安全阶段边界取消。" if terminal_status == "cancelled" else "",
    )


def run_one() -> bool:
    close_old_connections()
    recover_stale_jobs(int(getattr(settings, "PROCESSPILOT_JOB_STALE_SECONDS", 900)))
    job = claim_next()
    if not job:
        close_old_connections()
        return False
    execute(job)
    close_old_connections()
    return True


def drain_local_queue(max_jobs: int = 100) -> int:
    processed = 0
    while processed < max_jobs and run_one():
        processed += 1
    return processed


def start_local_worker() -> None:
    """Development convenience only; production uses the run_runtime_worker command."""
    if not getattr(settings, "PROCESSPILOT_INLINE_WORKER", True):
        return
    threading.Thread(target=drain_local_queue, daemon=True, name="processpilot-db-worker").start()
