from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "training_data" / "public_industrial" / "damadics_lublin"
SOURCE_URL = (
    "https://iair.mchtr.pw.edu.pl/layout/set/print/content/download/161/809/"
    "file/damadics-lublin-data-description.zip"
)
SOURCE_PAGE = "https://iair.mchtr.pw.edu.pl/layout/set/print/Damadics"
DESCRIPTION_SHA256 = "ee6f4083fae635c34bd6e33b068553a401e9e182e50f0914c5956f3073b7625a"
DATA_PART1_URL = (
    "https://iair.mchtr.pw.edu.pl/layout/set/print/content/download/163/817/"
    "file/Lublin_all_data_part1.zip"
)
DATA_PART1_SHA256 = "4fea6d279b1077bc51a15a21170144125e9e973214de57b1f8b622e16ba774a3"


FIELDS = [
    (1, "-", "timestamp", "Time stamp", "0-86399", "s"),
    (2, "P51_05", "P1", "juice pressure (valve inlet)", "0-1000", "kPa"),
    (3, "P51_06", "P2", "juice pressure (valve outlet)", "0-1000", "kPa"),
    (4, "T51_01", "T", "juice temperature (valve outlet)", "50-150", "degC"),
    (5, "F51_01", "F", "juice flow (1st evaporator inlet)", "0-500", "m3/h"),
    (6, "LC51_03CV", "CV", "control value (controller output)", "0-100", "percent"),
    (7, "LC51_03X", "X", "servomotor rod displacement", "0-100", "percent"),
    (8, "LC51_03PV", "PV", "juice level in 1st evaporator", "0-100", "percent"),
    (9, "TC51_05", "temperature", "juice temperature (1st evaporator inlet)", "50-150", "degC"),
    (10, "T51_08", "temperature", "juice temperature (1st evaporator outlet)", "50-150", "degC"),
    (11, "D51_01", "density", "juice density (1st evaporator inlet)", "0-25", "Bx"),
    (12, "D51_02", "density", "juice density (1st evaporator outlet)", "13-41", "Bx"),
    (13, "F51_02", "steam_flow", "steam flow", "1-100", "t/h"),
    (14, "PC51_01", "steam_pressure", "steam pressure", "100-300", "kPa"),
    (15, "T51_06", "steam_temperature", "steam temperature", "50-150", "degC"),
    (16, "P51_03", "vapour_pressure", "vapour pressure", "0-250", "kPa"),
    (17, "T51_07", "vapour_temperature", "vapour temperature", "50-150", "degC"),
    (18, "P57_03", "P1", "juice pressure (valve inlet)", "0-1000", "kPa"),
    (19, "P57_04", "P2", "juice pressure (valve outlet)", "0-1000", "kPa"),
    (20, "T57_03", "T", "juice temperature (valve inlet)", "0-150", "degC"),
    (21, "FC57_03PV", "PV", "juice flow (5th evaporator outlet)", "0-100", "m3/h"),
    (22, "FC57_03CV", "CV", "control value (controller output)", "0-100", "percent"),
    (23, "FC57_03X", "X", "servomotor rod displacement", "0-100", "percent"),
    (24, "P74_00", "P1", "water pressure (valve inlet)", "0-4000", "kPa"),
    (25, "P74_01", "P2", "water pressure (valve outlet)", "0-4000", "kPa"),
    (26, "T74_00", "T", "water temperature (valve outlet)", "0-150", "degC"),
    (27, "F74_00", "F", "water flow (steam boiler inlet)", "0-40", "t/h"),
    (28, "LC74_20CV", "CV", "control value (controller output)", "0-100", "percent"),
    (29, "LC74_20X", "X", "servomotor rod displacement", "0-100", "percent"),
    (30, "LC74_20PV", "PV", "water level in steam boiler", "0-100", "percent"),
    (31, "F74_30", "steam_flow", "steam flow (steam boiler outlet)", "0-40", "t/h"),
    (32, "P74_30", "steam_pressure", "steam pressure (steam boiler outlet)", "0-4000", "kPa"),
    (33, "T74_30", "steam_temperature", "steam temperature (steam boiler outlet)", "0-550", "degC"),
]

APPROVED_MAPPING = {
    "timestamp": ("thermal_power_boiler", "timestamp", "approved"),
    "F74_00": ("thermal_power_boiler", "feedwater_flow", "approved"),
    "LC74_20PV": ("thermal_power_boiler", "drum_level", "review"),
    "F74_30": ("thermal_power_boiler", "main_steam_flow", "approved"),
    "P74_30": ("thermal_power_boiler", "main_steam_pressure", "approved"),
    "T74_30": ("thermal_power_boiler", "main_steam_temperature", "approved"),
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for column, tag, symbol, description, value_range, unit in FIELDS:
        mapping = APPROVED_MAPPING.get(tag)
        rows.append(
            {
                "column": column,
                "actuator": "1" if column <= 17 else "2" if column <= 23 else "3",
                "raw_tag": tag,
                "variable_symbol": symbol,
                "description": description,
                "range": value_range,
                "unit": unit,
                "target_scenario": mapping[0] if mapping else "",
                "target_standard_name": mapping[1] if mapping else "",
                "review_status": mapping[2] if mapping else "external_only",
            }
        )
    dictionary = OUTPUT / "damadics_field_dictionary.csv"
    with dictionary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "dataset": "DAMADICS Lublin Sugar Factory actuator benchmark",
        "source_type": "real_factory_public_benchmark",
        "source_page": SOURCE_PAGE,
        "description_download": SOURCE_URL,
        "description_sha256": DESCRIPTION_SHA256,
        "data_part1_download": DATA_PART1_URL,
        "data_part1_sha256": DATA_PART1_SHA256,
        "data_part1_days": 7,
        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "field_count": len(rows),
        "recording_shape": "86400 rows x 33 columns per day",
        "sampling": "1 Hz",
        "data_period": "2001-10-27 to 2001-11-23",
        "license_status": "No explicit redistribution license found on the official page.",
        "use_policy": (
            "Field metadata is retained with provenance. Only semantically equivalent mappings marked "
            "approved enter training; review and external_only rows stay isolated."
        ),
        "approved_mappings": sum(row["review_status"] == "approved" for row in rows),
        "review_mappings": sum(row["review_status"] == "review" for row in rows),
        "dictionary_sha256": hashlib.sha256(dictionary.read_bytes()).hexdigest(),
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "README.md").write_text(
        "# DAMADICS 真实工业字段包\n\n"
        "该字段包来自 DAMADICS 项目方官网公布的 Lublin 糖厂执行器基准说明书。"
        "每个日文件包含 86,400 行、33 列，采样频率为 1 Hz。\n\n"
        "本工程只将语义与单位均可确认等价的标签加入训练；汽包水位的公开标签为百分比，"
        "本工程标准字段为毫米，因此保留为 `review`，不会自动参训。\n\n"
        "官网未给出明确再分发许可证，因此交付包包含字段字典、来源、哈希和下载脚本，"
        "不把完整原始日文件重新打包分发。\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
