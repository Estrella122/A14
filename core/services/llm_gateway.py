from __future__ import annotations

import ipaddress
import json
import re
import ssl
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi
from django.conf import settings


class LLMGatewayError(RuntimeError):
    """A safe, user-facing error from an OpenAI-compatible model endpoint."""


@dataclass(frozen=True)
class ResolvedLLMConfig:
    provider: str
    label: str
    model: str
    base_url: str
    api_key: str


def _clean_model(value: Any, fallback: str) -> str:
    model = str(value or fallback).strip()
    if not model or len(model) > 120 or not re.fullmatch(r"[A-Za-z0-9._:/-]+", model):
        raise LLMGatewayError("模型名称格式无效。")
    return model


def _local_base_url(value: Any) -> str:
    base_url = str(value or getattr(settings, "PROCESSPILOT_LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1")).strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LLMGatewayError("本地模型地址必须是有效的 HTTP(S) URL。")
    hostname = parsed.hostname.lower()
    is_loopback = hostname == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        pass
    if not is_loopback:
        raise LLMGatewayError("为避免服务器端请求伪造，本地模型接口仅允许 localhost 或回环地址。")
    return base_url


def resolve_llm_config(config: dict[str, Any] | None) -> ResolvedLLMConfig | None:
    config = config or {}
    provider = str(config.get("provider") or "evidence").strip().lower()
    if provider == "evidence":
        return None
    if provider == "deepseek":
        api_key = str(getattr(settings, "DEEPSEEK_API_KEY", "") or "").strip()
        if not api_key:
            raise LLMGatewayError("DeepSeek 尚未在服务端配置 API Key。")
        return ResolvedLLMConfig(
            provider="deepseek",
            label="DeepSeek API",
            model=_clean_model(config.get("model"), getattr(settings, "DEEPSEEK_MODEL", "deepseek-flash")),
            base_url=str(getattr(settings, "DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")).rstrip("/"),
            api_key=api_key,
        )
    if provider == "local":
        return ResolvedLLMConfig(
            provider="local",
            label="本地 OpenAI 兼容模型",
            model=_clean_model(config.get("model"), getattr(settings, "PROCESSPILOT_LOCAL_LLM_MODEL", "qwen2.5:7b")),
            base_url=_local_base_url(config.get("base_url")),
            api_key=str(getattr(settings, "PROCESSPILOT_LOCAL_LLM_API_KEY", "") or "").strip(),
        )
    raise LLMGatewayError("模型提供商仅支持 evidence、deepseek 或 local。")


def provider_catalog() -> dict[str, Any]:
    return {
        "default_provider": "deepseek" if getattr(settings, "DEEPSEEK_API_KEY", "") else "evidence",
        "providers": [
            {"id": "evidence", "label": "Evidence Agent", "configured": True, "model": "deterministic-evidence-v1", "description": "不调用外部模型，完全按任务证据生成。"},
            {"id": "deepseek", "label": "DeepSeek API", "configured": bool(getattr(settings, "DEEPSEEK_API_KEY", "")), "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-flash"), "description": "服务端密钥，OpenAI 兼容流式接口。"},
            {"id": "local", "label": "本地 LLM", "configured": True, "model": getattr(settings, "PROCESSPILOT_LOCAL_LLM_MODEL", "qwen2.5:7b"), "base_url": getattr(settings, "PROCESSPILOT_LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1"), "description": "连接 Ollama、LM Studio 等本机 OpenAI 兼容接口。"},
        ],
    }


def _chat_endpoint(base_url: str) -> str:
    return base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"


