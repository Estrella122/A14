"""Render only the current MD execution's evidence, never stale pipeline metrics."""
import re


def render_manifest_response(plan, results):
    names = {step["skill_id"]: step["name"] for step in plan.get("steps", [])}
    if not results:
        document = plan["analysis"].get("agent_context", {}).get("loaded_skill_context", "")
        sections = re.split(r"(?m)^# ", document)
        paragraphs = [section.strip() for section in sections if section.startswith(("能力说明", "证据边界"))]
        return "\n\n".join(paragraphs) or "当前没有执行算法。", [], []
    paragraphs, cards = [], []
    for result in results:
        name = names.get(result["skill_id"], result["skill_id"])
        if result["status"] in {"success", "partial"}:
            findings = result.get("findings") or result.get("facts") or ["已生成指标，详见本次执行记录。"]
            text = "；".join(str(value) for value in findings[:8])
            if len(findings) > 8:
                text += f"；其余 {len(findings)-8} 项见本次 metrics。"
        else:
            text = result.get("reason") or "；".join(result.get("warnings") or result.get("limitations") or ["未获得可用结果"])
        boundaries = result.get("warnings", []) + result.get("limitations", [])
        paragraphs.append(f"{name}：{text}" + (" " + "；".join(dict.fromkeys(boundaries)) if boundaries else ""))
        cards.append({"label": name, "value": {"success": "已计算", "partial": "部分结果", "blocked": "缺少输入", "unavailable": "不可用", "failed": "失败", "read": "已读取"}.get(result["status"], result["status"])})
    return "\n\n".join(paragraphs), cards, []
