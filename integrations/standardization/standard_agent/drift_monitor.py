from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


class DriftMonitor:
    def __init__(self, path: Path, max_records: int = 2000) -> None:
        self.path = path
        self.max_records = max_records
        self._lock = threading.Lock()

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def record(self, result_id: str, result: dict[str, Any]) -> dict[str, Any]:
        mappings = result["mapping"]["mappings"]
        confidences = [float(item["confidence"]) for item in mappings if item.get("standard")]
        methods = Counter(str(item.get("method", "unknown")) for item in mappings)
        profile = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "result_id": result_id,
            "scenario_id": result["scenario"]["scenario_id"],
            "decision": result["data_decision"]["status"],
            "field_count": len(mappings),
            "unmapped_rate": round(sum(item["status"] == "unmapped" for item in mappings) / max(len(mappings), 1), 4),
            "review_rate": round(sum(item["status"] in {"review", "duplicate"} for item in mappings) / max(len(mappings), 1), 4),
            "mean_confidence": round(sum(confidences) / max(len(confidences), 1), 4),
            "required_coverage": float(result["mapping"]["required_coverage"]),
            "methods": dict(methods),
        }
        with self._lock:
            records = [*self._read(), profile][-self.max_records :]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")
            temporary.replace(self.path)
        return profile

    def summary(self, limit: int = 100) -> dict[str, Any]:
        with self._lock:
            records = self._read()[-max(1, min(limit, 1000)) :]
        if not records:
            return {"status": "no_data", "records": 0, "message": "尚未累积线上分析画像。", "recent": []}
        average_unmapped = sum(item["unmapped_rate"] for item in records) / len(records)
        average_review = sum(item["review_rate"] for item in records) / len(records)
        average_confidence = sum(item["mean_confidence"] for item in records) / len(records)
        reject_rate = sum(item["decision"] == "reject" for item in records) / len(records)
        scenario_distribution = Counter(item["scenario_id"] for item in records)
        warnings = []
        if average_unmapped > 0.25:
            warnings.append("未映射字段比例超过 25%")
        if average_review > 0.20:
            warnings.append("待审核字段比例超过 20%")
        if average_confidence < 0.75:
            warnings.append("平均映射置信度低于 75%")
        if reject_rate > 0.30:
            warnings.append("文件拒绝率超过 30%")
        return {
            "status": "warning" if warnings else "stable",
            "records": len(records),
            "average_unmapped_rate": round(average_unmapped, 4),
            "average_review_rate": round(average_review, 4),
            "average_confidence": round(average_confidence, 4),
            "reject_rate": round(reject_rate, 4),
            "scenario_distribution": dict(scenario_distribution),
            "warnings": warnings,
            "recent": records[-20:],
        }
