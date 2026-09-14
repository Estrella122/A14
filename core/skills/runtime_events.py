from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError, transaction
from django.test.testcases import DatabaseOperationForbidden


EVENTS_DIR = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / "agent_skill_runs"
MAX_EVENTS = 500
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock(run_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(run_id, threading.Lock())


class RuntimeEventStore:
    """Append-only, cursor-addressable operational events for one Skill run."""

    def __init__(self, skill_run_id: str, pipeline_run_id: str | None = None):
        self.skill_run_id = skill_run_id
        self.pipeline_run_id = pipeline_run_id
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.events_path = EVENTS_DIR / f"{skill_run_id}.events.jsonl"
        self.state_path = EVENTS_DIR / f"{skill_run_id}.live.json"
        database_state = None
        try:
            from core.models import SkillRunRecord
            record, _ = SkillRunRecord.objects.get_or_create(
                skill_run_id=skill_run_id,
                defaults={"pipeline_run_id": pipeline_run_id or "", "status": "running"},
            )
            database_state = {
                "skill_run_id": record.skill_run_id, "run_id": record.pipeline_run_id or pipeline_run_id,
                "status": record.status, "last_sequence": record.last_sequence,
                "event_count": record.event_count, "payload_bytes": record.payload_bytes,
                "result": record.result, "error": record.error or None,
            }
        except (OperationalError, ProgrammingError, DatabaseOperationForbidden):
            pass
        if not self.state_path.exists():
            self._write_state(database_state or {"skill_run_id": skill_run_id, "run_id": pipeline_run_id, "status": "running", "last_sequence": 0, "event_count": 0, "payload_bytes": 0, "result": None, "error": None})

    def _read_state(self) -> dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"skill_run_id": self.skill_run_id, "run_id": self.pipeline_run_id, "status": "running", "last_sequence": 0, "event_count": 0, "payload_bytes": 0}

    def _write_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().astimezone().isoformat(timespec="milliseconds")
        temporary = self.state_path.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
        temporary.write_text(json.dumps(state, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def emit(self, event_type: str, *, stage: str, status: str, message: str,
             skill_id: str | None = None, capability_id: str | None = None,
             executor: str | None = None, progress: float | None = None,
             metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        with _lock(self.skill_run_id):
            state = self._read_state()
            sequence = int(state.get("last_sequence", 0)) + 1
            event = {
                "sequence": sequence,
                "run_id": state.get("run_id") or self.pipeline_run_id,
                "skill_run_id": self.skill_run_id,
                "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
                "event_type": event_type,
                "stage": stage,
                "skill_id": skill_id,
                "capability_id": capability_id,
                "executor": executor,
                "status": status,
                "message": message,
                "progress": progress,
                "metadata": metadata or {},
            }
            encoded = json.dumps(event, ensure_ascii=False, default=str)
            with self.events_path.open("a", encoding="utf-8") as stream:
                stream.write(encoded + "\n")
            state.update(last_sequence=sequence, event_count=int(state.get("event_count", 0)) + 1,
                         payload_bytes=int(state.get("payload_bytes", 0)) + len(encoded.encode("utf-8")))
            if state["event_count"] > MAX_EVENTS:
                retained = self.events_path.read_text(encoding="utf-8").splitlines()[-MAX_EVENTS:]
                self.events_path.write_text("\n".join(retained) + "\n", encoding="utf-8")
                state["history_truncated"] = True
                state["retained_event_count"] = len(retained)
            self._write_state(state)
            try:
                from core.models import SkillRunEvent, SkillRunRecord
                with transaction.atomic():
                    record = SkillRunRecord.objects.select_for_update().get(skill_run_id=self.skill_run_id)
                    sequence = record.last_sequence + 1
                    event["sequence"] = sequence
                    encoded_bytes = len(json.dumps(event, ensure_ascii=False, default=str).encode("utf-8"))
                    SkillRunEvent.objects.create(
                        run=record, sequence=sequence, event_type=event_type, stage=stage,
                        status=status, message=message, payload=event,
                    )
                    record.last_sequence = sequence
                    record.event_count += 1
                    record.payload_bytes += encoded_bytes
                    record.save(update_fields=("last_sequence", "event_count", "payload_bytes", "updated_at"))
                    stale_ids = list(record.events.order_by("-sequence").values_list("pk", flat=True)[MAX_EVENTS:])
                    if stale_ids:
                        SkillRunEvent.objects.filter(pk__in=stale_ids).delete()
            except (OperationalError, ProgrammingError, DatabaseOperationForbidden):
                pass
            return event

    def finish(self, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        with _lock(self.skill_run_id):
            state = self._read_state()
            state.update(status=status, result=result, error=error)
            self._write_state(state)
            try:
                from core.models import SkillRunRecord
                SkillRunRecord.objects.filter(skill_run_id=self.skill_run_id).update(
                    status=status, result=result, error=error or "",
                )
            except (OperationalError, ProgrammingError, DatabaseOperationForbidden):
                pass

    def snapshot(self, after: int = 0, limit: int = 100) -> dict[str, Any]:
        try:
            from core.models import SkillRunRecord
            record = SkillRunRecord.objects.get(skill_run_id=self.skill_run_id)
            rows = record.events.filter(sequence__gt=after).order_by("sequence")[:max(1, min(limit, MAX_EVENTS))]
            events = [row.payload for row in rows]
            count = record.event_count
            return {
                "skill_run_id": record.skill_run_id, "run_id": record.pipeline_run_id or None,
                "status": record.status, "last_sequence": record.last_sequence,
                "event_count": count, "payload_bytes": record.payload_bytes,
                "result": record.result, "error": record.error or None,
                "updated_at": record.updated_at.isoformat(), "events": events,
                "next_sequence": events[-1]["sequence"] if events else after,
                "has_more": bool(events and events[-1]["sequence"] < record.last_sequence),
                "metrics": {"event_count": count, "average_payload_bytes": round(record.payload_bytes / count, 1) if count else 0},
            }
        except (OperationalError, ProgrammingError, DatabaseOperationForbidden):
            pass
        except Exception as exc:
            if exc.__class__.__name__ != "DoesNotExist":
                raise
        state = self._read_state()
        events: list[dict[str, Any]] = []
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if int(event.get("sequence", 0)) > after:
                    events.append(event)
        events = events[:max(1, min(limit, MAX_EVENTS))]
        count = int(state.get("event_count", 0))
        return {
            **state,
            "events": events,
            "next_sequence": events[-1]["sequence"] if events else after,
            "has_more": bool(events and events[-1]["sequence"] < int(state.get("last_sequence", 0))),
            "metrics": {"event_count": count, "average_payload_bytes": round(int(state.get("payload_bytes", 0)) / count, 1) if count else 0},
        }


def get_runtime_event_store(skill_run_id: str) -> RuntimeEventStore | None:
    store = RuntimeEventStore.__new__(RuntimeEventStore)
    store.skill_run_id = skill_run_id
    store.pipeline_run_id = None
    store.events_path = EVENTS_DIR / f"{skill_run_id}.events.jsonl"
    store.state_path = EVENTS_DIR / f"{skill_run_id}.live.json"
    if store.state_path.exists():
        return store
    try:
        from core.models import SkillRunRecord
        return store if SkillRunRecord.objects.filter(skill_run_id=skill_run_id).exists() else None
    except (OperationalError, ProgrammingError, DatabaseOperationForbidden):
        return None
