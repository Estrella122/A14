from __future__ import annotations

import tempfile
import json
import threading
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .services.pipeline import PipelineError, STAGES, _json_safe, _persist_snapshot, get_run, list_runs, rerun_pipeline, resolve_artifact, run_pipeline
from .services.jobs import enqueue, start_local_worker


MAX_UPLOAD_BYTES = 200 * 1024 * 1024

WORKFLOW_STAGE_BY_NODE = {
    "source": "standardization",
    "cleaning": "cleaning",
    "selection": "selection",
    "lag": "modeling",
    "collinearity": "modeling",
    "identification": "modeling",
    "evaluation": "modeling",
    "optimization": "optimization",
    "report": "report",
}
WORKFLOW_STAGE_ORDER = ["standardization", "cleaning", "selection", "modeling", "optimization", "review", "report"]


def _mapping_overrides(value) -> dict[str, str]:
    if not value:
        return {}
    parsed = value if isinstance(value, dict) else json.loads(value)
    if not isinstance(parsed, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in parsed.items()):
        raise ValueError("字段映射 overrides 必须是字符串到字符串的 JSON 对象。")
    return parsed


def _response(payload, status=200):
    from .services.evidence_values import final_result_view
    data = payload.get('data')
    if isinstance(data, dict) and data.get('run_id') and 'results' in data:
        payload = {**payload, 'data': final_result_view(data)}
    response = JsonResponse(
        _json_safe(payload),
        status=status,
        json_dumps_params={"ensure_ascii": False, "allow_nan": False},
    )
    return response


def _legacy_async_for_unmigrated_database(temporary: Path, options: dict, ready: threading.Event, state: dict) -> None:
    """Compatibility fallback used only when the durable queue tables are unavailable."""
    def created(snapshot):
        state["run_id"] = snapshot["run_id"]
        ready.set()
    try:
        run_pipeline(temporary, on_created=created, **options)
    except Exception as exc:
        state["error"] = str(exc)
        ready.set()


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
        from .security import run_accessible
        runs = [run for run in runs if run_accessible(request, run)]
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
        upload_started = perf_counter()
        upload_started_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        handle = tempfile.NamedTemporaryFile(prefix="processpilot_", suffix=".csv", delete=False)
        temporary = Path(handle.name)
        with handle:
            for chunk in upload.chunks():
                handle.write(chunk)
        upload_ms = round((perf_counter() - upload_started) * 1000, 3)
        upload_finished_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        from .asset_api import register_asset, visible_assets, owner
        import hashlib
        if request.POST.get('asset_id'):
            asset = visible_assets(request).filter(asset_id=request.POST['asset_id'], status='active').first()
            if not asset or asset.content_hash != hashlib.sha256(temporary.read_bytes()).hexdigest():
                raise ValueError('资产不存在、已归档或内容与所选资产不一致。')
        else:
            asset = register_asset(temporary, upload.name, request)
        options = dict(
            asset_id=asset.asset_id, owner_id=owner(request),
            original_name=upload.name,
            scenario_id=request.POST.get("scenario_id", "auto"),
            project_scene=request.POST.get("project_scene", ""),
            instruction=request.POST.get("instruction", ""),
            resample_rule=request.POST.get("resample_rule"),
            max_lag=int(request.POST["max_lag"]) if "max_lag" in request.POST else None,
            parameters=json.loads(request.POST["parameters"]) if "parameters" in request.POST else None,
            overrides=_mapping_overrides(request.POST.get("overrides")),
            ingest_timing={"csv_upload_ms": upload_ms, "spans": {"csv_upload": {"start_time": upload_started_at, "end_time": upload_finished_at, "elapsed_ms": upload_ms}}},
        )
        if request.POST.get("async_analysis", "").lower() in {"1", "true", "yes"}:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8]
            input_dir = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / "job_inputs"
            input_dir.mkdir(parents=True, exist_ok=True)
            queued_source = input_dir / f"{run_id}.csv"
            temporary.replace(queued_source)
            temporary = None
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            snapshot = {
                "run_id": run_id, "asset_id": asset.asset_id, "owner_id": owner(request), "project": "A14", "status": "queued", "current_stage": "queued",
                "original_name": upload.name, "project_scene": options["project_scene"] or None,
                "scenario_request": options["scenario_id"], "instruction": options["instruction"],
                "mapping_overrides": options["overrides"], "created_at": now, "updated_at": now,
                "stages": [{"key": key, "label": label, "status": "pending", "message": "等待 Worker"} for key, label in STAGES],
                "artifacts": {}, "results": {},
            }
            persisted = _persist_snapshot(snapshot)
            if not persisted:
                queued_source.replace(temporary := Path(tempfile.mkstemp(prefix="processpilot_compat_", suffix=".csv")[1]))
                ready, state = threading.Event(), {}
                threading.Thread(target=_legacy_async_for_unmigrated_database, args=(temporary, options, ready, state), daemon=True).start()
                if not ready.wait(10) or not state.get("run_id"):
                    return _response({"ok": False, "message": state.get("error") or "流水线任务创建失败。"}, status=422)
                return _response({"ok": True, "data": get_run(state["run_id"])}, status=202)
            job = enqueue("pipeline", {"source_path": str(queued_source), "run_id": run_id, **options}, result_ref=run_id)
            snapshot["job"] = {"job_id": job.job_id, "status": job.status, "durable": True}
            _persist_snapshot(snapshot)
            start_local_worker()
            return _response({"ok": True, "data": snapshot}, status=202)
        snapshot = run_pipeline(temporary, **options)
        return _response({"ok": True, "data": snapshot}, status=201)
    except (PipelineError, ValueError) as exc:
        if temporary and temporary.exists():
            temporary.unlink()
        return _response({"ok": False, "message": str(exc), "data": None}, status=422)


