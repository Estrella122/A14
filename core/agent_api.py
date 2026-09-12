import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .services.agent_chat import chat
from .services.expert_qa import coverage_summary
from .services.pipeline import PipelineError, get_run
from .skills import execute_skill_plan, get_skill_run, list_skills, plan_skills


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
        result = chat(payload.get("message", ""), payload.get("run_id"), payload.get("previous_intent"), payload.get("previous_intents"))
        return JsonResponse({"ok": True, "data": result}, json_dumps_params={"ensure_ascii": False})
    except (ValueError, PipelineError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=422, json_dumps_params={"ensure_ascii": False})


@require_GET
def agent_skills(request):
    data = list_skills()
    data["expert_topics"] = coverage_summary()
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
    result = get_skill_run(skill_run_id)
    if not result:
        return JsonResponse({"ok": False, "message": "Skill 运行记录不存在。"}, status=404, json_dumps_params={"ensure_ascii": False})
    events = [{"sequence": index, "skill_id": item["skill_id"], "name": item["name"], "status": item["status"], "duration_ms": item["duration_ms"]} for index, item in enumerate(result["executions"], 1)]
    return JsonResponse({"ok": True, "data": {"skill_run_id": skill_run_id, "events": events}}, json_dumps_params={"ensure_ascii": False})


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
    status = "failed" if snapshot.get("status") == "failed" else "success"
    nodes = [
        {"id": "instruction", "name": "用户指令", "kind": "input", "duration_ms": 0, "status": "success", "input": {"message": snapshot.get("instruction") or "上传 CSV 并执行全流程"}, "output": {"run_id": run_id, "dataset": snapshot.get("original_name")}},
        {"id": "intent", "name": "意图解析", "kind": "reason", "duration_ms": stage_duration.get("standardization", 0), "status": status, "input": {"scenario_request": snapshot.get("scenario_request", "auto")}, "output": {"scenario": standard.get("scenario", {}).get("scenario_name"), "data_decision": standard.get("data_decision", {}).get("status")}},
        {"id": "tools", "name": "工具选择", "kind": "tool", "duration_ms": 0, "status": status, "input": {"available_stages": len(stages)}, "output": {"tools": [stage.get("key") for stage in stages]}},
        {"id": "parameters", "name": "参数生成", "kind": "parameter", "duration_ms": 0, "status": status, "input": {"objective": "R²、误差与数据覆盖率综合评价"}, "output": {"resample_rule": cleaning.get("config", {}).get("resample_rule"), "max_lag": modeling.get("config", {}).get("max_lag"), "best_parameters": optimization.get("best_parameters", {})}},
        {"id": "execution", "name": "算法调用", "kind": "execution", "duration_ms": sum(stage_duration.values()), "status": status, "input": {"rows": cleaning.get("cleaned_row_count"), "variables": len(standard.get("mapping", {}).get("mappings", []))}, "output": {"selected_segments": cleaning.get("selected_segment_count"), "modeling_rows": cleaning.get("modeling_row_count"), "features": len(modeling.get("selected_inputs", []))}},
        {"id": "evaluation", "name": "结果评估", "kind": "evaluation", "duration_ms": stage_duration.get("modeling", 0), "status": status, "input": {"metrics": ["R²", "RMSE", "MAE"]}, "output": {**modeling.get("metrics", {}).get("test", {}), "gate": "passed" if review.get("passed") else "review"}},
        {"id": "decision", "name": "下一步决策", "kind": "decision", "duration_ms": stage_duration.get("optimization", 0), "status": status, "input": {"rounds": len(optimization.get("iterations", [])), "best_round": optimization.get("best_round")}, "output": {"action": "deliver" if review.get("passed") else "review", "reason": optimization.get("stopping", {}).get("stop_reason") or review.get("conclusion")}},
        {"id": "output", "name": "最终输出", "kind": "output", "duration_ms": stage_duration.get("report", 0), "status": status, "input": {"review": review.get("conclusion")}, "output": {"artifacts": list(snapshot.get("artifacts", {}).keys()), "status": snapshot.get("status")}},
    ]
    payload = {"source": "api", "run_id": run_id, "total_duration_ms": total_duration, "nodes": nodes, "toolchain": ["数据清洗", "动态筛选", "时滞解耦", "系统辨识", "指标评估"]}
    return JsonResponse({"ok": True, "data": payload}, json_dumps_params={"ensure_ascii": False})
