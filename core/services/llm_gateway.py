from __future__ import annotations

import ipaddress
import base64
import hashlib
import json
import os
import re
import ssl
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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


_CREDENTIAL_AAD = b"processpilot-llm-credential-v1"


def _credential_cipher() -> AESGCM:
    key = hashlib.sha256(f"{settings.SECRET_KEY}:processpilot:llm".encode("utf-8")).digest()
    return AESGCM(key)


def issue_llm_credential(config: ResolvedLLMConfig, *, ttl_seconds: int = 8 * 60 * 60) -> str:
    """Return an authenticated, expiring token suitable for a queued worker.

    The browser keeps this token in memory only. The runtime queue therefore
    never stores a user's API key in plaintext and no schema migration is needed.
    """
    payload = json.dumps({
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "api_key": config.api_key,
        "expires_at": int(time.time()) + ttl_seconds,
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    nonce = os.urandom(12)
    encrypted = _credential_cipher().encrypt(nonce, payload, _CREDENTIAL_AAD)
    return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii").rstrip("=")


def _read_llm_credential(token: Any) -> ResolvedLLMConfig:
    try:
        raw_token = str(token or "").strip()
        if not raw_token or len(raw_token) > 8192:
            raise ValueError
        raw = base64.urlsafe_b64decode(raw_token + "=" * (-len(raw_token) % 4))
        payload = json.loads(_credential_cipher().decrypt(raw[:12], raw[12:], _CREDENTIAL_AAD).decode("utf-8"))
        if int(payload.get("expires_at", 0)) < int(time.time()):
            raise LLMGatewayError("模型连接凭据已过期，请重新测试连接。")
        return _resolve_inline_config(payload)
    except LLMGatewayError:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, InvalidTag) as exc:
        raise LLMGatewayError("模型连接凭据无效，请重新测试连接。") from exc


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


def _deepseek_base_url(value: Any) -> str:
    base_url = str(value or getattr(settings, "DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")).strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "api.deepseek.com" or parsed.username or parsed.password:
        raise LLMGatewayError("DeepSeek API 地址仅允许 https://api.deepseek.com 官方接口。")
    return base_url


def _resolve_inline_config(config: dict[str, Any]) -> ResolvedLLMConfig:
    provider = str(config.get("provider") or "").strip().lower()
    if provider == "deepseek":
        api_key = str(config.get("api_key") or "").strip()
        if not api_key:
            raise LLMGatewayError("请填写 DeepSeek API Key。")
        return ResolvedLLMConfig(
            provider="deepseek", label="DeepSeek API",
            model=_clean_model(config.get("model"), getattr(settings, "DEEPSEEK_MODEL", "deepseek-flash")),
            base_url=_deepseek_base_url(config.get("base_url")), api_key=api_key,
        )
    if provider == "local":
        return ResolvedLLMConfig(
            provider="local", label="本地 OpenAI 兼容模型",
            model=_clean_model(config.get("model"), getattr(settings, "PROCESSPILOT_LOCAL_LLM_MODEL", "qwen2.5:7b")),
            base_url=_local_base_url(config.get("base_url")), api_key=str(config.get("api_key") or "").strip(),
        )
    raise LLMGatewayError("连接测试仅支持 DeepSeek 或本地 OpenAI 兼容模型。")


def resolve_llm_config(config: dict[str, Any] | None) -> ResolvedLLMConfig | None:
    config = config or {}
    if config.get("credential"):
        resolved = _read_llm_credential(config["credential"])
        requested_provider = str(config.get("provider") or resolved.provider).strip().lower()
        requested_model = _clean_model(config.get("model"), resolved.model)
        requested_base = str(config.get("base_url") or resolved.base_url).rstrip("/")
        if (requested_provider, requested_model, requested_base) != (resolved.provider, resolved.model, resolved.base_url):
            raise LLMGatewayError("模型设置已变更，请重新测试连接。")
        return resolved
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
            base_url=_deepseek_base_url(None),
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
            {"id": "deepseek", "label": "DeepSeek API", "configured": bool(getattr(settings, "DEEPSEEK_API_KEY", "")), "accepts_user_key": True, "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-flash"), "base_url": getattr(settings, "DEEPSEEK_API_BASE_URL", "https://api.deepseek.com"), "models": ["deepseek-flash", "deepseek-v4-pro"], "description": "可使用服务端密钥，或仅在当前页面会话中输入自己的 Key。"},
            {"id": "local", "label": "本地 LLM", "configured": True, "accepts_user_key": True, "model": getattr(settings, "PROCESSPILOT_LOCAL_LLM_MODEL", "qwen2.5:7b"), "base_url": getattr(settings, "PROCESSPILOT_LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1"), "description": "连接 Ollama、LM Studio 等本机 OpenAI 兼容接口。"},
        ],
    }


def _chat_endpoint(base_url: str) -> str:
    return base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"


def test_llm_connection(config: dict[str, Any]) -> dict[str, Any]:
    provider = str(config.get("provider") or "").strip().lower()
    if provider == "deepseek" and not str(config.get("api_key") or "").strip():
        resolved = resolve_llm_config({"provider": "deepseek", "model": config.get("model"), "base_url": config.get("base_url")})
        if resolved is None:  # pragma: no cover - guarded by provider above
            raise LLMGatewayError("DeepSeek 尚未配置。")
    else:
        resolved = _resolve_inline_config(config)
    request_body = {
        "model": resolved.model,
        "messages": [{"role": "user", "content": "连接测试：只回复 OK"}],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if resolved.api_key:
        headers["Authorization"] = f"Bearer {resolved.api_key}"
    request = Request(_chat_endpoint(resolved.base_url), data=json.dumps(request_body).encode("utf-8"), headers=headers, method="POST")
    started = time.monotonic()
    try:
        tls_context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=min(30, int(getattr(settings, "PROCESSPILOT_LLM_TIMEOUT_SECONDS", 90))), context=tls_context) as remote:
            payload = json.loads(remote.read().decode("utf-8"))
        if not payload.get("choices"):
            raise LLMGatewayError(f"{resolved.label} 已响应，但未返回有效的模型结果。")
    except HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise LLMGatewayError(f"{resolved.label} 连接测试失败（HTTP {exc.code}）：{detail[:180]}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LLMGatewayError(f"无法连接 {resolved.label}：{exc}") from exc
    return {
        "connected": True, "provider": resolved.provider, "label": resolved.label,
        "model": resolved.model, "base_url": resolved.base_url,
        "latency_ms": max(1, round((time.monotonic() - started) * 1000)),
        "credential": issue_llm_credential(resolved),
        "expires_in_seconds": 8 * 60 * 60,
    }


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