@require_GET
def pipeline_latest(request):
    from .security import run_accessible
    snapshot = next((run for run in list_runs(500) if run_accessible(request, run)), None) if settings.PROCESSPILOT_REQUIRE_AUTH else get_run()
    if not snapshot:
        return _response({"ok": True, "data": None})
    return _response({"ok": True, "data": snapshot})


@require_GET
def pipeline_detail(request, run_id):
    snapshot = get_run(run_id)
    if not snapshot:
        return _response({"ok": False, "message": "运行任务不存在。"}, status=404)
    return _response({"ok": True, "data": snapshot})


@require_POST
def pipeline_rerun(request, run_id):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        snapshot = rerun_pipeline(
            run_id,
            resample_rule=payload.get("resample_rule"),
            max_lag=payload.get("max_lag"),
            parameters=payload.get("parameters"),
            scenario_id=payload.get("scenario_id"),
            overrides=_mapping_overrides(payload["overrides"]) if "overrides" in payload else None,
        )
        return _response({"ok": True, "data": snapshot}, status=201)
    except (PipelineError, ValueError, json.JSONDecodeError) as exc:
        return _response({"ok": False, "message": str(exc), "data": None}, status=422)


@require_POST
def pipeline_workflow_execute(request):
    """Validate a visual graph and execute it through the real canonical pipeline."""
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        run_id = str(payload.get("run_id", "")).strip()
        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        if not run_id:
            raise ValueError("请先上传 CSV，再执行可视化流水线。")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("流水线至少需要一个节点。")
        if not isinstance(edges, list):
            raise ValueError("流水线连线格式无效。")

        node_by_id = {}
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                raise ValueError("流水线节点格式无效。")
            node_type = node.get("type")
            if node_type not in WORKFLOW_STAGE_BY_NODE:
                raise ValueError(f"暂不支持节点类型：{node_type}")
            if node["id"] in node_by_id:
                raise ValueError("流水线节点 ID 不能重复。")
            node_by_id[node["id"]] = node
        if not any(node.get("type") == "source" for node in nodes):
            raise ValueError("真实执行必须包含数据源节点。")

        indegree = {node_id: 0 for node_id in node_by_id}
        outgoing = {node_id: [] for node_id in node_by_id}
        for edge in edges:
            source, target = edge.get("from"), edge.get("to")
            if source not in node_by_id or target not in node_by_id or source == target:
                raise ValueError("流水线包含无效连线。")
            source_stage = WORKFLOW_STAGE_ORDER.index(WORKFLOW_STAGE_BY_NODE[node_by_id[source]["type"]])
            target_stage = WORKFLOW_STAGE_ORDER.index(WORKFLOW_STAGE_BY_NODE[node_by_id[target]["type"]])
            if source_stage > target_stage:
                raise ValueError("真实流水线不支持逆向阶段连线。")
            indegree[target] += 1
            outgoing[source].append(target)
        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = []
        while queue:
            node_id = queue.pop(0)
            visited.append(node_id)
            for target in outgoing[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        if len(visited) != len(nodes):
            raise ValueError("流水线存在循环连线。")

        requested_stages = [WORKFLOW_STAGE_BY_NODE[node["type"]] for node in nodes]
        stop_after = max(requested_stages, key=WORKFLOW_STAGE_ORDER.index)
        cleaning_node = next((node for node in nodes if node.get("type") == "cleaning"), {})
        lag_node = next((node for node in nodes if node.get("type") == "lag"), {})
        resample_rule = str((cleaning_node.get("config") or {}).get("resample", "10s"))
        max_lag = int((lag_node.get("config") or {}).get("maxLag", 60))
        snapshot = rerun_pipeline(run_id, resample_rule=resample_rule, max_lag=max_lag, stop_after=stop_after)
        stage_status = {stage["key"]: stage["status"] for stage in snapshot.get("stages", [])}
        workflow = {
            "mode": "canonical_backend_execution",
            "requested_node_count": len(nodes),
            "executed_through": stop_after,
            "included_dependencies": [stage for stage in WORKFLOW_STAGE_ORDER if WORKFLOW_STAGE_ORDER.index(stage) <= WORKFLOW_STAGE_ORDER.index(stop_after)],
            "nodes": [{"id": node["id"], "type": node["type"], "status": stage_status.get(WORKFLOW_STAGE_BY_NODE[node["type"]], "skipped")} for node in nodes],
        }
        return _response({"ok": True, "data": {"run": snapshot, "workflow": workflow}}, status=201)
    except (PipelineError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return _response({"ok": False, "message": str(exc)}, status=422)


@require_GET
def pipeline_artifact(request, run_id, artifact_key):
    try:
        path, name = resolve_artifact(run_id, artifact_key)
    except PipelineError as exc:
        return _response({"ok": False, "message": str(exc)}, status=404)
    return FileResponse(path.open("rb"), as_attachment=True, filename=name)
