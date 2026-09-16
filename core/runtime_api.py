from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from .models import RuntimeJob


def _job_payload(job):
    return {
        "job_id": job.job_id, "job_type": job.job_type, "status": job.status,
        "result_ref": job.result_ref, "error": job.error or None,
        "error_code": job.error_code or None, "request_id": job.request_id or None,
        "tool_name": job.tool_name or None, "current_stage": job.current_stage or None,
        "progress": job.progress or {}, "cancel_requested": bool(job.cancel_requested_at),
        "attempts": job.attempts, "max_attempts": job.max_attempts,
        "locked_by": job.locked_by or None,
        "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat(),
    }


@require_GET
def health(request):
    connection.ensure_connection()
    runtime_root = Path(settings.PROCESSPILOT_RUNTIME_ROOT)
    runtime_root.mkdir(parents=True, exist_ok=True)
    probe = runtime_root / ".healthcheck"
    probe.touch(exist_ok=True)
    from core.mcp.client import check_server
    mcp_status = check_server(getattr(settings, "PROCESSPILOT_MCP_URL", ""))
    return JsonResponse({
        "ok": True, "status": "ready", "database": "ready", "runtime_storage": "ready",
        "queue": {
            "queued": RuntimeJob.objects.filter(status="queued").count(),
            "running": RuntimeJob.objects.filter(status="running").count(),
            "failed": RuntimeJob.objects.filter(status="failed").count(),
        },
        "control_mode": "advisory_only", "actuation_allowed": False,
        "mcp": mcp_status,
    })


@require_http_methods(["GET", "POST", "OPTIONS"])
def job_detail(request, job_id):
    if request.method == "OPTIONS":
        return JsonResponse({"ok": True})
    try:
        job = RuntimeJob.objects.get(job_id=job_id)
    except RuntimeJob.DoesNotExist:
        return JsonResponse({"ok": False, "message": "后台任务不存在"}, status=404)
    if request.method == "POST":
        if job.status != "queued":
            return JsonResponse({"ok": False, "message": "只能取消尚未开始的任务"}, status=409)
        job.status = "cancelled"
        job.save(update_fields=("status", "updated_at"))
    return JsonResponse({"ok": True, "data": _job_payload(job)}, json_dumps_params={"ensure_ascii": False})
