from __future__ import annotations

import argparse
import csv
import json
import random
import re
from pathlib import Path

from standard_agent import ScenarioRepository, StandardizationAgent
from standard_agent.demo import generate_demo
from standard_agent.ml_model import CharNGramCentroidModel


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "field_semantic_model.json"
DEFAULT_OUTPUT = ROOT / "training_data" / "random_challenge"

VENDORS = ["DCS", "PLC", "SIS", "RTU", "HMI", "APC"]
SUFFIXES = ["PV", "AI", "RAW", "VALUE", "MEAS"]
LINES = ["A线", "B线", "1号机组", "二期", "主控", "现场"]
IRRELEVANT = [
    "值班员电子签名", "日报打印次数", "画面刷新周期", "交换机端口状态", "摄像头在线标志",
    "工单审批人", "文件上传时间", "办公室湿度", "报表模板编号", "账户登录次数",
    "数据库备份状态", "网络往返时延", "鼠标点击计数", "班车到站时间", "厂区门禁记录",
    "视频码率", "打印机墨粉余量", "巡检照片地址", "软件版本说明", "会议室预约状态",
]


def compact(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", str(text)).strip("_")


def challenge_name(field, rng: random.Random) -> str:
    bases = [field.display_name, field.standard_name, *field.aliases]
    base = compact(rng.choice([item for item in bases if item]))
    channel = rng.randint(2, 99)
    style = rng.randrange(4)
    if style == 0:
        return f"{rng.choice(VENDORS)}_{rng.randint(1, 6):02d}_{base}_{rng.choice(SUFFIXES)}_{channel:02d}"
    if style == 1:
        return f"{rng.choice(LINES)}#{base}#测点{channel}"
    if style == 2:
        return f"{rng.choice(VENDORS)}.{rng.randint(10, 88)}.{base}.{rng.choice(SUFFIXES)}"
    return f"装置{rng.randint(1, 9)}-{base}-CH{channel:02d}-{rng.choice(SUFFIXES)}"


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(model: CharNGramCentroidModel, rows: list[dict]) -> dict:
    threshold = float(model.metadata["accept_threshold"])
    relevant = [row for row in rows if row["standard_name"] != "__irrelevant__"]
    negatives = [row for row in rows if row["standard_name"] == "__irrelevant__"]
    top1 = top3 = accepted = false_accepts = 0
    errors = []
    for row in relevant:
        predictions = model.predict(row["text"], row["scenario_id"], limit=3)
        labels = [item["standard_name"] for item in predictions]
        score = predictions[0]["score"] if predictions else 0.0
        top1 += bool(labels and labels[0] == row["standard_name"])
        top3 += row["standard_name"] in labels
        accepted += bool(predictions and predictions[0]["standard_name"] != "__irrelevant__" and score >= threshold)
        if not labels or labels[0] != row["standard_name"] or score < threshold:
            errors.append({**row, "predicted": labels[0] if labels else None, "score": score})
    for row in negatives:
        predictions = model.predict(row["text"], row["scenario_id"], limit=1)
        score = predictions[0]["score"] if predictions else 0.0
        if predictions and predictions[0]["standard_name"] != "__irrelevant__" and score >= threshold:
            false_accepts += 1
            errors.append({**row, "predicted": predictions[0]["standard_name"], "score": score})
    return {
        "relevant_samples": len(relevant),
        "irrelevant_samples": len(negatives),
        "top1_accuracy": round(top1 / max(len(relevant), 1), 4),
        "top3_accuracy": round(top3 / max(len(relevant), 1), 4),
        "relevant_accept_recall": round(accepted / max(len(relevant), 1), 4),
        "irrelevant_false_accept_rate": round(false_accepts / max(len(negatives), 1), 4),
        "errors": errors,
    }


def build_raw_file(repository: ScenarioRepository, rng: random.Random, output: Path) -> dict:
    template = rng.choice(repository.list())
    original = generate_demo(template.scenario_id, rows=240, seed=rng.randint(1, 10_000_000))
    agent = StandardizationAgent(repository)
    baseline = agent.standardize(original, scenario_id=template.scenario_id)
    field_by_standard = {field.standard_name: field for field in template.fields}
    expected = {}
    rename = {}
    for item in baseline["mapping"]["mappings"]:
        if item.get("standard") in field_by_standard:
            generated = challenge_name(field_by_standard[item["standard"]], rng)
            rename[item["raw"]] = generated
            expected[generated] = item["standard"]
    challenged = original.rename(columns=rename)
    challenged[f"{rng.choice(VENDORS)}_网络心跳_{rng.randint(10,99)}"] = rng.choice([0, 1])
    challenged["值班员电子签名"] = "operator_test"
    challenged.to_csv(output, index=False, encoding="utf-8-sig")
    result = agent.standardize(challenged, scenario_id="auto")
    predicted = {item["raw"]: item.get("standard") for item in result["mapping"]["mappings"]}
    correct = sum(predicted.get(raw) == standard for raw, standard in expected.items())
    return {
        "scenario_id": template.scenario_id,
        "scenario_name": template.scenario_name,
        "rows": len(challenged),
        "input_fields": len(challenged.columns),
        "labeled_fields": len(expected),
        "correct_fields": correct,
        "field_accuracy": round(correct / max(len(expected), 1), 4),
        "detected_scenario": result["scenario"]["scenario_id"],
        "file_status": result["data_decision"]["status"],
        "required_coverage": result["mapping"]["required_coverage"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成并评估随机厂商字段盲测集")
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--variants", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    repository = ScenarioRepository()
    model = CharNGramCentroidModel.load(MODEL)
    rows = []
    for template in repository.list():
        for field in template.fields:
            for _ in range(args.variants):
                rows.append({"text": challenge_name(field, rng), "scenario_id": template.scenario_id, "standard_name": field.standard_name, "relevance": "required" if field.required else "useful"})
        for text in rng.sample(IRRELEVANT, min(len(IRRELEVANT), args.variants * 3)):
            rows.append({"text": f"{rng.choice(VENDORS)}_{compact(text)}_{rng.randint(10,99)}", "scenario_id": template.scenario_id, "standard_name": "__irrelevant__", "relevance": "irrelevant"})
    rng.shuffle(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "random_field_challenge.csv", rows, ["text", "scenario_id", "standard_name", "relevance"])
    metrics = evaluate(model, rows)
    raw_result = build_raw_file(repository, rng, args.output / "random_raw_timeseries.csv")
    thresholds = {"top1_accuracy": 0.90, "relevant_accept_recall": 0.85, "irrelevant_false_accept_rate": 0.05, "raw_field_accuracy": 0.85, "raw_required_coverage": 0.85}
    passed = (
        metrics["top1_accuracy"] >= thresholds["top1_accuracy"]
        and metrics["relevant_accept_recall"] >= thresholds["relevant_accept_recall"]
        and metrics["irrelevant_false_accept_rate"] <= thresholds["irrelevant_false_accept_rate"]
        and raw_result["field_accuracy"] >= thresholds["raw_field_accuracy"]
        and raw_result["required_coverage"] >= thresholds["raw_required_coverage"]
        and raw_result["file_status"] != "reject"
    )
    report = {"seed": args.seed, "passed": passed, "thresholds": thresholds, "field_challenge": metrics, "raw_file": raw_result}
    (args.output / "random_challenge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
