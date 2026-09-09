from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from standard_agent import ScenarioRepository
from standard_agent.demo import generate_demo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "training_data"


def split_for(value: str) -> str:
    bucket = int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def variants(text: str, unit: str, role: str) -> list[tuple[str, str]]:
    text = str(text).strip()
    compact = re.sub(r"[\s\-./()（）\[\]【】]+", "_", text).strip("_")
    suffix = "SP" if role == "manipulated" else "PV"
    values = [
        (text, "template"),
        (compact, "normalized"),
        (compact.upper(), "uppercase"),
        (compact.replace("_", ""), "compact"),
        (f"{compact}_{suffix}", "control_suffix"),
        (f"{compact}_01", "channel_suffix"),
        (f"A线_{text}", "line_prefix"),
        (f"1号{text}", "equipment_prefix"),
        (f"DCS_03_{compact}_PV_17", "vendor_dcs_tag"),
        (f"HMI.22.{compact}.AI", "vendor_hmi_tag"),
        (f"装置5-{compact}-CH30-VALUE", "vendor_channel_tag"),
        (f"B线#{text}#测点42", "line_point_tag"),
    ]
    if unit not in {"", "string", "boolean", "datetime"}:
        values.extend([(f"{text}[{unit}]", "unit_bracket"), (f"{compact}_{unit}", "unit_suffix")])
    unique = []
    seen = set()
    for value, source in values:
        if value and value not in seen:
            seen.add(value)
            unique.append((value, source))
    return unique


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    repository = ScenarioRepository()
    field_rows = []
    dictionary_rows = []
    for template in repository.list():
        for field in template.fields:
            dictionary_rows.append({"scenario_id": template.scenario_id, "scenario_name": template.scenario_name, **field.as_dict(), "aliases": "|".join(field.aliases)})
            seeds = [field.standard_name, field.display_name, *field.aliases]
            for seed in seeds:
                group_id = hashlib.sha256(f"{template.scenario_id}|{field.standard_name}|{seed}".encode("utf-8")).hexdigest()[:16]
                group_split = split_for(group_id)
                for text, source in variants(seed, field.unit, field.role):
                    field_rows.append(
                        {
                            "text": text,
                            "scenario_id": template.scenario_id,
                            "standard_name": field.standard_name,
                            "relevance": "required" if field.required else "useful",
                            "role": field.role,
                            "unit": field.unit,
                            "source": source,
                            "group_id": group_id,
                            "split": group_split,
                        }
                    )
        negatives = [
            "操作员姓名", "班组备注", "报表序号", "厂商备用测点", "画面颜色", "报警文本", "设备描述", "通讯状态字", "检修记录", "办公室温度",
            "值班员电子签名", "日报打印次数", "画面刷新周期", "交换机端口状态", "摄像头在线标志", "工单审批人", "文件上传时间", "报表模板编号", "账户登录次数",
            "数据库备份状态", "网络往返时延", "鼠标点击计数", "班车到站时间", "厂区门禁记录", "视频码率", "打印机墨粉余量", "巡检照片地址", "软件版本说明", "会议室预约状态",
        ]
        for text in negatives:
            group_id = hashlib.sha256(f"{template.scenario_id}|negative|{text}".encode("utf-8")).hexdigest()[:16]
            group_split = split_for(group_id)
            for value, source in [(text, "negative"), (f"DCS_{text}_25", "negative_vendor"), (f"HMI.60.{text}.RAW", "negative_vendor")]:
                field_rows.append({"text": value, "scenario_id": template.scenario_id, "standard_name": "__irrelevant__", "relevance": "irrelevant", "role": "none", "unit": "", "source": source, "group_id": group_id, "split": group_split})

    dedup = {(row["text"], row["scenario_id"], row["standard_name"]): row for row in field_rows}
    field_rows = sorted(dedup.values(), key=lambda row: (row["split"], row["scenario_id"], row["standard_name"], row["text"]))
    intent_rows = []
    intent_patterns = ["统一{keyword}历史数据字段", "识别这批{keyword}DCS测点", "判断{keyword}数据是否满足建模字段要求", "把{keyword}变量转换成标准格式", "检查{keyword}文件缺少哪些必需字段", "这是{keyword}运行数据"]
    for template in repository.list():
        for keyword in template.config.get("keywords", [])[:6]:
            for pattern in intent_patterns:
                text = pattern.format(keyword=keyword)
                intent_rows.append({"text": text, "scenario_id": template.scenario_id, "scenario_name": template.scenario_name, "split": split_for(f"intent|{template.scenario_id}|{text}")})

    field_columns = ["text", "scenario_id", "standard_name", "relevance", "role", "unit", "source", "group_id", "split"]
    write_csv(OUTPUT / "field_semantics_all.csv", field_rows, field_columns)
    for split in ("train", "validation", "test"):
        rows = [row for row in field_rows if row["split"] == split]
        write_csv(OUTPUT / f"field_semantics_{split}.csv", rows, field_columns)
    write_csv(OUTPUT / "scenario_intents.csv", intent_rows, ["text", "scenario_id", "scenario_name", "split"])
    write_csv(OUTPUT / "multi_scenario_dictionary.csv", dictionary_rows, ["scenario_id", "scenario_name", "standard_name", "display_name", "description", "role", "data_type", "unit", "required", "aliases", "lower_bound", "upper_bound"])

    samples = OUTPUT / "raw_samples"
    samples.mkdir(exist_ok=True)
    for template in repository.list():
        generate_demo(template.scenario_id, rows=360, seed=20260722).to_csv(samples / f"{template.scenario_id}_raw.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "version": "1.0.0",
        "scenarios": [item.summary() for item in repository.list()],
        "field_samples": len(field_rows),
        "intent_samples": len(intent_rows),
        "splits": {split: sum(row["split"] == split for row in field_rows) for split in ("train", "validation", "test")},
        "label_policy": {"required": "场景必需字段", "useful": "可选但具有工艺价值", "irrelevant": "不进入标准数据", "uncertain": "由模型阈值产生，需人工确认"},
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "workbook_payload.json").write_text(
        json.dumps({"manifest": manifest, "field_rows": field_rows, "intent_rows": intent_rows, "dictionary_rows": dictionary_rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
