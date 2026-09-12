from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeArtifactRef:
    run_id: str
    skill_id: str
    artifact_type: str
    path: str
    version: str = "1"
    created_at: str | None = None
    source_execution_id: str | None = None

    def public(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeArtifactResolver:
    def __init__(self, snapshot: dict[str, Any], state: dict[str, Any] | None = None):
        self.snapshot = snapshot
        self.state = state if state is not None else {}

    def resolve(self, artifact_type: str, skill_id: str = "pipeline") -> RuntimeArtifactRef | None:
        state_ref = (self.state.get("artifact_refs") or {}).get(artifact_type)
        if isinstance(state_ref, RuntimeArtifactRef):
            return state_ref
        run_id = str(self.snapshot.get("run_id") or "")
        if not run_id or artifact_type not in self.snapshot.get("artifacts", {}):
            return None
        try:
            from core.services.pipeline import resolve_artifact
            path, _ = resolve_artifact(run_id, artifact_type)
        except Exception:
            return None
        return RuntimeArtifactRef(
            run_id=run_id, skill_id=skill_id, artifact_type=artifact_type, path=str(path),
            created_at=self.snapshot.get("updated_at") or self.snapshot.get("created_at"),
            source_execution_id=run_id,
        )

    def register(self, artifact_type: str, path: str | Path, skill_id: str, source_execution_id: str) -> RuntimeArtifactRef:
        ref = RuntimeArtifactRef(
            run_id=str(self.snapshot.get("run_id") or source_execution_id), skill_id=skill_id,
            artifact_type=artifact_type, path=str(path), created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            source_execution_id=source_execution_id,
        )
        self.state.setdefault("artifact_refs", {})[artifact_type] = ref
        return ref
