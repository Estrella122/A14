from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path

import pandas as pd

from standard_agent import ScenarioRepository, StandardizationAgent
from standard_agent.demo import generate_demo
from standard_agent.ml_model import CharNGramCentroidModel
from training.random_challenge import IRRELEVANT, MODEL, VENDORS, challenge_name, compact, evaluate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "training_data" / "multi_angle_evaluation"


def challenged_frame(agent: StandardizationAgent, template, rng: random.Random, rows: int = 120) -> tuple[pd.DataFrame, dict[str, str]]:
    original = generate_demo(template.scenario_id, rows=rows, seed=rng.randint(1, 10_000_000))
    baseline = agent.standardize(original, scenario_id=template.scenario_id)
    fields = template.by_name
    rename = {}
    expected = {}
    used = set()
    for item in baseline["mapping"]["mappings"]:
        standard = item.get("standard")
        if standard not in fields:
            continue
        generated = challenge_name(fields[standard], rng)
        while generated in used:
            generated = challenge_name(fields[standard], rng)
        used.add(generated)
        rename[item["raw"]] = generated
        expected[generated] = standard
    return original.rename(columns=rename), expected


def mapping_accuracy(result: dict, expected: dict[str, str]) -> float:
    predicted = {item["raw"]: item.get("standard") for item in result["mapping"]["mappings"]}
    correct = sum(predicted.get(raw) == standard for raw, standard in expected.items())
    return round(correct / max(len(expected), 1), 4)


def case(seed: int, angle: str, template, result: dict, expected: dict[str, str], passed: bool, notes: str = "") -> dict:
    return {
        "seed": seed,
        "angle": angle,
        "expected_scenario": template.scenario_id if template else "none",
        "detected_scenario": result["scenario"]["scenario_id"],
        "field_accuracy": mapping_accuracy(result, expected) if expected else None,
        "required_coverage": result["mapping"]["required_coverage"],
        "review_count": result["mapping"]["review_count"],
        "unmapped_count": result["mapping"]["unmapped_count"],
        "unit_risk_count": result["mapping"]["unit_risk_count"],
        "file_status": result["data_decision"]["status"],
        "passed": passed,
        "notes": notes,
    }


