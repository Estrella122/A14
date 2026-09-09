from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .engine import normalize_name
from .repository import ScenarioRepository


class FeedbackStore:
    STATUSES = {"pending", "approved", "rejected"}

    def __init__(self, path: Path, repository: ScenarioRepository, approved_knowledge_path: Path | None = None) -> None:
        self.path = path
        self.repository = repository
        self.lock = threading.Lock()
        if not self.path.exists() and approved_knowledge_path and approved_knowledge_path.exists():
            self._bootstrap_approved(approved_knowledge_path)

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "records": []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise ValueError("字段反馈库格式无效。")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def _bootstrap_approved(self, knowledge_path: Path) -> None:
        knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
        timestamp = datetime.fromtimestamp(knowledge_path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        records = []
        for scenario_id, fields in knowledge.items():
            for standard_name, aliases in fields.items():
                for alias in aliases:
                    records.append({
                        "feedback_id": uuid4().hex,
                        "scenario_id": scenario_id,
                        "raw_name": alias,
                        "normalized_raw_name": normalize_name(alias),
                        "standard_name": standard_name,
                        "status": "approved",
                        "source": "legacy_migration",
                        "note": "从旧版已确认别名库迁移",
                        "submitted_by": "system_migration",
                        "submitted_at": timestamp,
                        "reviewed_by": "system_migration",
                        "reviewed_at": timestamp,
                        "review_note": "历史已通过记录",
                    })
        if records:
            self._write({"version": 1, "records": records})

    def submit(
        self,
        scenario_id: str,
        raw_name: str,
        standard_name: str,
        submitted_by: str = "operator",
        source: str = "web_manual",
        note: str = "",
    ) -> dict[str, Any]:
        template = self.repository.get(str(scenario_id))
        if standard_name not in template.by_name:
            raise ValueError(f"场景 {scenario_id} 不存在标准字段 {standard_name}。")
        raw_name = str(raw_name).strip()
        if not raw_name:
            raise ValueError("原始字段名不能为空。")
        submitted_by = str(submitted_by or "operator").strip()[:80]
        note = str(note or "").strip()[:500]
        normalized = normalize_name(raw_name)
        with self.lock:
            payload = self._read()
            duplicate = next(
                (
                    item for item in reversed(payload["records"])
                    if item["scenario_id"] == scenario_id
                    and item["normalized_raw_name"] == normalized
                    and item["standard_name"] == standard_name
                    and item["status"] in {"pending", "approved"}
                ),
                None,
            )
            if duplicate:
                return {**duplicate, "duplicate": True}
            now = self._now()
            record = {
                "feedback_id": uuid4().hex,
                "scenario_id": scenario_id,
                "raw_name": raw_name,
                "normalized_raw_name": normalized,
                "standard_name": standard_name,
                "status": "pending",
                "source": str(source or "web_manual")[:80],
                "note": note,
                "submitted_by": submitted_by,
                "submitted_at": now,
                "reviewed_by": None,
                "reviewed_at": None,
                "review_note": None,
            }
            payload["records"].append(record)
            self._write(payload)
            return {**record, "duplicate": False}

    def review(
        self,
        feedback_id: str,
        decision: str,
        reviewed_by: str,
        review_note: str = "",
        approve_callback: Callable[[str, str, str], Any] | None = None,
    ) -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision 必须为 approved 或 rejected。")
        reviewed_by = str(reviewed_by or "reviewer").strip()[:80]
        review_note = str(review_note or "").strip()[:500]
        with self.lock:
            payload = self._read()
            record = next((item for item in payload["records"] if item["feedback_id"] == feedback_id), None)
            if record is None:
                raise ValueError(f"审核记录不存在：{feedback_id}")
            if record["status"] != "pending":
                if record["status"] == decision:
                    return {**record, "unchanged": True}
                raise ValueError("已完成的审核记录不能改判。")
            if decision == "approved" and approve_callback:
                approve_callback(record["scenario_id"], record["raw_name"], record["standard_name"])
            record.update(
                status=decision,
                reviewed_by=reviewed_by,
                reviewed_at=self._now(),
                review_note=review_note,
            )
            self._write(payload)
            return {**record, "unchanged": False}

    def bulk_submit(self, rows: list[dict[str, Any]], submitted_by: str = "bulk_import") -> dict[str, Any]:
        if len(rows) > 2000:
            raise ValueError("单次最多导入 2000 条字段。")
        required = {"scenario_id", "raw_name", "standard_name"}
        results = []
        errors = []
        for index, row in enumerate(rows, 2):
            if not required.issubset(row):
                raise ValueError("批量文件必须包含 scenario_id、raw_name、standard_name。")
            try:
                results.append(self.submit(
                    str(row.get("scenario_id", "")),
                    str(row.get("raw_name", "")),
                    str(row.get("standard_name", "")),
                    str(row.get("submitted_by") or submitted_by),
                    "bulk_csv",
                    str(row.get("note", "")),
                ))
            except ValueError as exc:
                errors.append({"row": index, "error": str(exc)})
        return {
            "received": len(rows),
            "created": sum(not item.get("duplicate") for item in results),
            "duplicates": sum(bool(item.get("duplicate")) for item in results),
            "errors": errors,
        }

    def list(self, status: str | None = None, limit: int = 500) -> dict[str, Any]:
        if status and status not in self.STATUSES:
            raise ValueError(f"未知审核状态：{status}")
        with self.lock:
            records = list(reversed(self._read()["records"]))
        stats = {name: sum(item["status"] == name for item in records) for name in self.STATUSES}
        selected = [item for item in records if not status or item["status"] == status][: max(1, min(int(limit), 1000))]
        return {"records": selected, "stats": {**stats, "total": len(records)}}
