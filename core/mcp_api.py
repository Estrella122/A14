from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from core.mcp.client import check_server
from core.mcp.service import CONTROL_MODE, TOOL_SPECS
from core.models import RuntimeJob


TOOL_LABELS = {
    "run_dynamic_selection": ("高信噪比动态优选", "计算工具", "赛题（3）：截取有效建模数据段并进行质量评分。"),
    "run_decoupling_identification": ("时滞与共线性解耦辨识", "计算工具", "赛题（4）：补偿时滞、剔除冗余变量并训练验证模型。"),
    "run_closed_loop_optimization": ("一键式闭环寻优", "计算工具", "赛题（5）：以验证集表现反馈搜索最佳预处理策略。"),
    "get_job_status": ("任务状态查询", "任务工具", "查询异步任务进度、门禁和结果引用。"),
    "cancel_job": ("取消任务", "任务工具", "取消排队任务或登记协作式取消请求。"),
    "list_run_artifacts": ("运行产物清单", "证据工具", "列出类型化产物、版本和哈希。"),
    "get_artifact_summary": ("产物安全摘要", "证据工具", "读取产物元数据摘要，不注入完整原始数据。"),
    "list_registered_runs": ("已登记运行", "数据工具", "列出可供 Agent 调用的真实数据运行。"),
    "search_knowledge": ("审核知识检索", "知识工具", "检索经过审核的场景、变量、算法和 Skill 知识。"),
}


def _public_tools():
    tools = []
    for name, (label, category, description) in TOOL_LABELS.items():
        spec = TOOL_SPECS.get(name, {})
        tools.append({
            "name": name,
            "label": label,
            "category": category,
            "description": description,
            "stage": spec.get("stage"),
            "skills": list(spec.get("skills", ())),
            "quality_gates": list(spec.get("quality_gates", ())),
            "read_only": name not in TOOL_SPECS and name != "cancel_job",
        })
    return tools


@require_GET
def mcp_center(request):
    health = check_server(getattr(settings, "PROCESSPILOT_MCP_URL", ""))
    queryset = RuntimeJob.objects.filter(job_type="mcp_pipeline")
    recent = queryset.order_by("-created_at")[:20]
    jobs = [{
        "job_id": job.job_id,
        "tool_name": job.tool_name,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress": job.progress,
        "result_ref": job.result_ref,
        "error_code": job.error_code or None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    } for job in recent]
    return JsonResponse({
        "ok": True,
        "server": {
            "name": "processpilot-modeling",
            "transport": "Streamable HTTP",
            "endpoint": getattr(settings, "PROCESSPILOT_MCP_URL", ""),
            "control_mode": CONTROL_MODE,
            "actuation_allowed": False,
            **health,
        },
        "tools": _public_tools(),
        "jobs": jobs,
        "job_counts": {
            status: queryset.filter(status=status).count()
            for status in ("queued", "running", "completed", "blocked", "failed", "cancelled")
        },
    }, json_dumps_params={"ensure_ascii": False})
