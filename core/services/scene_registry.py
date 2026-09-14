from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


REGISTRY_PATH = Path(settings.BASE_DIR) / "frontend" / "src" / "data" / "scenes.json"


@lru_cache(maxsize=1)
def list_scene_configs() -> list[dict]:
    rows = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    ids = [row.get("id") for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("场景注册表包含空 ID 或重复 ID。")
    return rows


def get_scene_config(scene_id: str) -> dict | None:
    return next((row for row in list_scene_configs() if row["id"] == scene_id), None)


def identify_registered_scene(text: str) -> dict | None:
    normalized = str(text or "").lower()
    candidates = []
    for row in list_scene_configs():
        hits = [alias for alias in row.get("aliases", []) if alias.lower() in normalized]
        if hits:
            candidates.append((max(map(len, hits)), row))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None
