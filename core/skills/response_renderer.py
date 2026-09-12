from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ResponseRenderer(ABC):
    @abstractmethod
    def render(self, task_spec: dict[str, Any], execution_result: dict[str, Any]) -> str:
        raise NotImplementedError


class DeterministicResponseRenderer(ResponseRenderer):
    def render(self, task_spec: dict[str, Any], execution_result: dict[str, Any]) -> str:
        count = len(execution_result.get("capability_executions", []))
        findings = [item.get("statement") for item in execution_result.get("findings", []) if item.get("statement")]
        if not findings:
            findings = [item.get("statement") for item in execution_result.get("facts", []) if item.get("statement")]
        limitations = list(dict.fromkeys(item.get("statement") for item in execution_result.get("limitations", []) if item.get("statement")))
        text = f"已按“{task_spec.get('objective', '当前目标')}”执行 {count} 项 industrial-analysis 能力。"
        if findings:
            text += "发现：" + "；".join(findings)
        if limitations:
            text += " 限制：" + "；".join(limitations)
        return text


class LLMResponseRenderer(ResponseRenderer):
    def __init__(self, structured_completion):
        self.structured_completion = structured_completion

    def render(self, task_spec: dict[str, Any], execution_result: dict[str, Any]) -> str:
        response = self.structured_completion({
            "instruction": "Answer only from SkillExecutionResult evidence. Explain blocked/skipped capabilities and do not invent results.",
            "task_spec": task_spec,
            "skill_execution_result": execution_result,
        })
        return response["answer"] if isinstance(response, dict) else str(response)