def run_matrix(seeds: list[int]) -> tuple[list[dict], dict]:
    repository = ScenarioRepository()
    agent = StandardizationAgent(repository)
    model = CharNGramCentroidModel.load(MODEL)
    cases = []
    field_rows = []
    templates = repository.list()

    for seed in seeds:
        rng = random.Random(seed)
        for template in templates:
            for field in template.fields:
                for _ in range(3):
                    field_rows.append({"text": challenge_name(field, rng), "scenario_id": template.scenario_id, "standard_name": field.standard_name, "relevance": "required" if field.required else "useful"})
            for text in rng.sample(IRRELEVANT, 12):
                field_rows.append({"text": f"{rng.choice(VENDORS)}_{compact(text)}_{rng.randint(10,99)}", "scenario_id": template.scenario_id, "standard_name": "__irrelevant__", "relevance": "irrelevant"})

            frame, expected = challenged_frame(agent, template, rng)
            result = agent.standardize(frame, scenario_id="auto")
            accuracy = mapping_accuracy(result, expected)
            passed = result["scenario"]["scenario_id"] == template.scenario_id and accuracy >= 0.95 and result["mapping"]["required_coverage"] == 1.0 and result["data_decision"]["status"] == "ready"
            cases.append(case(seed, "vendor_noise", template, result, expected, passed))

            flooded = frame.copy()
            for index, text in enumerate(IRRELEVANT):
                flooded[f"{rng.choice(VENDORS)}_{compact(text)}_{seed % 100}_{index}"] = index
            result = agent.standardize(flooded, scenario_id="auto")
            accuracy = mapping_accuracy(result, expected)
            passed = result["scenario"]["scenario_id"] == template.scenario_id and accuracy >= 0.95 and result["mapping"]["required_coverage"] == 1.0 and result["data_decision"]["status"] == "ready"
            cases.append(case(seed, "irrelevant_flood", template, result, expected, passed, "加入20个无关字段"))

            required_names = {field.standard_name for field in template.fields if field.required}
            drop_columns = [raw for raw, standard in expected.items() if standard in required_names][:2]
            incomplete = frame.drop(columns=drop_columns)
            incomplete_expected = {raw: standard for raw, standard in expected.items() if raw not in drop_columns}
            result = agent.standardize(incomplete, scenario_id="auto")
            passed = result["mapping"]["required_coverage"] < 1.0 and result["data_decision"]["status"] != "ready"
            cases.append(case(seed, "missing_required", template, result, incomplete_expected, passed, "删除2个必需字段"))

            corrupted = frame.copy()
            numeric_required = next((field for field in template.fields if field.required and field.data_type in {"float", "integer"} and field.standard_name in expected.values()), None)
            if numeric_required:
                raw = next(raw for raw, standard in expected.items() if standard == numeric_required.standard_name)
                corrupted[raw] = corrupted[raw].astype(object)
                corrupted.loc[corrupted.index[:3], raw] = "bad-value"
                result = agent.standardize(corrupted, scenario_id="auto")
                type_errors = sum(item["type_errors"] for item in result["validation"])
                passed = type_errors >= 3 and result["data_decision"]["status"] == "review"
                cases.append(case(seed, "type_corruption", template, result, expected, passed, "注入3个不可解析数值"))

            conflict = frame.copy()
            unit_field = next((field for field in template.fields if field.required and field.unit not in {"datetime", "rpm"} and field.standard_name in expected.values()), None)
            if unit_field:
                raw = next(raw for raw, standard in expected.items() if standard == unit_field.standard_name)
                conflict = conflict.rename(columns={raw: f"{unit_field.display_name}[rpm]"})
                conflict_expected = {new_raw: standard for new_raw, standard in expected.items()}
                conflict_expected[f"{unit_field.display_name}[rpm]"] = conflict_expected.pop(raw)
                result = agent.standardize(conflict, scenario_id="auto")
                passed = result["mapping"]["unit_risk_count"] >= 1 and result["data_decision"]["status"] != "ready"
                cases.append(case(seed, "unit_conflict", template, result, conflict_expected, passed, f"{unit_field.standard_name}伪装为rpm"))

            wrong = templates[(templates.index(template) + 1) % len(templates)]
            result = agent.standardize(frame, scenario_id=wrong.scenario_id)
            passed = result["mapping"]["required_coverage"] < 1.0 and result["data_decision"]["status"] != "ready"
            cases.append(case(seed, "forced_wrong_scenario", template, result, expected, passed, f"强制使用{wrong.scenario_id}"))

        left, right = rng.sample(templates, 2)
        left_frame, left_expected = challenged_frame(agent, left, rng, rows=80)
        right_frame, right_expected = challenged_frame(agent, right, rng, rows=80)
        mixed = pd.concat([left_frame.reset_index(drop=True), right_frame.reset_index(drop=True)], axis=1)
        result = agent.standardize(mixed, scenario_id="auto")
        passed = result["detection"]["is_ambiguous"] and result["data_decision"]["status"] != "ready"
        cases.append(case(seed, "mixed_scenarios", left, result, {**left_expected, **right_expected}, passed, f"混合{left.scenario_id}+{right.scenario_id}"))

        irrelevant_frame = pd.DataFrame({f"{rng.choice(VENDORS)}_{compact(text)}_{index}": [index] * 60 for index, text in enumerate(IRRELEVANT)})
        result = agent.standardize(irrelevant_frame, scenario_id="auto")
        passed = result["data_decision"]["status"] == "reject" and result["mapping"]["required_coverage"] == 0.0
        cases.append(case(seed, "irrelevant_only_file", None, result, {}, passed, "文件仅含20个无关字段"))

    field_metrics = evaluate(model, field_rows)
    return cases, field_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="A14 Agent 多种子、多场景、多角度压力测试")
    parser.add_argument("--seed-start", type=int, default=20261001)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    started = time.perf_counter()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    cases, field_metrics = run_matrix(seeds)
    angles = sorted({item["angle"] for item in cases})
    angle_summary = {}
    for angle in angles:
        subset = [item for item in cases if item["angle"] == angle]
        angle_summary[angle] = {"cases": len(subset), "passed": sum(item["passed"] for item in subset), "pass_rate": round(sum(item["passed"] for item in subset) / len(subset), 4)}
    failed = [item for item in cases if not item["passed"]]
    passed = not failed and field_metrics["top1_accuracy"] >= 0.95 and field_metrics["relevant_accept_recall"] >= 0.90 and field_metrics["irrelevant_false_accept_rate"] <= 0.02
    report = {
        "passed": passed,
        "seed_start": args.seed_start,
        "seed_count": args.seeds,
        "scenario_count": 5,
        "case_count": len(cases),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "field_semantic": field_metrics,
        "angle_summary": angle_summary,
        "failed_cases": failed,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    columns = ["seed", "angle", "expected_scenario", "detected_scenario", "field_accuracy", "required_coverage", "review_count", "unmapped_count", "unit_risk_count", "file_status", "passed", "notes"]
    with (args.output / "case_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(cases)
    (args.output / "multi_angle_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
