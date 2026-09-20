from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


TERMINAL_STATUSES = {"completed", "partial", "blocked", "failed", "cancelled", "timed_out"}
REQUIRED_MODELING_TOOLS = {
    "run_dynamic_selection",
    "run_decoupling_identification",
    "run_closed_loop_optimization",
    "get_job_status",
}


class MCPInvocationError(RuntimeError):
    pass


def _rpc(url: str, method: str, params: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": uuid4().hex,
        "method": method,
        "params": params,
    }).encode("utf-8")
    request = Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise MCPInvocationError(f"MCP HTTP 请求失败：{exc}") from exc
    if not isinstance(payload, dict):
        raise MCPInvocationError("MCP Server 返回了无效 JSON-RPC 响应。")
    if payload.get("error"):
        error = payload["error"]
        message = error.get("message", "未知协议错误") if isinstance(error, dict) else str(error)
        raise MCPInvocationError(f"MCP Server 返回错误：{message}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise MCPInvocationError("MCP Server 未返回 result。")
    return result


def _structured(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("isError"):
        content = result.get("content") or []
        message = content[0].get("text") if content and isinstance(content[0], dict) else "工具执行失败"
        raise MCPInvocationError(f"MCP 工具执行失败：{message}")
    payload = result.get("structuredContent")
    if not isinstance(payload, dict):
        raise MCPInvocationError("MCP Server 未返回结构化结果。")
    return payload


def _invoke_and_wait(
    url: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    timeout_seconds: float,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    import time

    submitted = _structured(_rpc(url, "tools/call", {
        "name": tool_name,
        "arguments": arguments,
    }, min(timeout_seconds, 10)))
    if on_progress:
        on_progress(submitted)
    if submitted.get("status") in TERMINAL_STATUSES:
        return submitted
    job_id = submitted.get("job_id")
    if not job_id:
        raise MCPInvocationError("MCP Server 未返回 job_id。")
    deadline = time.monotonic() + timeout_seconds
    submitted_stage = submitted.get("current_stage") or {}
    submitted_progress = submitted.get("progress") or {}
    last_progress_signature = (
        submitted.get("status"), submitted_stage.get("key"), submitted_stage.get("status"), submitted_progress.get("percent")
    )
    while time.monotonic() < deadline:
        time.sleep(0.2)
        current = _structured(_rpc(url, "tools/call", {
            "name": "get_job_status",
            "arguments": {
                "job_id": job_id,
                "caller_id": arguments.get("caller_id", "processpilot-agent"),
            },
        }, min(timeout_seconds, 10)))
        current_stage = current.get("current_stage") or {}
        progress = current.get("progress") or {}
        progress_signature = (
            current.get("status"), current_stage.get("key"), current_stage.get("status"), progress.get("percent")
        )
        if on_progress and progress_signature != last_progress_signature:
            on_progress(current)
            last_progress_signature = progress_signature
        if current.get("status") in TERMINAL_STATUSES:
            return current
    raise MCPInvocationError(f"MCP 任务 {job_id} 在 {timeout_seconds:g} 秒内未完成。")


def invoke_and_wait(
    url: str,
    tool_name: str,
    source_run_id: str,
    *,
    resample_rule: str | None = None,
    max_lag: int | None = None,
    parameters: dict | None = None,
    request_key: str | None = None,
    timeout_seconds: float = 180,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "source_run_id": source_run_id,
        "caller_id": "processpilot-agent",
        "idempotency_key": request_key or f"agent-{uuid4().hex}",
        "resample_rule": resample_rule,
        "parameters": parameters,
    }
    if tool_name == "run_dynamic_selection":
        arguments["max_lag"] = max_lag
    else:
        arguments["maximum_lag_samples"] = max_lag
    try:
        return _invoke_and_wait(url, tool_name, arguments, timeout_seconds=timeout_seconds, on_progress=on_progress)
    except MCPInvocationError:
        raise
    except Exception as exc:
        raise MCPInvocationError(f"无法调用 MCP Server：{exc}") from exc


def _check_server(url: str) -> dict[str, Any]:
    result = _rpc(url, "tools/list", {}, 2)
    available = {
        tool.get("name") for tool in result.get("tools", [])
        if isinstance(tool, dict) and tool.get("name")
    }
    missing = sorted(REQUIRED_MODELING_TOOLS - available)
    return {"online": not missing, "tool_count": len(available), "missing_tools": missing}


def check_server(url: str) -> dict[str, Any]:
    if not url:
        return {"configured": False, "online": False, "tool_count": 0, "missing_tools": []}
    try:
        return {"configured": True, **_check_server(url)}
    except Exception as exc:
        return {"configured": True, "online": False, "tool_count": 0, "missing_tools": [], "error": str(exc)}
