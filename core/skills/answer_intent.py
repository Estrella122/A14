from __future__ import annotations

import re
from typing import Any


ANSWER_INTENTS = (
    "VALUE_QUERY",
    "METHOD_QUERY",
    "FORMULA_QUERY",
    "EVIDENCE_QUERY",
    "INTERPRETATION_QUERY",
    "COMPARISON_QUERY",
    "CAUSE_QUERY",
    "RECOMMENDATION_QUERY",
)


_PATTERNS = (
    ("FORMULA_QUERY", r"公式|方程|数学表达|表达式"),
    ("EVIDENCE_QUERY", r"可靠|靠谱|可信|置信|证据|验证|准不准"),
    ("COMPARISON_QUERY", r"哪个|哪段|哪些时间|最高|最低|排名|比较|对比"),
    ("CAUSE_QUERY", r"为什么|为何|原因|怎么会"),
    ("RECOMMENDATION_QUERY", r"建议|怎么办|如何改进|下一步|怎么处理"),
    ("INTERPRETATION_QUERY", r"说明什么|意味着|代表什么|怎么理解|如何解读|有什么意义"),
    ("METHOD_QUERY", r"怎么算|如何计算|计算方法|用什么方法|算法|步骤"),
    ("VALUE_QUERY", r"多少|数值|具体值|结果是|是多大"),
)


def resolve_answer_intent(message: str, conversation_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify the requested answer form independently from analysis capability selection."""
    normalized = str(message or "").strip().lower()
    for kind, pattern in _PATTERNS:
        signals = re.findall(pattern, normalized, re.IGNORECASE)
        if signals:
            return {"kind": kind, "confidence": 0.96, "signals": list(dict.fromkeys(signals)), "source": "answer_form_rules"}

    previous = (conversation_context or {}).get("previous_task_spec") or {}
    previous_answer = previous.get("answer_intent") or {}
    previous_kind = previous_answer.get("kind") if isinstance(previous_answer, dict) else previous_answer
    if re.search(r"这个|该结果|刚才|继续|具体", normalized) and previous_kind in ANSWER_INTENTS:
        return {"kind": previous_kind, "confidence": 0.72, "signals": ["上下文继承"], "source": "conversation_context"}
    return {"kind": "INTERPRETATION_QUERY", "confidence": 0.55, "signals": [], "source": "default"}
