from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


class ProductionDatabase:
    """Thread-safe SQLite persistence with WAL, migrations, audit, and backups."""

    SCHEMA_VERSION = 2

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.initialize()

    @staticmethod
    def now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            connection = self.connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def initialize(self) -> None:
        connection = self.connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.commit()
        finally:
            connection.close()
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                DROP TABLE IF EXISTS sessions;
                DROP TABLE IF EXISTS users;
                CREATE TABLE IF NOT EXISTS feedback_records (
                    feedback_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    raw_name TEXT NOT NULL,
                    normalized_raw_name TEXT NOT NULL,
                    standard_name TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
                    source TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    submitted_by TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_note TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_status_time
                    ON feedback_records(status, submitted_at DESC);
                CREATE INDEX IF NOT EXISTS idx_feedback_lookup
                    ON feedback_records(scenario_id, normalized_raw_name, standard_name, status);
                CREATE TABLE IF NOT EXISTS audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    resource_id TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at DESC);
                """
            )
            feedback_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(feedback_records)").fetchall()
            }
            for name in ("revoked_by", "revoked_at", "revoke_note"):
                if name not in feedback_columns:
                    connection.execute(f"ALTER TABLE feedback_records ADD COLUMN {name} TEXT")
            connection.execute(
                "INSERT INTO metadata(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(self.SCHEMA_VERSION),),
            )

    def audit(
        self,
        actor: str,
        action: str,
        resource: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        values = (
            actor,
            action,
            resource,
            resource_id,
            json.dumps(details or {}, ensure_ascii=False, separators=(",", ":")),
            self.now(),
        )
        statement = (
            "INSERT INTO audit_log(actor, action, resource, resource_id, details_json, created_at) "
            "VALUES(?,?,?,?,?,?)"
        )
        if connection is not None:
            connection.execute(statement, values)
            return
        with self.transaction() as own_connection:
            own_connection.execute(statement, values)

    def list_audit(self, limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT ?", (safe_limit,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json") or "{}")
            result.append(item)
        return result

    def backup(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        target = directory / f"a14_task2_{stamp}.sqlite3"
        with self.lock:
            source_connection = self.connect()
            target_connection = sqlite3.connect(target)
            try:
                source_connection.backup(target_connection)
            finally:
                target_connection.close()
                source_connection.close()
        return target
