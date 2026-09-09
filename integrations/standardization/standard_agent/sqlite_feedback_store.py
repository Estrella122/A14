from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .database import ProductionDatabase
from .engine import normalize_name
from .repository import ScenarioRepository


class SQLiteFeedbackStore:
    STATUSES = {"pending", "approved", "rejected"}

    def __init__(
        self,
        database: ProductionDatabase,
        repository: ScenarioRepository,
        legacy_records_path: Path | None = None,
        approved_knowledge_path: Path | None = None,
    ) -> None:
        self.database = database
        self.repository = repository
        self._migrate(legacy_records_path, approved_knowledge_path)

    def _migrate(self, records_path: Path | None, knowledge_path: Path | None) -> None:
        with self.database.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM feedback_records").fetchone()[0]
        if count:
            return
        records: list[dict[str, Any]] = []
        if records_path and records_path.exists():
            payload = json.loads(records_path.read_text(encoding="utf-8"))
            records.extend(payload.get("records", []))
        elif knowledge_path and knowledge_path.exists():
            knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
            timestamp = self.database.now()
            for scenario_id, fields in knowledge.items():
                for standard_name, aliases in fields.items():
                    for alias in aliases:
                        records.append(
                            {
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
                            }
                        )
        if not records:
            return
        with self.database.transaction() as connection:
            for item in records:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO feedback_records(
                        feedback_id,scenario_id,raw_name,normalized_raw_name,standard_name,
                        status,source,note,submitted_by,submitted_at,reviewed_by,reviewed_at,review_note
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item["feedback_id"],
                        item["scenario_id"],
                        item["raw_name"],
                        item.get("normalized_raw_name") or normalize_name(item["raw_name"]),
                        item["standard_name"],
                        item["status"],
                        item.get("source", "legacy_migration"),
                        item.get("note", ""),
                        item.get("submitted_by", "system_migration"),
                        item.get("submitted_at", self.database.now()),
                        item.get("reviewed_by"),
                        item.get("reviewed_at"),
                        item.get("review_note"),
                    ),
                )
            self.database.audit(
                "system_migration",
                "feedback.migrate",
                "feedback",
                details={"records": len(records)},
                connection=connection,
            )

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
        normalized = normalize_name(raw_name)
        with self.database.transaction() as connection:
            duplicate = connection.execute(
                """
                SELECT * FROM feedback_records
                WHERE scenario_id=? AND normalized_raw_name=? AND standard_name=?
                  AND status IN ('pending','approved')
                ORDER BY submitted_at DESC LIMIT 1
                """,
                (scenario_id, normalized, standard_name),
            ).fetchone()
            if duplicate is not None:
                return {**dict(duplicate), "duplicate": True}
            record = {
                "feedback_id": uuid4().hex,
                "scenario_id": scenario_id,
                "raw_name": raw_name,
                "normalized_raw_name": normalized,
                "standard_name": standard_name,
                "status": "pending",
                "source": str(source or "web_manual")[:80],
                "note": str(note or "").strip()[:500],
                "submitted_by": str(submitted_by or "operator").strip()[:80],
                "submitted_at": self.database.now(),
                "reviewed_by": None,
                "reviewed_at": None,
                "review_note": None,
            }
            connection.execute(
                """
                INSERT INTO feedback_records(
                    feedback_id,scenario_id,raw_name,normalized_raw_name,standard_name,
                    status,source,note,submitted_by,submitted_at,reviewed_by,reviewed_at,review_note
                ) VALUES(:feedback_id,:scenario_id,:raw_name,:normalized_raw_name,:standard_name,
                    :status,:source,:note,:submitted_by,:submitted_at,:reviewed_by,:reviewed_at,:review_note)
                """,
                record,
            )
            self.database.audit(
                record["submitted_by"],
                "feedback.submit",
                "feedback",
                record["feedback_id"],
                {"scenario_id": scenario_id, "standard_name": standard_name},
                connection,
            )
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
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM feedback_records WHERE feedback_id=?", (feedback_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"审核记录不存在：{feedback_id}")
            record = dict(row)
            if record["status"] != "pending":
                if record["status"] == decision:
                    return {**record, "unchanged": True}
                raise ValueError("已完成的审核记录不能改判。")
            if decision == "approved" and approve_callback:
                approve_callback(record["scenario_id"], record["raw_name"], record["standard_name"])
            reviewed_at = self.database.now()
            connection.execute(
                """
                UPDATE feedback_records
                SET status=?, reviewed_by=?, reviewed_at=?, review_note=?
                WHERE feedback_id=?
                """,
                (
                    decision,
                    str(reviewed_by or "reviewer").strip()[:80],
                    reviewed_at,
                    str(review_note or "").strip()[:500],
                    feedback_id,
                ),
            )
            self.database.audit(
                str(reviewed_by or "reviewer")[:80],
                f"feedback.{decision}",
                "feedback",
                feedback_id,
                {"scenario_id": record["scenario_id"], "standard_name": record["standard_name"]},
                connection,
            )
            updated = connection.execute(
                "SELECT * FROM feedback_records WHERE feedback_id=?", (feedback_id,)
            ).fetchone()
        return {**dict(updated), "unchanged": False}

    def revoke(
        self,
        feedback_id: str,
        revoked_by: str,
        revoke_note: str = "",
        revoke_callback: Callable[[str, str, str], Any] | None = None,
    ) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM feedback_records WHERE feedback_id=?", (feedback_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"审核记录不存在：{feedback_id}")
            record = dict(row)
            if record["status"] != "approved":
                raise ValueError("只能撤销已通过的字段知识。")
            other = connection.execute(
                """
                SELECT COUNT(*) FROM feedback_records
                WHERE feedback_id<>? AND scenario_id=? AND normalized_raw_name=?
                  AND standard_name=? AND status='approved'
                """,
                (
                    feedback_id,
                    record["scenario_id"],
                    record["normalized_raw_name"],
                    record["standard_name"],
                ),
            ).fetchone()[0]
            callback_result = None
            if not other and revoke_callback:
                callback_result = revoke_callback(
                    record["scenario_id"], record["raw_name"], record["standard_name"]
                )
            revoked_at = self.database.now()
            actor = str(revoked_by or "local_operator").strip()[:80]
            note = str(revoke_note or "").strip()[:500]
            connection.execute(
                """
                UPDATE feedback_records
                SET status='rejected', revoked_by=?, revoked_at=?, revoke_note=?,
                    review_note=CASE WHEN review_note='' OR review_note IS NULL
                        THEN '已撤销' ELSE review_note || '；已撤销' END
                WHERE feedback_id=?
                """,
                (actor, revoked_at, note, feedback_id),
            )
            self.database.audit(
                actor,
                "feedback.revoked",
                "feedback",
                feedback_id,
                {
                    "scenario_id": record["scenario_id"],
                    "standard_name": record["standard_name"],
                    "learned_alias_removed": bool(callback_result and callback_result.get("removed")),
                },
                connection,
            )
            updated = connection.execute(
                "SELECT * FROM feedback_records WHERE feedback_id=?", (feedback_id,)
            ).fetchone()
        return {
            **dict(updated),
            "knowledge_removed": bool(callback_result and callback_result.get("removed")),
        }

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
                results.append(
                    self.submit(
                        str(row.get("scenario_id", "")),
                        str(row.get("raw_name", "")),
                        str(row.get("standard_name", "")),
                        str(row.get("submitted_by") or submitted_by),
                        "bulk_csv",
                        str(row.get("note", "")),
                    )
                )
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
        safe_limit = max(1, min(int(limit), 1000))
        with self.database.connect() as connection:
            stats = {
                name: connection.execute(
                    "SELECT COUNT(*) FROM feedback_records WHERE status=?", (name,)
                ).fetchone()[0]
                for name in self.STATUSES
            }
            if status:
                rows = connection.execute(
                    "SELECT * FROM feedback_records WHERE status=? ORDER BY submitted_at DESC LIMIT ?",
                    (status, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM feedback_records ORDER BY submitted_at DESC LIMIT ?", (safe_limit,)
                ).fetchall()
        return {
            "records": [dict(row) for row in rows],
            "stats": {**stats, "total": sum(stats.values())},
        }
