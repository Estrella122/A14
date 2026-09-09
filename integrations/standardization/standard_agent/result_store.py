from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd


class PersistentResultStore:
    """Bounded result cache with restart-safe CSV and metadata snapshots."""

    def __init__(self, root: Path, max_results: int = 50, memory_results: int = 12) -> None:
        self.root = root
        self.max_results = max_results
        self.memory_results = memory_results
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.lock = threading.Lock()

    def put(self, result: dict) -> str:
        result_id = uuid4().hex
        with self.lock:
            self.cache[result_id] = result
            self.cache.move_to_end(result_id)
            while len(self.cache) > self.memory_results:
                self.cache.popitem(last=False)
            if isinstance(result.get("standardized_data"), pd.DataFrame):
                self._persist(result_id, result)
                self._prune()
        return result_id

    def get(self, result_id: str) -> dict | None:
        if not re.fullmatch(r"[0-9a-f]{32}", result_id or ""):
            return None
        with self.lock:
            cached = self.cache.get(result_id)
            if cached is not None:
                self.cache.move_to_end(result_id)
                return cached
            restored = self._restore(result_id)
            if restored is not None:
                self.cache[result_id] = restored
                while len(self.cache) > self.memory_results:
                    self.cache.popitem(last=False)
            return restored

    def _persist(self, result_id: str, result: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        frame_path = self.root / f"{result_id}.csv.gz"
        metadata_path = self.root / f"{result_id}.json"
        temporary_frame = frame_path.with_suffix(".csv.gz.tmp")
        temporary_metadata = metadata_path.with_suffix(".json.tmp")
        result["standardized_data"].to_csv(temporary_frame, index=False, compression="gzip")
        metadata = {key: value for key, value in result.items() if key != "standardized_data"}
        payload = {
            "result_id": result_id,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "result": metadata,
        }
        temporary_metadata.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary_frame.replace(frame_path)
        temporary_metadata.replace(metadata_path)

    def _restore(self, result_id: str) -> dict | None:
        frame_path = self.root / f"{result_id}.csv.gz"
        metadata_path = self.root / f"{result_id}.json"
        if not frame_path.exists() or not metadata_path.exists():
            return None
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            result = payload["result"]
            result["standardized_data"] = pd.read_csv(frame_path, compression="gzip")
            return result
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

    def _prune(self) -> None:
        metadata_files = sorted(self.root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for metadata_path in metadata_files[self.max_results :]:
            result_id = metadata_path.stem
            metadata_path.unlink(missing_ok=True)
            (self.root / f"{result_id}.csv.gz").unlink(missing_ok=True)

