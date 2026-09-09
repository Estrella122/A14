from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from standard_agent.ml_model import CharNGramCentroidModel
from standard_agent.semantic_ensemble import EmbeddingPrototypeIndex, HybridSemanticModel, load_embedding_encoder
from training.audit_training_data import audit as audit_training_data


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training_data" / "field_semantics_all.csv"
WEB_DATA = ROOT / "training_data" / "web_research" / "web_alias_training.csv"
MULTI_ANGLE_DATA = ROOT / "training_data" / "multi_angle_training" / "field_semantics_multi_angle.csv"
MODEL = ROOT / "models" / "field_semantic_model.json"
MODEL_INDEX = MODEL.with_suffix(".embedding.npz")
EMBEDDING_ENCODER = ROOT / "models" / "embedding_encoder_multilingual"
REPORT = ROOT / "models" / "training_metrics.json"
PROGRESS = ROOT / "models" / "training_progress.json"
LEARNED_ALIASES = ROOT / "knowledge" / "learned_aliases.json"
VERSIONS = ROOT / "models" / "versions"
REGISTRY = ROOT / "models" / "model_registry.json"


class ProgressReporter:
    def __init__(self, path: Path, ui_delay: float = 0.0) -> None:
        self.path = path
        self.ui_delay = max(ui_delay, 0.0)
        self.run_id = uuid.uuid4().hex[:12]
        self.started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.events: list[dict] = []

    def emit(self, stage: str, progress: int, message: str, status: str = "running", metrics: dict | None = None) -> None:
        event = {
            "stage": stage,
            "progress": progress,
            "message": message,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self.events.append(event)
        payload = {
            "run_id": self.run_id,
            "status": status,
            "stage": stage,
            "progress": progress,
            "message": message,
            "started_at": self.started_at,
            "updated_at": event["time"],
            "events": self.events,
            "metrics": metrics,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        print(f"[{progress:3d}%] {message}", flush=True)
        if self.ui_delay and status == "running":
            time.sleep(self.ui_delay)


def read_rows() -> list[dict[str, str]]:
    with DATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_web_rows() -> list[dict[str, str]]:
    if not WEB_DATA.exists():
        return []
    with WEB_DATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_multi_angle_rows() -> list[dict[str, str]]:
    if not MULTI_ANGLE_DATA.exists():
        return []
    with MULTI_ANGLE_DATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_feedback_rows() -> list[dict[str, str]]:
    if not LEARNED_ALIASES.exists():
        return []
    knowledge = json.loads(LEARNED_ALIASES.read_text(encoding="utf-8"))
    return [
        {
            "text": alias,
            "scenario_id": scenario_id,
            "standard_name": standard_name,
            "source": "human_feedback",
            "split": "external_train",
        }
        for scenario_id, fields in knowledge.items()
        for standard_name, aliases in fields.items()
        for alias in aliases
    ]


def release_gate(candidate: dict, baseline: dict | None) -> dict:
    baseline = baseline or {}
    baseline_test = baseline.get("test", {})
    baseline_cold = baseline.get("cold_start_test", {})
    thresholds = {
        "test_top1_min": max(0.95, float(baseline_test.get("top1_accuracy", 0.0))),
        "cold_start_top1_min": max(0.80, float(baseline_cold.get("top1_accuracy", 0.0))),
        "test_top3_min": max(0.98, float(baseline_test.get("top3_accuracy", baseline_test.get("top1_accuracy", 0.0)))),
        "cold_start_top3_min": max(0.95, float(baseline_cold.get("top3_accuracy", baseline_cold.get("top1_accuracy", 0.0)))),
        "cold_start_recall_min": max(0.90, float(baseline_cold.get("relevant_accept_recall", baseline_cold.get("top1_accuracy", 0.0)))),
        "false_accept_max": min(0.02, float(baseline_test.get("irrelevant_false_accept_rate", 0.02)) + 0.005),
    }
    checks = {
        "test_top1": candidate["test"]["top1_accuracy"] >= thresholds["test_top1_min"],
        "cold_start_top1": candidate["cold_start_test"]["top1_accuracy"] >= thresholds["cold_start_top1_min"],
        "test_top3": candidate["test"].get("top3_accuracy", candidate["test"]["top1_accuracy"]) >= thresholds["test_top3_min"],
        "cold_start_top3": candidate["cold_start_test"].get("top3_accuracy", candidate["cold_start_test"]["top1_accuracy"]) >= thresholds["cold_start_top3_min"],
        "cold_start_recall": candidate["cold_start_test"].get("relevant_accept_recall", candidate["cold_start_test"]["top1_accuracy"]) >= thresholds["cold_start_recall_min"],
        "false_accept": candidate["test"]["irrelevant_false_accept_rate"] <= thresholds["false_accept_max"],
    }
    if "training_data_audit" in candidate:
        checks.update(
            training_data_integrity=not candidate["training_data_audit"]["direct_semantic_conflicts"],
            conformal_coverage=candidate["training_data_audit"]["conformal"]["observed_coverage"] >= 0.90,
        )
    return {"passed": all(checks.values()), "thresholds": thresholds, "checks": checks}


def publish_model(model: HybridSemanticModel, report: dict, run_id: str) -> None:
    version_dir = VERSIONS / run_id
    version_dir.mkdir(parents=True, exist_ok=False)
    version_model = version_dir / MODEL.name
    version_report = version_dir / REPORT.name
    model.save(version_model)
    version_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {"active_version": None, "versions": []}
    if not registry["versions"] and MODEL.exists() and REPORT.exists():
        baseline_report = json.loads(REPORT.read_text(encoding="utf-8"))
        baseline_id = hashlib.sha256(MODEL.read_bytes()).hexdigest()[:12]
        baseline_dir = VERSIONS / baseline_id
        baseline_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MODEL, baseline_dir / MODEL.name)
        if MODEL_INDEX.exists():
            shutil.copy2(MODEL_INDEX, baseline_dir / MODEL_INDEX.name)
        shutil.copy2(REPORT, baseline_dir / REPORT.name)
        registry["versions"].append({
            "version_id": baseline_id,
            "created_at": datetime.fromtimestamp(MODEL.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            "test_top1": baseline_report["test"]["top1_accuracy"],
            "cold_start_top1": baseline_report["cold_start_test"]["top1_accuracy"],
            "false_accept_rate": baseline_report["test"]["irrelevant_false_accept_rate"],
            "feedback_samples": baseline_report.get("feedback_learning", {}).get("training_samples", 0),
        })
    temporary_model = MODEL.with_suffix(".json.tmp")
    temporary_index = MODEL_INDEX.with_suffix(".tmp.npz")
    temporary_report = REPORT.with_suffix(".json.tmp")
    shutil.copy2(version_model, temporary_model)
    version_index = version_model.with_suffix(".embedding.npz")
    if version_index.exists():
        shutil.copy2(version_index, temporary_index)
    shutil.copy2(version_report, temporary_report)
    temporary_model.replace(MODEL)
    if temporary_index.exists():
        temporary_index.replace(MODEL_INDEX)
    elif MODEL_INDEX.exists():
        MODEL_INDEX.unlink()
    temporary_report.replace(REPORT)
    registry["active_version"] = run_id
    registry["versions"].append({
        "version_id": run_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "test_top1": report["test"]["top1_accuracy"],
        "cold_start_top1": report["cold_start_test"]["top1_accuracy"],
        "false_accept_rate": report["test"]["irrelevant_false_accept_rate"],
        "feedback_samples": report["feedback_learning"]["training_samples"],
    })
    temporary_registry = REGISTRY.with_suffix(".json.tmp")
    temporary_registry.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_registry.replace(REGISTRY)


def evaluate(model: Any, rows: list[dict[str, str]], split: str, excluded_sources: set[str] | None = None) -> dict:
    excluded_sources = excluded_sources or set()
    all_rows = [row for row in rows if row["split"] == split and row.get("source") not in excluded_sources]
    subset = [row for row in all_rows if row["standard_name"] != "__irrelevant__"]
    if hasattr(model, "prime"):
        model.prime(row["text"] for row in all_rows)
    correct = 0
    top3 = 0
    scores = []
    for row in subset:
        predictions = model.predict(row["text"], row["scenario_id"], limit=3)
        labels = [item["standard_name"] for item in predictions]
        correct += bool(labels and labels[0] == row["standard_name"])
        top3 += row["standard_name"] in labels
        if predictions:
            scores.append(predictions[0]["score"])
    total = len(subset)
    threshold = float(model.metadata["accept_threshold"])
    relevant_accepted = 0
    for row in subset:
        predictions = model.predict(row["text"], row["scenario_id"], limit=1)
        relevant_accepted += bool(predictions and predictions[0]["standard_name"] != "__irrelevant__" and predictions[0]["score"] >= threshold)
    negatives = [row for row in all_rows if row["standard_name"] == "__irrelevant__"]
    false_accepts = 0
    for row in negatives:
        predictions = model.predict(row["text"], row["scenario_id"], limit=1)
        false_accepts += bool(predictions and predictions[0]["standard_name"] != "__irrelevant__" and predictions[0]["score"] >= threshold)
    return {
        "samples": total,
        "top1_accuracy": round(correct / max(total, 1), 4),
        "top3_accuracy": round(top3 / max(total, 1), 4),
        "mean_top_score": round(sum(scores) / max(len(scores), 1), 4),
        "relevant_accept_recall": round(relevant_accepted / max(total, 1), 4),
        "irrelevant_samples": len(negatives),
        "irrelevant_false_accept_rate": round(false_accepts / max(len(negatives), 1), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 A14 多场景字段语义模型")
    parser.add_argument("--progress-file", type=Path, default=PROGRESS)
    parser.add_argument("--ui-delay", type=float, default=0.0, help="仅用于让网页有时间展示阶段切换")
    args = parser.parse_args()
    reporter = ProgressReporter(args.progress_file, args.ui_delay)
    try:
        reporter.emit("initialize", 3, "初始化训练任务")
        rows = read_rows()
        web_rows = read_web_rows()
        multi_angle_rows = read_multi_angle_rows()
        feedback_rows = read_feedback_rows()
        baseline = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else None
        split_counts = {name: sum(row["split"] == name for row in rows) for name in ("train", "validation", "test")}
        reporter.emit("load_data", 12, f"已加载 {len(rows)} 条基准样本、{len(web_rows)} 条网络审核样本、{len(multi_angle_rows)} 条多角度增强样本和 {len(feedback_rows)} 条人工反馈")
        audit_report = audit_training_data()
        reporter.emit("audit_data", 16, f"训练数据审计完成：直接语义冲突 {len(audit_report['direct_semantic_conflicts'])} 组，保序覆盖 {audit_report['conformal']['observed_coverage'] * 100:.2f}%")
        encoder = load_embedding_encoder(EMBEDDING_ENCODER) if EMBEDDING_ENCODER.exists() else None
        reporter.emit("load_encoder", 18, "已加载本地多语言语义编码器" if encoder else "未配置本地语义编码器，使用可复现字符模型")
        cold_train = [row for row in rows if row["split"] == "train"] + web_rows + multi_angle_rows + feedback_rows
        cold_char_model = CharNGramCentroidModel().fit(cold_train)
        cold_embedding_index = EmbeddingPrototypeIndex.build(cold_train, encoder) if encoder else None
        cold_model = HybridSemanticModel(cold_char_model, cold_embedding_index, EMBEDDING_ENCODER, encoder=encoder)
        cold_start_test = evaluate(cold_model, rows, "test")
        approved_anchors = [row for row in rows if row.get("source") == "template"]
        train_index = {(row["text"], row["scenario_id"], row["standard_name"]): row for row in [*cold_train, *approved_anchors]}
        train = list(train_index.values())
        reporter.emit("prepare", 24, f"已准备 {len(train)} 条运行训练样本，其中网络增强 {len(web_rows)} 条；另完成严格别名冷启动评估")
        char_model = CharNGramCentroidModel().fit(train)
        embedding_index = EmbeddingPrototypeIndex.build(train, encoder) if encoder else None
        model = HybridSemanticModel(char_model, embedding_index, EMBEDDING_ENCODER, encoder=encoder)
        reporter.emit("fit", 52, f"特征构建与模型拟合完成：{model.metadata['features']} 个特征，{model.metadata['labels']} 个标签")
        train_metrics = evaluate(model, rows, "train")
        reporter.emit("evaluate_train", 64, f"训练集 Top-1：{train_metrics['top1_accuracy'] * 100:.2f}%")
        validation_metrics = evaluate(model, rows, "validation", {"template"})
        reporter.emit("evaluate_validation", 76, f"验证集 Top-1：{validation_metrics['top1_accuracy'] * 100:.2f}%")
        test_metrics = evaluate(model, rows, "test", {"template"})
        reporter.emit("evaluate_test", 88, f"测试集 Top-1：{test_metrics['top1_accuracy'] * 100:.2f}%")
        report = {
            "protocol": {
                "test": "已审核别名已知，仅测试未见厂商包装与格式变化",
                "cold_start_test": "原始别名组完全隔离，用于衡量未知工业同义词泛化",
                "direct_group_leakage": 0,
                "external_web_knowledge": "仅加载审核状态为 approved 的来源术语；review 候选不参与训练",
            },
            "web_augmentation": {
                "training_samples": len(web_rows),
                "source_count": len({row.get("source_id") for row in web_rows}),
                "data_file": str(WEB_DATA.relative_to(ROOT)),
            },
            "multi_angle_augmentation": {
                "training_samples": len(multi_angle_rows),
                "angles": sorted({row.get("training_angle", "unknown") for row in multi_angle_rows}),
                "data_file": str(MULTI_ANGLE_DATA.relative_to(ROOT)),
                "isolation": "仅从基准训练分组生成，不读取验证与测试分组",
            },
            "feedback_learning": {
                "training_samples": len(feedback_rows),
                "data_file": str(LEARNED_ALIASES.relative_to(ROOT)),
            },
            "semantic_ensemble": {
                "encoder": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" if encoder else None,
                "char_weight": model.metadata["char_weight"],
                "embedding_weight": model.metadata["embedding_weight"],
                "embedding_prototypes": model.metadata["embedding_prototypes"],
                "policy": "工业字符模型为主，多语言语义仅做候选重排；未通过发布门槛不上线",
            },
            "training_data_audit": audit_report,
            "model": model.metadata,
            "train": train_metrics,
            "validation": validation_metrics,
            "test": test_metrics,
            "cold_start_test": cold_start_test,
        }
        gate = release_gate(report, baseline)
        report["release_gate"] = gate
        report["model_version"] = reporter.run_id
        if not gate["passed"]:
            reporter.emit("release_gate", 100, "候选模型未达发布门槛，已保留现用模型", status="rejected", metrics=report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        reporter.emit("release_gate", 94, "候选模型通过准入门槛")
        publish_model(model, report, reporter.run_id)
        reporter.emit("save", 97, f"模型版本 {reporter.run_id} 已归档并发布")
        reporter.emit("complete", 100, "训练完成，新模型已热加载", status="completed", metrics=report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        reporter.emit("failed", 100, f"训练失败：{exc}", status="failed")
        raise


if __name__ == "__main__":
    main()