def _plain_text_answer(value: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", value, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return re.sub(r"(?m)^#{1,6}\s*", "", text).strip()


def _evidence_payload(message: str, snapshot: dict[str, Any], response: dict[str, Any]) -> str:
    results = snapshot.get("results", {})
    standardization = results.get("standardization", {})
    cleaning = results.get("cleaning", {})
    modeling = results.get("modeling", {})
    optimization = results.get("optimization", {})
    def pick(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
        return {key: source.get(key) for key in keys if source.get(key) is not None}
    payload = {
        "user_question": message,
        "run_id": snapshot.get("run_id"),
        "run_status": snapshot.get("status"),
        "scenario": pick(standardization.get("scenario", {}), ("scenario_id", "scenario_name", "primary_output", "model_outputs", "sampling_seconds", "time_axis_type")),
        "standardization": {
            "data_decision": standardization.get("data_decision"),
            "required_coverage": standardization.get("mapping", {}).get("required_coverage"),
            "missing_required": standardization.get("mapping", {}).get("missing_required", []),
        },
        "data_quality": pick(cleaning, ("overall_score", "cleaned_row_count", "modeling_row_count", "selected_segment_count", "missing_rate", "dimension_scores", "warnings")),
        "modeling": pick(modeling, ("output_col", "input_cols", "selected_inputs", "lags", "metrics", "baseline_comparison", "residual_diagnostics", "warnings")),
        "optimization": pick(optimization, ("best_round", "best_label", "best_score", "best_parameters", "best_metrics", "stopping", "warnings")),
        "review": pick(results.get("review", {}), ("passed", "conclusion", "blockers", "warnings")),
        "evidence_answer": response.get("answer"),
        "cards": response.get("cards", []),
        "intent": response.get("intent", {}),
        "skill_executions": [{
            "skill_id": item.get("skill_id"), "name": item.get("name"), "status": item.get("status"),
            "activity": item.get("activity"), "evidence": item.get("evidence", []),
        } for item in response.get("skill_executions", [])],
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def generate_grounded_answer(
    *, message: str, snapshot: dict[str, Any], response: dict[str, Any], config: dict[str, Any] | None,
    on_delta: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    resolved = resolve_llm_config(config)
    if resolved is None:
        return {"answer": response.get("answer", ""), "provider": "evidence", "model": "deterministic-evidence-v1", "usage": None}
    request_body = {
        "model": resolved.model,
        "messages": [
            {"role": "system", "content": (
                "你是 ProcessPilot 流程工业建模 Agent。只能依据随后提供的运行证据回答，不得编造指标、产物、"
                "Skill 执行状态或控制结论。明确区分已执行、只读取证据、等待其他模块和不可投运。"
                "先给结论，再给关键证据与下一步；使用分段纯文本和简洁中文，不要使用 Markdown 标记。"
                "不要输出隐藏思维链，只输出可审计的判断依据摘要。"
            )},
            {"role": "user", "content": _evidence_payload(message, snapshot, response)},
        ],
        "temperature": 0.2,
        "stream": True,
    }
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if resolved.api_key:
        headers["Authorization"] = f"Bearer {resolved.api_key}"
    request = Request(_chat_endpoint(resolved.base_url), data=json.dumps(request_body).encode("utf-8"), headers=headers, method="POST")
    chunks: list[str] = []
    usage = None
    try:
        tls_context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=int(getattr(settings, "PROCESSPILOT_LLM_TIMEOUT_SECONDS", 90)), context=tls_context) as remote:
            content_type = str(remote.headers.get("content-type", "")).lower()
            if "text/event-stream" not in content_type:
                payload = json.loads(remote.read().decode("utf-8"))
                text = str(payload.get("choices", [{}])[0].get("message", {}).get("content") or "")
                usage = payload.get("usage")
                if text and on_delta:
                    on_delta(text)
                chunks.append(text)
            else:
                for raw_line in remote:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    payload = json.loads(data)
                    usage = payload.get("usage") or usage
                    text = str(payload.get("choices", [{}])[0].get("delta", {}).get("content") or "")
                    if text:
                        chunks.append(text)
                        if on_delta:
                            on_delta(text)
    except HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise LLMGatewayError(f"{resolved.label} 返回 HTTP {exc.code}：{detail[:180]}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LLMGatewayError(f"无法连接 {resolved.label}：{exc}") from exc
    answer = _plain_text_answer("".join(chunks))
    if not answer:
        raise LLMGatewayError(f"{resolved.label} 未返回可用文本。")
    return {"answer": answer, "provider": resolved.provider, "label": resolved.label, "model": resolved.model, "usage": usage}
