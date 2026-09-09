from __future__ import annotations

import csv
import json
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from standard_agent import StandardizationAgent


ARCHIVE = ROOT / ".runtime" / "external_data" / "damadics" / "Lublin_all_data_part1.zip"
MEMBER = "Lublin_all_data/01112001.txt"
OUTPUT = ROOT / "training_data" / "public_industrial" / "damadics_lublin"
ALL_COLUMNS = [
    "time_seconds", "P51_05", "P51_06", "T51_01", "F51_01", "LC51_03CV",
    "LC51_03X", "LC51_03PV", "TC51_05", "T51_08", "D51_01", "D51_02",
    "F51_02", "PC51_01", "T51_06", "P51_03", "T51_07", "P57_03", "P57_04",
    "T57_03", "FC57_03PV", "FC57_03CV", "FC57_03X", "P74_00", "P74_01",
    "T74_00", "F74_00", "LC74_20CV", "LC74_20X", "LC74_20PV", "F74_30",
    "P74_30", "T74_30",
]
BOILER_COLUMNS = [
    "timestamp", "P74_00", "P74_01", "T74_00", "F74_00", "LC74_20CV",
    "LC74_20X", "LC74_20PV", "F74_30", "P74_30", "T74_30",
]


def read_sample(rows: int = 2000) -> pd.DataFrame:
    if not ARCHIVE.exists():
        raise FileNotFoundError(
            f"真实数据包不存在：{ARCHIVE}。请先运行 tools/download_damadics_public_data.sh"
        )
    values = []
    with zipfile.ZipFile(ARCHIVE) as archive, archive.open(MEMBER) as handle:
        for index, raw_line in enumerate(handle):
            if index >= rows:
                break
            parts = raw_line.decode("ascii").strip().split("\t")
            if len(parts) != len(ALL_COLUMNS):
                raise ValueError(f"第 {index + 1} 行列数异常：{len(parts)}")
            values.append(parts)
    frame = pd.DataFrame(values, columns=ALL_COLUMNS).apply(pd.to_numeric, errors="coerce")
    start = datetime(2001, 11, 1)
    frame["timestamp"] = frame["time_seconds"].map(
        lambda seconds: start + timedelta(seconds=int(seconds))
    )
    return frame[BOILER_COLUMNS]


def main() -> None:
    frame = read_sample()
    result = StandardizationAgent().standardize(
        frame,
        scenario_id="thermal_power_boiler",
        instruction="DAMADICS Lublin糖厂蒸汽锅炉执行器3真实历史数据",
    )
    mappings = result["mapping"]["mappings"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mapping_path = OUTPUT / "damadics_real_data_mapping_report.csv"
    columns = [
        "raw", "standard", "display_name", "role", "detected_unit", "expected_unit",
        "confidence", "method", "status",
    ]
    with mapping_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(mappings)
    accepted = [item for item in mappings if item["status"] == "matched"]
    report = {
        "dataset": "DAMADICS Lublin Sugar Factory",
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "member": MEMBER,
        "rows_checked": len(frame),
        "raw_columns": len(frame.columns),
        "scenario_for_review": result["scenario"]["scenario_id"],
        "matched_fields": {item["raw"]: item["standard"] for item in accepted},
        "review_fields": [item["raw"] for item in mappings if item["status"] == "review"],
        "unmapped_fields": [item["raw"] for item in mappings if item["status"] == "unmapped"],
        "withheld_fields": {
            item["raw"]: item["status"] for item in mappings if item["status"] != "matched"
        },
        "required_coverage": result["mapping"]["required_coverage"],
        "file_status": result["data_decision"]["status"],
        "file_reasons": result["data_decision"]["reasons"],
        "expected_policy": (
            "The public sample covers only a boiler water/steam subsystem. It must not be marked ready "
            "for the full thermal-power-boiler template when combustion-side required fields are absent."
        ),
        "passed": (
            len(frame) == 2000
            and {"timestamp", "feedwater_flow", "main_steam_flow", "main_steam_pressure", "main_steam_temperature"}
            .issubset({item["standard"] for item in accepted})
            and "LC74_20PV" not in {item["raw"] for item in accepted}
            and result["data_decision"]["status"] != "ready"
        ),
    }
    (OUTPUT / "damadics_real_data_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
