from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


MEASUREMENT_PREFIX_CANDIDATES = {
    "TE": "temperature",
    "PT": "pressure",
    "FT": "flow_rate",
}


def normalize_point_id(value: str) -> str:
    return re.sub(r"#+$", "", str(value).strip()).upper()


class PointSemanticDictionary:
    """Exact plant-point knowledge plus deliberately weak prefix candidates."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._rows = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        with self.path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "point_id", "semantic_name", "standard_field", "measurement_type",
            "unit", "equipment", "process_module", "scene", "confidence", "source",
        }
        if rows and not required.issubset(rows[0]):
            raise ValueError(f"点位语义字典缺少列：{sorted(required - set(rows[0]))}")
        return {normalize_point_id(row["point_id"]): row for row in rows}

    def resolve(self, raw_name: str, scenario_id: str, known_fields: set[str]) -> dict[str, Any]:
        point_id = normalize_point_id(raw_name)
        row = self._rows.get(point_id)
        if row:
            same_scene = row["scene"] == scenario_id
            valid_field = row["standard_field"] in known_fields
            status = "resolved" if same_scene and valid_field else "known_other_scene"
            return {
                **row,
                "point_id": point_id,
                "confidence": float(row["confidence"]),
                "status": status,
                "missing_knowledge": [] if status == "resolved" else ["matching_scene_template"],
            }
        prefix_match = re.match(r"^(TE|PT|FT)(?:_|\d)", point_id)
        if prefix_match:
            measurement_type = MEASUREMENT_PREFIX_CANDIDATES[prefix_match.group(1)]
            return {
                "point_id": point_id,
                "semantic_name": measurement_type,
                "standard_field": "",
                "measurement_type": measurement_type,
                "unit": "",
                "equipment": "",
                "process_module": "",
                "scene": "",
                "confidence": 0.35,
                "source": "instrument_prefix_candidate",
                "status": "unresolved",
                "missing_knowledge": ["equipment", "process_module", "scene", "unit", "point_to_standard_field_mapping"],
            }
        return {"status": "not_a_point", "point_id": point_id, "missing_knowledge": []}
