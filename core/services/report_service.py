from __future__ import annotations

from pathlib import Path
from typing import Any


def render_execution_report(snapshot: dict[str, Any], prior_results: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    """Format existing evidence only. This function never runs analysis algorithms."""
    if not snapshot.get("results") and not prior_results:
        raise ValueError("缺少可报告的既有执行结果。")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = snapshot.get("results", {})
    lines = [
        "# Skill Runtime 执行报告", "",
        f"Pipeline run：`{snapshot.get('run_id', '未绑定')}`", "",
        "## 已有结果", "",
    ]
    for name, value in results.items():
        if isinstance(value, dict):
            status = value.get("status") or value.get("conclusion") or "已记录"
            lines.append(f"- **{name}**：{status}")
    for item in prior_results:
        lines.append(f"- **{item.get('skill_id')}**：{item.get('status')}")
    lines += ["", "## 事实与发现", ""]
    facts = [fact for item in prior_results for fact in item.get("facts", [])]
    findings = [finding for item in prior_results for finding in item.get("findings", [])]
    lines.extend(f"- {item}" for item in (facts + findings or ["本报告仅整理当前 snapshot 中已有证据。"]))
    lines += ["", "## 限制", ""]
    limitations = [entry for item in prior_results for entry in item.get("limitations", [])]
    lines.extend(f"- {item}" for item in (limitations or ["报告生成过程没有重新执行标准化、清洗、建模或优化。"]))
    path = output_dir / "execution_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"title": "Skill Runtime 执行报告", "path": str(path), "sections": ["已有结果", "事实与发现", "限制"]}
