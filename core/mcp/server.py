from __future__ import annotations

import json
import os
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "heating_furnace_apc.settings")

import django

django.setup()

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from core.mcp.service import (
    MCPServiceError,
    artifact_summary,
    cancel_job as cancel_runtime_job,
    capabilities_resource,
    enqueue_modeling_tool,
    get_job,
    list_run_artifacts as list_artifacts,
    list_registered_runs as registered_runs,
    run_resource,
    scene_contract_resource,
    search_approved_knowledge,
    skill_contract_resource,
    skill_catalog_resource,
)


mcp = MCPServer(
    "processpilot-modeling",
    version="1.0.0",
    instructions=(
        "ProcessPilot 的三个工业建模工具仅执行离线动态数据优选、解耦辨识和预处理反馈寻优。"
        "它不会向 PLC/DCS 下发控制参数。计算工具返回持久化 job_id，请通过 get_job_status 查询结果。"
    ),
)


def _call(operation):
    try:
        return operation()
    except MCPServiceError as exc:
        return {
            "schema_version": "processpilot-mcp-result-v1",
            "status": "blocked",
            "error": exc.public(),
            "control_mode": "advisory_only",
            "actuation_allowed": False,
        }


COMPUTE_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
READ_TOOL = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
CANCEL_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)


@mcp.tool(annotations=COMPUTE_TOOL)
def run_dynamic_selection(
    source_run_id: str,
    caller_id: str = "local-agent",
    idempotency_key: str = "",
    scene_id: str = "auto",
    resample_rule: str = "10s",
    max_lag: int = 60,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """筛选并评分高信噪比动态建模数据段。

    适用于“提取有效动态段、评估信噪比、生成建模数据”等执行请求。
    不用于解释已有结果、训练模型或生产控制。source_run_id 必须来自已登记的真实数据运行。
    """
    return _call(lambda: enqueue_modeling_tool(
        "run_dynamic_selection", source_run_id, caller_id=caller_id,
        idempotency_key=idempotency_key, scene_id=scene_id,
        resample_rule=resample_rule, max_lag=max_lag, overrides=overrides,
    ))


@mcp.tool(annotations=COMPUTE_TOOL)
def run_decoupling_identification(
    source_run_id: str,
    caller_id: str = "local-agent",
    idempotency_key: str = "",
    scene_id: str = "auto",
    resample_rule: str = "10s",
    maximum_lag_samples: int = 60,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """执行因果方向受限的时滞估计、共线性分析和 AR/ARX 辨识验证。

    适用于“估算时滞、剔除冗余变量、训练并验证辨识模型”等请求。
    互相关不被表述为因果证明，本工具也不执行多轮预处理寻优或控制下发。
    """
    return _call(lambda: enqueue_modeling_tool(
        "run_decoupling_identification", source_run_id, caller_id=caller_id,
        idempotency_key=idempotency_key, scene_id=scene_id,
        resample_rule=resample_rule, max_lag=maximum_lag_samples, overrides=overrides,
    ))


@mcp.tool(annotations=COMPUTE_TOOL)
def run_closed_loop_optimization(
    source_run_id: str,
    caller_id: str = "local-agent",
    idempotency_key: str = "",
    scene_id: str = "auto",
    resample_rule: str = "10s",
    maximum_lag_samples: int = 60,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """循环搜索预处理与建模候选，以冻结验证集指标反馈选择最佳方案。

    这里的闭环仅指离线“预处理—建模—验证反馈”搜索。测试集不参与寻优，
    优胜方案冻结后只评估一次；本工具不向 PLC/DCS 写入任何参数。
    """
    return _call(lambda: enqueue_modeling_tool(
        "run_closed_loop_optimization", source_run_id, caller_id=caller_id,
        idempotency_key=idempotency_key, scene_id=scene_id,
        resample_rule=resample_rule, max_lag=maximum_lag_samples, overrides=overrides,
    ))


@mcp.tool(annotations=READ_TOOL)
def get_job_status(job_id: str, caller_id: str = "local-agent") -> dict[str, Any]:
    """读取 MCP 工业建模任务的状态、进度、指标、门禁和产物引用，不重新运行算法。"""
    return _call(lambda: get_job(job_id, caller_id=caller_id))


@mcp.tool(annotations=CANCEL_TOOL)
def cancel_job(job_id: str, caller_id: str = "local-agent") -> dict[str, Any]:
    """取消自己创建的排队任务；运行中任务会登记协作式取消请求。"""
    return _call(lambda: cancel_runtime_job(job_id, caller_id=caller_id))


@mcp.tool(annotations=READ_TOOL)
def list_run_artifacts(run_id: str) -> dict[str, Any]:
    """列出运行产生的类型化产物、版本和哈希，不返回本地文件路径或完整数据。"""
    return _call(lambda: list_artifacts(run_id))


@mcp.tool(annotations=READ_TOOL)
def get_artifact_summary(run_id: str, artifact_key: str) -> dict[str, Any]:
    """读取产物的安全元数据摘要；不会把完整 CSV 或模型文件注入 Agent 上下文。"""
    return _call(lambda: artifact_summary(run_id, artifact_key))


@mcp.tool(annotations=READ_TOOL)
def list_registered_runs(limit: int = 20, scene_id: str = "") -> dict[str, Any]:
    """列出 Agent 可使用的已登记真实数据运行，不返回原始 CSV 内容或服务器路径。"""
    return _call(lambda: registered_runs(limit, scene_id))


@mcp.tool(annotations=READ_TOOL)
def search_knowledge(query: str, scene_id: str = "", limit: int = 8) -> dict[str, Any]:
    """检索经过审核的场景、变量、算法和 Skill 知识；仅用于路由与解释，不绕过硬门禁。"""
    return _call(lambda: search_approved_knowledge(query, scene_id, limit))


@mcp.resource("processpilot://server/capabilities")
def server_capabilities() -> str:
    """ProcessPilot MCP 工具、对应 Skill 和安全边界。"""
    return capabilities_resource()


@mcp.resource("processpilot://skills/catalog")
def skills_catalog() -> str:
    """现有业务 Skill 的只读、版本化执行契约目录。"""
    return skill_catalog_resource()


@mcp.resource("processpilot://skills/{skill_id}/contract")
def skill_contract(skill_id: str) -> str:
    """单个 Skill 的版本化输入、产物和质量门禁契约。"""
    try:
        return skill_contract_resource(skill_id)
    except MCPServiceError as exc:
        return json.dumps(exc.public(), ensure_ascii=False)


@mcp.resource("processpilot://scenes/{scene_id}/contract")
def scene_contract(scene_id: str) -> str:
    """正式工业场景的字段、采样、目标与数据来源契约。"""
    try:
        return scene_contract_resource(scene_id)
    except MCPServiceError as exc:
        return json.dumps(exc.public(), ensure_ascii=False)


@mcp.resource("processpilot://runs/{run_id}/manifest")
def run_manifest(run_id: str) -> str:
    """运行状态、场景、阶段和产物清单。"""
    try:
        return run_resource(run_id)
    except MCPServiceError as exc:
        return json.dumps(exc.public(), ensure_ascii=False)


@mcp.resource("processpilot://runs/{run_id}/evidence")
def run_evidence(run_id: str) -> str:
    """运行的结构化计算证据；大型原始数据不会包含在资源中。"""
    try:
        return run_resource(run_id, evidence=True)
    except MCPServiceError as exc:
        return json.dumps(exc.public(), ensure_ascii=False)


def main() -> None:
    transport = os.getenv("PROCESSPILOT_MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return
    if transport != "streamable-http":
        raise SystemExit("PROCESSPILOT_MCP_TRANSPORT 只支持 stdio 或 streamable-http。")
    host = os.getenv("PROCESSPILOT_MCP_HOST", "127.0.0.1")
    allow_remote = os.getenv("PROCESSPILOT_MCP_ALLOW_REMOTE", "false").lower() in {"1", "true", "yes"}
    if host not in {"127.0.0.1", "localhost", "::1"} and not allow_remote:
        raise SystemExit("远程绑定默认关闭；完成认证与授权配置后再显式设置 PROCESSPILOT_MCP_ALLOW_REMOTE=true。")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=int(os.getenv("PROCESSPILOT_MCP_PORT", "8010")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        max_request_body_size=1024 * 1024,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
