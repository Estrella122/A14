from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from standard_agent import ScenarioRepository


CANDIDATES = ROOT / "knowledge" / "web_alias_candidates.csv"
SOURCES = ROOT / "knowledge" / "web_sources.json"
OUTPUT = ROOT / "training_data" / "web_research" / "web_alias_training.csv"


def variants(text: str, unit: str, role: str) -> list[tuple[str, str]]:
    compact = re.sub(r"[\s\-./()（）\[\]【】]+", "_", text.strip()).strip("_")
    suffix = "SP" if role == "manipulated" else "PV"
    values = [
        (text, "web_phrase"),
        (compact, "web_normalized"),
        (compact.upper(), "web_uppercase"),
        (compact.replace("_", ""), "web_compact"),
        (f"DCS_02_{compact}_{suffix}_11", "web_vendor_tag"),
        (f"Unit3.{compact}.AI", "web_channel_tag"),
    ]
    if unit not in {"", "string", "boolean", "datetime"}:
        values.append((f"{text}[{unit}]", "web_unit_bracket"))
    return list(dict.fromkeys(values))


def main() -> None:
    source_registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    source_ids = {item["source_id"] for item in source_registry["sources"]}
    repository = ScenarioRepository()
    with CANDIDATES.open(encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle))

    rows: list[dict[str, str]] = []
    approved_candidates = 0
    for candidate in candidates:
        if candidate["source_id"] not in source_ids:
            raise ValueError(f"未登记来源：{candidate['source_id']}")
        if candidate["review_status"] != "approved":
            continue
        template = repository.get(candidate["scenario_id"])
        field = template.by_name.get(candidate["standard_name"])
        if field is None:
            raise ValueError(f"不存在标准字段：{candidate['scenario_id']}/{candidate['standard_name']}")
        approved_candidates += 1
        group_id = hashlib.sha256(
            f"web|{candidate['source_id']}|{candidate['scenario_id']}|{candidate['standard_name']}|{candidate['candidate_alias']}".encode("utf-8")
        ).hexdigest()[:16]
        for text, variant_source in variants(candidate["candidate_alias"], field.unit, field.role):
            rows.append(
                {
                    "text": text,
                    "scenario_id": candidate["scenario_id"],
                    "standard_name": field.standard_name,
                    "relevance": "required" if field.required else "useful",
                    "role": field.role,
                    "unit": field.unit,
                    "source": f"web_approved:{candidate['source_id']}:{variant_source}",
                    "group_id": group_id,
                    "split": "external_train",
                    "source_id": candidate["source_id"],
                    "source_url": next(item["url"] for item in source_registry["sources"] if item["source_id"] == candidate["source_id"]),
                }
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    columns = ["text", "scenario_id", "standard_name", "relevance", "role", "unit", "source", "group_id", "split", "source_id", "source_url"]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"approved_candidates": approved_candidates, "training_samples": len(rows), "output": str(OUTPUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
