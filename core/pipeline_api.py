from __future__ import annotations

import tempfile
import json
from pathlib import Path

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .services.pipeline import PipelineError, get_run, list_runs, rerun_pipeline, resolve_artifact, run_pipeline


MAX_UPLOAD_BYTES = 200 * 1024 * 1024


def _mapping_overrides(value) -> dict[str, str]:
    if not value:
        return {}
    parsed = value if isinstance(value, dict) else json.loads(value)
    if not isinstance(parsed, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in parsed.items()):
        raise ValueError("字段映射 overrides 必须是字符串到字符串的 JSON 对象。")
    return parsed


def _response(payload, status=200):
    response = JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def pipeline_collection(request):
    if request.method == "OPTIONS":
        return _response({"ok": True})
    if request.method == "GET":
        try:
            limit = int(request.GET.get("limit", "100"))
        except ValueError:
            limit = 100
        scenario_id = request.GET.get("scenario_id", "").strip()
        runs = list_runs(limit, scenario_id=scenario_id) if scenario_id else list_runs(limit)
        return _response({"ok": True, "data": runs})
    upload = request.FILES.get("file")
    if upload is None:
        return _response({"ok": False, "message": "请选择CSV文件。"}, status=400)
    if not upload.name.lower().endswith(".csv"):
        return _response({"ok": False, "message": "只支持CSV文件。"}, status=400)
    if upload.size > MAX_UPLOAD_BYTES:
        return _response({"ok": False, "message": "CSV文件不能超过200 MB。"}, status=413)

    temporary = None
    try:
        handle = tempfile.NamedTemporaryFile(prefix="processpilot_", suffix=".csv", delete=False)
        temporary = Path(handle.name)
        with handle:
            for chunk in upload.chunks():
                handle.write(chunk)
        snapshot = run_pipeline(
            temporary,
            original_name=upload.name,
            scenario_id=request.POST.get("scenario_id", "auto"),
            instruction=request.POST.get("instruction", ""),
            resample_rule=request.POST.get("resample_rule", "10s"),
            max_lag=int(request.POST.get("max_lag", "60")),
            overrides=_mapping_overrides(request.POST.get("overrides")),
        )
        return _response({"ok": True, "data": snapshot}, status=201)
    except (PipelineError, ValueError) as exc:
        if temporary and temporary.exists():
            temporary.unlink()
        return _response({"ok": False, "message": str(exc), "data": get_run()}, status=422)


@require_GET
def pipeline_latest(request):
    snapshot = get_run()
    if not snapshot:
        return _response({"ok": True, "data": None})
    return _response({"ok": True, "data": snapshot})


@require_GET
def pipeline_detail(request, run_id):
    snapshot = get_run(run_id)
    if not snapshot:
        return _response({"ok": False, "message": "运行任务不存在。"}, status=404)
    return _response({"ok": True, "data": snapshot})


@csrf_exempt
@require_POST
def pipeline_rerun(request, run_id):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        snapshot = rerun_pipeline(
            run_id,
            resample_rule=payload.get("resample_rule", "10s"),
            max_lag=int(payload.get("max_lag", 60)),
            scenario_id=payload.get("scenario_id"),
            overrides=_mapping_overrides(payload["overrides"]) if "overrides" in payload else None,
        )
        return _response({"ok": True, "data": snapshot}, status=201)
    except (PipelineError, ValueError, json.JSONDecodeError) as exc:
        return _response({"ok": False, "message": str(exc), "data": get_run()}, status=422)


@require_GET
def pipeline_artifact(request, run_id, artifact_key):
    try:
        path, name = resolve_artifact(run_id, artifact_key)
    except PipelineError as exc:
        return _response({"ok": False, "message": str(exc)}, status=404)
    return FileResponse(path.open("rb"), as_attachment=True, filename=name)
