import json
import time
from datetime import datetime
from uuid import uuid4

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST

from .services.agent_chat import chat
from .services.expert_qa import coverage_summary
from .services.pipeline import PipelineError, get_run
from .services.jobs import enqueue, start_local_worker
from .services.llm_gateway import LLMGatewayError, provider_catalog, resolve_llm_config
from .skills import execute_skill_plan, get_skill_run, list_skills, plan_skills
from .skills.runtime_events import RuntimeEventStore, get_runtime_event_store


def _duration_ms(start, end):
    if not start or not end:
        return 0
    try:
        return max(0, int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() * 1000))
    except (TypeError, ValueError):
        return 0


@require_POST
def agent_chat(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        llm_config = _safe_llm_config(payload.get("llm"))
        result = chat(payload.get("message", ""), payload.get("run_id"), payload.get("previous_intent"), payload.get("previous_intents"), llm_config=llm_config)
        return JsonResponse({"ok": True, "data": result}, json_dumps_params={"ensure_ascii": False})
    except (ValueError, PipelineError, LLMGatewayError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=422, json_dumps_params={"ensure_ascii": False})


def _safe_llm_config(value):
    source = value if isinstance(value, dict) else {}
    safe = {key: source.get(key) for key in ("provider", "model", "base_url") if source.get(key) is not None}
    resolve_llm_config(safe)
    return safe


@require_GET
def agent_llm_providers(request):
    return JsonResponse({"ok": True, "data": provider_catalog()}, json_dumps_params={"ensure_ascii": False})


@require_POST
def agent_live_chat(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        message = str(payload.get("message", "")).strip()
        if not message:
            raise ValueError("聊天内容不能为空。")
        if not get_run(payload.get("run_id")):
            raise PipelineError("尚无可分析的流水线任务，请先上传CSV。")
        payload["llm"] = _safe_llm_config(payload.get("llm"))
        skill_run_id = f"skillrun_{uuid4().hex[:12]}"
        RuntimeEventStore(skill_run_id, payload.get("run_id"))
        job = enqueue("agent_chat", payload, result_ref=skill_run_id)
        start_local_worker()
        return JsonResponse({"ok": True, "data": {"skill_run_id": skill_run_id, "run_id": payload.get("run_id"), "status": "queued", "job_id": job.job_id, "durable": True}}, status=202, json_dumps_params={"ensure_ascii": False})
    except (ValueError, PipelineError, LLMGatewayError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=422, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skills(request):
    data = list_skills()
    data["expert_topics"] = coverage_summary()
    return JsonResponse({"ok": True, "data": data}, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skill_detail(request, skill_id):
    from .skills.registry import get_registry
    data = get_registry().get_manifest(skill_id)
    if data is None:
        return JsonResponse({"ok": False, "message": "Skill 不存在"}, status=404)
    return JsonResponse({"ok": True, "data": data}, json_dumps_params={"ensure_ascii": False})


@require_POST
def agent_plan(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        run_id = payload.get("run_id")
        result = plan_skills(payload.get("message", ""), run_id, snapshot=get_run(run_id) if run_id else None)
        return JsonResponse({"ok": True, "data": result}, status=201, json_dumps_params={"ensure_ascii": False})
    except (ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=422, json_dumps_params={"ensure_ascii": False})


@require_POST
def agent_skill_run_collection(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        snapshot = get_run(payload.get("run_id"))
        if not snapshot:
            raise PipelineError("尚无可执行的流水线任务，请先上传 CSV。")
        plan = payload.get("plan") or plan_skills(payload.get("message", "分析当前任务"), snapshot["run_id"], snapshot=snapshot)
        result = execute_skill_plan(plan, snapshot)
        return JsonResponse({"ok": True, "data": result}, status=201, json_dumps_params={"ensure_ascii": False})
    except (ValueError, PipelineError, json.JSONDecodeError, KeyError) as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=422, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skill_run_detail(request, skill_run_id):
    result = get_skill_run(skill_run_id)
    if not result:
        return JsonResponse({"ok": False, "message": "Skill 运行记录不存在。"}, status=404, json_dumps_params={"ensure_ascii": False})
    return JsonResponse({"ok": True, "data": result}, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skill_run_events(request, skill_run_id):
    store = get_runtime_event_store(skill_run_id)
    if store:
        try:
            after = max(0, int(request.GET.get("after", 0)))
            limit = max(1, min(200, int(request.GET.get("limit", 100))))
        except ValueError:
            return JsonResponse({"ok": False, "message": "after 和 limit 必须是整数。"}, status=422, json_dumps_params={"ensure_ascii": False})
        return JsonResponse({"ok": True, "data": store.snapshot(after=after, limit=limit)}, json_dumps_params={"ensure_ascii": False})
    result = get_skill_run(skill_run_id)
    if not result:
        return JsonResponse({"ok": False, "message": "Skill 运行记录不存在。"}, status=404, json_dumps_params={"ensure_ascii": False})
    events = [{"sequence": index, "skill_id": item["skill_id"], "name": item["name"], "status": item["status"], "duration_ms": item["duration_ms"]} for index, item in enumerate(result["executions"], 1)]
    return JsonResponse({"ok": True, "data": {"skill_run_id": skill_run_id, "events": events}}, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skill_run_stream(request, skill_run_id):
    """Stream auditable runtime events and answer deltas over server-sent events."""
    store = get_runtime_event_store(skill_run_id)
    if not store:
        return JsonResponse({"ok": False, "message": "Skill 运行记录不存在。"}, status=404, json_dumps_params={"ensure_ascii": False})
    try:
        after = max(0, int(request.GET.get("after", 0)))
    except ValueError:
        return JsonResponse({"ok": False, "message": "after 必须是整数。"}, status=422, json_dumps_params={"ensure_ascii": False})

    def encode(event_name, payload):
        return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

    def event_stream():
        cursor = after
        yield "retry: 1000\n: ProcessPilot runtime stream connected\n\n"
        while True:
            snapshot = store.snapshot(after=cursor, limit=100)
            for event in snapshot.get("events", []):
                cursor = max(cursor, int(event.get("sequence", cursor)))
                yield encode("runtime", event)
            if snapshot.get("has_more"):
                continue
            status = snapshot.get("status")
            if status in {"completed", "failed"}:
                yield encode("complete" if status == "completed" else "failed", {
                    "status": status,
                    "result": snapshot.get("result"),
                    "error": snapshot.get("error"),
                    "metrics": snapshot.get("metrics", {}),
                    "next_sequence": cursor,
                })
                return
            yield ": keep-alive\n\n"
            time.sleep(0.2)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-transform"
    response["X-Accel-Buffering"] = "no"
    return response


@require_GET
def agent_trace(request, run_id):
    """Expose auditable execution decisions without revealing private model reasoning tokens."""
    snapshot = get_run(run_id)
    if not snapshot:
        return JsonResponse({"ok": False, "message": "Agent 运行任务不存在。"}, status=404, json_dumps_params={"ensure_ascii": False})
    results = snapshot.get("results", {})
    standard = results.get("standardization", {})
    cleaning = results.get("cleaning", {})
    modeling = results.get("modeling", {})
    optimization = results.get("optimization", {})
    review = results.get("review", {})
    stages = snapshot.get("stages", [])
    stage_duration = {stage.get("key"): _duration_ms(stage.get("started_at"), stage.get("finished_at")) for stage in stages}
    total_duration = _duration_ms(snapshot.get("created_at"), snapshot.get("updated_at"))
    stage_states = {stage.get("key"): stage.get("status") for stage in stages}

    def evidence_status(stage_keys=(), *, available=False, terminal=False):
        states = [stage_states.get(key) for key in stage_keys]
        if any(value == "failed" for value in states):
            return "failed"
        if available or any(value in {"completed", "success"} for value in states):
            return "success"
        if any(value in {"running", "executing"} for value in states):
            return "running"
        if terminal and snapshot.get("status") == "failed":
            return "failed"
        return "waiting"

    nodes = [
        {"id": "instruction", "name": "用户指令", "kind": "input", "duration_ms": 0, "status": "success", "input": {"message": snapshot.get("instruction") or "上传 CSV 并执行全流程"}, "output": {"run_id": run_id, "dataset": snapshot.get("original_name")}},
        {"id": "intent", "name": "意图解析", "kind": "reason", "duration_ms": stage_duration.get("standardization", 0), "status": evidence_status(("standardization",), available=bool(standard)), "input": {"scenario_request": snapshot.get("scenario_request", "auto")}, "output": {"scenario": standard.get("scenario", {}).get("scenario_name"), "data_decision": standard.get("data_decision", {}).get("status")}},
        {"id": "tools", "name": "工具选择", "kind": "tool", "duration_ms": 0, "status": "success" if stages else "waiting", "input": {"available_stages": len(stages)}, "output": {"tools": [stage.get("key") for stage in stages]}},
        {"id": "parameters", "name": "参数生成", "kind": "parameter", "duration_ms": 0, "status": "success" if cleaning.get("config") or modeling.get("config") or optimization.get("best_parameters") else evidence_status(("cleaning", "modeling", "optimization")), "input": {"objective": "R²、误差与数据覆盖率综合评价"}, "output": {"resample_rule": cleaning.get("config", {}).get("resample_rule"), "max_lag": modeling.get("config", {}).get("max_lag"), "best_parameters": optimization.get("best_parameters", {})}},
        {"id": "execution", "name": "算法调用", "kind": "execution", "duration_ms": sum(stage_duration.values()), "status": evidence_status(("cleaning", "selection", "modeling", "optimization"), available=bool(cleaning or modeling or optimization)), "input": {"rows": cleaning.get("cleaned_row_count"), "variables": len(standard.get("mapping", {}).get("mappings", []))}, "output": {"selected_segments": cleaning.get("selected_segment_count"), "modeling_rows": cleaning.get("modeling_row_count"), "features": len(modeling.get("selected_inputs", []))}},
        {"id": "evaluation", "name": "结果评估", "kind": "evaluation", "duration_ms": stage_duration.get("modeling", 0), "status": evidence_status(("modeling", "review"), available=bool(modeling.get("metrics") or review)), "input": {"metrics": ["R²", "RMSE", "MAE"]}, "output": {**modeling.get("metrics", {}).get("test", {}), "gate": "passed" if review.get("passed") else "review"}},
        {"id": "decision", "name": "下一步决策", "kind": "decision", "duration_ms": stage_duration.get("optimization", 0), "status": evidence_status(("optimization", "review"), available=bool(optimization.get("iterations") or review)), "input": {"rounds": len(optimization.get("iterations", [])), "best_round": optimization.get("best_round")}, "output": {"action": "deliver" if review.get("passed") else "review", "reason": optimization.get("stopping", {}).get("stop_reason") or review.get("conclusion")}},
        {"id": "output", "name": "最终输出", "kind": "output", "duration_ms": stage_duration.get("report", 0), "status": evidence_status(("report",), available=snapshot.get("status") == "completed", terminal=True), "input": {"review": review.get("conclusion")}, "output": {"artifacts": list(snapshot.get("artifacts", {}).keys()), "status": snapshot.get("status")}},
    ]
    payload = {"source": "api", "run_id": run_id, "total_duration_ms": total_duration, "nodes": nodes, "toolchain": ["数据清洗", "动态筛选", "时滞解耦", "系统辨识", "指标评估"]}
    return JsonResponse({"ok": True, "data": payload}, json_dumps_params={"ensure_ascii": False})
