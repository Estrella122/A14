from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from cleanlab.filter import find_label_issues
from mapie.classification import SplitConformalClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder

from standard_agent.ml_model import semantic_core
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training_data" / "field_semantics_all.csv"
DEFAULT_OUTPUT = ROOT / "models" / "training_data_audit.json"


def read_rows() -> list[dict[str, str]]:
    with DATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def calibration_error(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    predictions = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    correct = predictions == labels
    error = 0.0
    for lower in np.linspace(0.0, 1.0, bins, endpoint=False):
        upper = lower + 1.0 / bins
        mask = (confidence >= lower) & (confidence < upper if upper < 1.0 else confidence <= upper)
        if mask.any():
            error += float(mask.mean()) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return round(error, 4)


def audit(output: Path = DEFAULT_OUTPUT) -> dict:
    rows = read_rows()
    scenarios = sorted({row["scenario_id"] for row in rows})
    suspected = []
    audit_summaries = []
    total_suspected = 0
    total_correct = 0
    weighted_calibration = 0.0
    conformal_covered = 0
    conformal_samples = 0
    conformal_set_size = 0
    conformal_point_correct = 0

    for scenario_id in scenarios:
        indexed = [(index, row) for index, row in enumerate(rows) if row["scenario_id"] == scenario_id]
        indices = np.asarray([item[0] for item in indexed])
        scenario_rows = [item[1] for item in indexed]
        texts = np.asarray([row["text"] for row in scenario_rows])
        raw_labels = np.asarray([row["standard_name"] for row in scenario_rows])
        groups = np.asarray([row["group_id"] for row in scenario_rows])
        encoder = LabelEncoder()
        labels = encoder.fit_transform(raw_labels)
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=2, max_features=3000, sublinear_tf=True)
        features = vectorizer.fit_transform(texts)
        classifier = LogisticRegression(max_iter=500, class_weight="balanced", solver="lbfgs")
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20260813)
        probabilities = cross_val_predict(classifier, features, labels, groups=groups, cv=cv, method="predict_proba", n_jobs=-1)
        ranked = find_label_issues(labels=labels, pred_probs=probabilities, return_indices_ranked_by="self_confidence")
        total_suspected += len(ranked)
        correct = int((labels == probabilities.argmax(axis=1)).sum())
        ece = calibration_error(labels, probabilities)
        total_correct += correct
        weighted_calibration += ece * len(scenario_rows)
        audit_summaries.append(
            {
                "scenario_id": scenario_id,
                "samples": len(scenario_rows),
                "labels": len(encoder.classes_),
                "accuracy": round(correct / len(scenario_rows), 4),
                "expected_calibration_error": ece,
                "suspected_label_issues": len(ranked),
            }
        )
        for local_index in ranked:
            predicted = int(probabilities[local_index].argmax())
            suspected.append(
                {
                    "row": int(indices[local_index]),
                    "scenario_id": scenario_id,
                    "text": str(texts[local_index]),
                    "given_label": str(raw_labels[local_index]),
                    "predicted_label": str(encoder.inverse_transform([predicted])[0]),
                    "given_probability": round(float(probabilities[local_index, labels[local_index]]), 4),
                    "predicted_probability": round(float(probabilities[local_index, predicted]), 4),
                    "group_id": str(groups[local_index]),
                }
            )

        split_rows = {split: [row for row in scenario_rows if row["split"] == split] for split in ("train", "validation", "test")}
        conformal_vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=2, max_features=1500, sublinear_tf=True)
        train_x = conformal_vectorizer.fit_transform([row["text"] for row in split_rows["train"]]).toarray()
        validation_x = conformal_vectorizer.transform([row["text"] for row in split_rows["validation"]]).toarray()
        test_x = conformal_vectorizer.transform([row["text"] for row in split_rows["test"]]).toarray()
        conformal = SplitConformalClassifier(
            LogisticRegression(max_iter=500, class_weight="balanced", solver="lbfgs"),
            confidence_level=0.95,
            prefit=False,
            random_state=20260813,
        )
        conformal.fit(train_x, [row["standard_name"] for row in split_rows["train"]])
        conformal.conformalize(validation_x, [row["standard_name"] for row in split_rows["validation"]])
        point_predictions, prediction_sets = conformal.predict_set(test_x)
        classes = conformal._mapie_classifier.classes_
        test_targets = np.asarray([row["standard_name"] for row in split_rows["test"]])
        for index, target in enumerate(test_targets):
            target_index = np.flatnonzero(classes == target)
            conformal_covered += bool(len(target_index) and prediction_sets[index, target_index[0], 0])
        conformal_samples += len(test_targets)
        conformal_set_size += int(prediction_sets[:, :, 0].sum())
        conformal_point_correct += int((point_predictions == test_targets).sum())

    conflicts: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        key = (row["scenario_id"], semantic_core(row["text"]))
        conflicts.setdefault(key, set()).add(row["standard_name"])
    direct_conflicts = [
        {"scenario_id": scenario, "semantic_core": core, "labels": sorted(values)}
        for (scenario, core), values in conflicts.items()
        if core and len(values) > 1
    ]

    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data_file": str(DATA.relative_to(ROOT)),
        "samples": len(rows),
        "labels": len({(row["scenario_id"], row["standard_name"]) for row in rows}),
        "groups": len({row["group_id"] for row in rows}),
        "cross_validated_accuracy": round(total_correct / len(rows), 4),
        "expected_calibration_error": round(weighted_calibration / len(rows), 4),
        "scenario_audits": audit_summaries,
        "cleanlab": {
            "suspected_label_issues": total_suspected,
            "review_queue": sorted(suspected, key=lambda item: item["given_probability"])[:1000],
            "policy": "仅进入审核队列，不自动删除或改标",
        },
        "direct_semantic_conflicts": direct_conflicts,
        "conformal": {
            "engine": "MAPIE SplitConformalClassifier",
            "target_coverage": 0.95,
            "observed_coverage": round(conformal_covered / max(conformal_samples, 1), 4),
            "mean_prediction_set_size": round(conformal_set_size / max(conformal_samples, 1), 4),
            "point_accuracy": round(conformal_point_correct / max(conformal_samples, 1), 4),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="审计 A14 字段语义训练数据")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(audit(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
