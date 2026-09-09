from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "training_data" / "field_semantics_all.csv"
OUTPUT = ROOT / "training_data" / "multi_angle_training" / "field_semantics_multi_angle.csv"
MANIFEST = ROOT / "training_data" / "multi_angle_training" / "manifest.json"


def compact(text: str) -> str:
    return re.sub(r"[\s\-./()（）\[\]【】#:]+", "_", text.strip()).strip("_")


def variants(text: str, unit: str, irrelevant: bool) -> list[tuple[str, str]]:
    token = compact(text)
    values = [
        (f"PLC01.{token}.VALUE", "plc_vendor_envelope"),
        (f"DCS-A-{token}-PV-07", "dcs_vendor_envelope"),
        (f"2号线_{token}_测点A12", "equipment_channel_context"),
        (f"{token.lower()}_raw", "case_and_suffix_noise"),
        (token.replace("_", "."), "separator_noise"),
    ]
    if not irrelevant and unit not in {"", "string", "boolean", "datetime"}:
        values.extend(
            [
                (f"{text}({unit})", "unit_parenthesis"),
                (f"{token}__{unit}__AI", "unit_channel_mix"),
            ]
        )
    return list(dict.fromkeys(values))


def main() -> None:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    # Only augment training groups. Validation and test aliases remain untouched.
    anchors = [row for row in source_rows if row["split"] == "train" and row["source"] == "template"]
    generated: list[dict[str, str]] = []
    angle_counts: dict[str, int] = {}
    for row in anchors:
        for text, angle in variants(row["text"], row["unit"], row["standard_name"] == "__irrelevant__"):
            angle_counts[angle] = angle_counts.get(angle, 0) + 1
            generated.append(
                {
                    **row,
                    "text": text,
                    "source": f"multi_angle:{angle}",
                    "group_id": hashlib.sha256(
                        f"multi-angle|{row['group_id']}|{angle}|{text}".encode("utf-8")
                    ).hexdigest()[:16],
                    "split": "external_train",
                    "training_angle": angle,
                }
            )

    deduplicated = {
        (row["text"], row["scenario_id"], row["standard_name"]): row for row in generated
    }
    rows = sorted(
        deduplicated.values(),
        key=lambda row: (row["scenario_id"], row["standard_name"], row["text"]),
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "text", "scenario_id", "standard_name", "relevance", "role", "unit",
        "source", "group_id", "split", "training_angle",
    ]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "version": "1.0.0",
        "policy": "Only base training groups are augmented; validation and test groups are isolated.",
        "source_anchors": len(anchors),
        "training_samples": len(rows),
        "angles": angle_counts,
        "output": str(OUTPUT.relative_to(ROOT)),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
