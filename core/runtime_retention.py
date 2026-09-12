from __future__ import annotations

import json
import shutil
import time
from pathlib import Path


def retention_candidates(base_dir: Path, keep: int = 100, days: int = 30, runtime_root: Path | None = None) -> list[Path]:
    if keep < 1 or days < 1:
        raise ValueError("keep 和 days 必须大于 0")
    runtime = Path(runtime_root).resolve() if runtime_root is not None else Path(base_dir).resolve() / "runtime"
    cutoff = time.time() - days * 86400
    candidates: list[Path] = []

    pipeline_root = runtime / "pipeline_runs"
    latest_id = None
    latest_path = pipeline_root / "latest.json"
    if latest_path.is_file():
        try:
            latest_id = json.loads(latest_path.read_text(encoding="utf-8")).get("run_id")
        except (OSError, ValueError, TypeError):
            latest_id = None
    pipeline_runs = sorted(
        (path for path in pipeline_root.iterdir() if path.is_dir() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if pipeline_root.is_dir() else []
    for index, path in enumerate(pipeline_runs):
        if path.name != latest_id and (index >= keep or path.stat().st_mtime < cutoff):
            candidates.append(path)

    skill_root = runtime / "agent_skill_runs"
    skill_runs = sorted(
        (path for path in skill_root.glob("skillrun_*.json") if path.is_file() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if skill_root.is_dir() else []
    for index, path in enumerate(skill_runs):
        if index >= keep or path.stat().st_mtime < cutoff:
            candidates.append(path)
    return candidates


def prune_runtime(base_dir: Path, keep: int = 100, days: int = 30, apply: bool = False, runtime_root: Path | None = None) -> dict:
    targets = retention_candidates(base_dir, keep=keep, days=days, runtime_root=runtime_root)
    removed_bytes = sum(path.stat().st_size if path.is_file() else sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) for path in targets)
    if apply:
        for path in targets:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    return {
        "mode": "apply" if apply else "dry-run",
        "candidate_count": len(targets),
        "removed_bytes": removed_bytes if apply else 0,
        "reclaimable_bytes": removed_bytes,
        "targets": [str(path) for path in targets],
    }
