from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import pandas as pd


class ArtifactType:
    SOURCE_DATA = "SOURCE_DATA"
    STANDARDIZED_DATA = "STANDARDIZED_DATA"
    CLEANED_TRAIN = "CLEANED_TRAIN"
    CLEANED_VALIDATION = "CLEANED_VALIDATION"
    CLEANED_TEST = "CLEANED_TEST"
    FROZEN_SPLIT = "FROZEN_SPLIT"
    FIELD_DICTIONARY = "FIELD_DICTIONARY"
    SEGMENTATION_REPORT = "SEGMENTATION_REPORT"
    SELECTED_SEGMENTS = "SELECTED_SEGMENTS"
    SEGMENT_SCORES = "SEGMENT_SCORES"
    SNR_ESTIMATES = "SNR_ESTIMATES"
    MODELING_DATASET = "MODELING_DATASET"
    MODEL_ARTIFACT = "MODEL_ARTIFACT"
    MODEL_METRICS = "MODEL_METRICS"
    TIME_DELAY_ESTIMATES = "TIME_DELAY_ESTIMATES"
    DELAY_COMPENSATED_DATA = "DELAY_COMPENSATED_DATA"
    MODEL_DIAGNOSTICS = "MODEL_DIAGNOSTICS"
    OPTIMIZATION_REPORT = "OPTIMIZATION_REPORT"
    OPTIMIZATION_WINNER = "OPTIMIZATION_WINNER"


LEGACY_ARTIFACT_TYPES = {
    "source_csv": ArtifactType.SOURCE_DATA, "standardized_csv": ArtifactType.STANDARDIZED_DATA,
    "train_csv": ArtifactType.CLEANED_TRAIN, "validation_csv": ArtifactType.CLEANED_VALIDATION,
    "test_csv": ArtifactType.CLEANED_TEST, "split_json": ArtifactType.FROZEN_SPLIT,
    "field_dictionary_json": ArtifactType.FIELD_DICTIONARY,
    "segmentation_report_json": ArtifactType.SEGMENTATION_REPORT,
    "segments_csv": ArtifactType.SELECTED_SEGMENTS, "segment_scores_csv": ArtifactType.SEGMENT_SCORES,
    "snr_csv": ArtifactType.SNR_ESTIMATES, "modeling_csv": ArtifactType.MODELING_DATASET,
    "summary_json": ArtifactType.MODEL_ARTIFACT, "metrics_json": ArtifactType.MODEL_METRICS,
    "delays_csv": ArtifactType.TIME_DELAY_ESTIMATES,
    "delay_compensated_csv": ArtifactType.DELAY_COMPENSATED_DATA,
    "diagnostics_json": ArtifactType.MODEL_DIAGNOSTICS,
    "optimization_json": ArtifactType.OPTIMIZATION_REPORT,
    "optimization_winner_json": ArtifactType.OPTIMIZATION_WINNER,
}
TYPE_TO_LEGACY = {value: key for key, value in LEGACY_ARTIFACT_TYPES.items()}
LEGACY_LAYOUT_PATHS = {
    ArtifactType.CLEANED_TRAIN: "03_cleaning/train.csv",
    ArtifactType.CLEANED_VALIDATION: "03_cleaning/validation.csv",
    ArtifactType.CLEANED_TEST: "03_cleaning/test.csv",
    ArtifactType.FROZEN_SPLIT: "03_cleaning/split_manifest.json",
    ArtifactType.FIELD_DICTIONARY: "02_standardization/field_dictionary.json",
    ArtifactType.SEGMENTATION_REPORT: "03_cleaning/segmentation_report.json",
    ArtifactType.SELECTED_SEGMENTS: "03_cleaning/selected_dynamic_segments.csv",
    ArtifactType.SEGMENT_SCORES: "03_cleaning/segment_scores.csv",
    ArtifactType.SNR_ESTIMATES: "03_cleaning/snr_estimates.csv",
    ArtifactType.MODELING_DATASET: "03_cleaning/modeling_dataset.csv",
    ArtifactType.TIME_DELAY_ESTIMATES: "04_modeling/01_time_delay/delay_estimates.csv",
    ArtifactType.MODEL_DIAGNOSTICS: "04_modeling/03_system_identification/diagnostics.json",
}


EXECUTOR_ARTIFACT_CONTRACTS: dict[str, dict[str, tuple[str, ...]]] = {
    "standardization": {"requires": (ArtifactType.SOURCE_DATA,), "produces": (ArtifactType.STANDARDIZED_DATA, ArtifactType.FIELD_DICTIONARY)},
    "cleaning": {"requires": (ArtifactType.STANDARDIZED_DATA, ArtifactType.FIELD_DICTIONARY), "produces": (
        ArtifactType.CLEANED_TRAIN, ArtifactType.CLEANED_VALIDATION, ArtifactType.CLEANED_TEST,
        ArtifactType.FROZEN_SPLIT, ArtifactType.MODELING_DATASET)},
    "segmentation": {"requires": (ArtifactType.CLEANED_TRAIN, ArtifactType.FROZEN_SPLIT, ArtifactType.FIELD_DICTIONARY), "produces": (
        ArtifactType.SEGMENTATION_REPORT, ArtifactType.SELECTED_SEGMENTS, ArtifactType.SEGMENT_SCORES,
        ArtifactType.SNR_ESTIMATES, ArtifactType.MODELING_DATASET)},
    "modeling": {"requires": (ArtifactType.MODELING_DATASET, ArtifactType.CLEANED_VALIDATION, ArtifactType.CLEANED_TEST,
                                ArtifactType.FROZEN_SPLIT, ArtifactType.FIELD_DICTIONARY),
                 "produces": (ArtifactType.MODEL_ARTIFACT, ArtifactType.MODEL_METRICS)},
    "optimization": {"requires": (ArtifactType.MODEL_ARTIFACT, ArtifactType.CLEANED_TRAIN,
                                    ArtifactType.CLEANED_VALIDATION, ArtifactType.CLEANED_TEST,
                                    ArtifactType.FROZEN_SPLIT, ArtifactType.SELECTED_SEGMENTS,
                                    ArtifactType.FIELD_DICTIONARY),
                     "produces": (ArtifactType.OPTIMIZATION_REPORT, ArtifactType.OPTIMIZATION_WINNER)},
    "review": {"requires": (ArtifactType.MODEL_METRICS,), "produces": ()},
    "report": {"requires": (), "produces": ()},
}
EXECUTOR_INPUT_CONTRACTS = {
    "optimization": ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data"),
}


def canonical_artifact_type(value: str) -> str:
    return LEGACY_ARTIFACT_TYPES.get(str(value), str(value).upper())


def canonical_artifact_types(values: Iterable[str]) -> set[str]:
    return {canonical_artifact_type(value) for value in values}


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


@dataclass(frozen=True)
class RuntimeArtifactRef:
    artifact_id: str
    artifact_type: str
    producer: str
    run_id: str
    stage: str
    path: str
    version: str = "1"
    schema_version: str = "runtime-artifact-v1"
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    source_execution_id: str | None = None

    @property
    def skill_id(self) -> str:
        return self.producer

    def public(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeArtifactResolver:
    """Sole adapter between legacy snapshot paths and typed runtime artifacts."""

    def __init__(self, snapshot: dict[str, Any], state: dict[str, Any] | None = None):
        self.snapshot = snapshot
        self.state = state if state is not None else {}

    def _state_refs(self) -> dict[str, RuntimeArtifactRef]:
        return self.state.setdefault("artifact_refs", {})

    def available_types(self) -> set[str]:
        candidates = canonical_artifact_types(self.snapshot.get("artifacts", {}).keys())
        candidates.update(canonical_artifact_types(self._state_refs().keys()))
        candidates.update(canonical_artifact_type(row["artifact_type"])
                          for row in self.snapshot.get("artifact_registry", []) or []
                          if isinstance(row, dict) and row.get("artifact_type"))
        candidates.update(LEGACY_LAYOUT_PATHS)
        available = {artifact_type for artifact_type in candidates if self.resolve(artifact_type) is not None}
        if self.snapshot.get("results", {}).get("standardization", {}).get("dictionary"):
            available.add(ArtifactType.FIELD_DICTIONARY)
        if self.snapshot.get("_dataframe") is not None:
            available.add(ArtifactType.SOURCE_DATA)
        return available

    def readiness(self, required: Iterable[str]) -> dict[str, Any]:
        required_types = tuple(canonical_artifact_type(item) for item in required)
        available = self.available_types()
        checks = {item: item in available for item in required_types}
        missing = [item for item, present in checks.items() if not present]
        return {"required_artifacts": checks, "missing_artifacts": missing,
                "artifact_readiness_score": round(sum(checks.values()) / len(checks), 3) if checks else 1.0}

    def resolve(self, artifact_type: str, producer: str = "pipeline", version: str | None = None) -> RuntimeArtifactRef | None:
        canonical = canonical_artifact_type(artifact_type)
        state_ref = self._state_refs().get(canonical) or self._state_refs().get(artifact_type)
        if isinstance(state_ref, dict):
            state_ref = RuntimeArtifactRef(**state_ref)
        if (isinstance(state_ref, RuntimeArtifactRef) and Path(state_ref.path).is_file()
                and (version is None or state_ref.version == version)):
            return state_ref
        for row in self.snapshot.get("artifact_registry", []) or []:
            if isinstance(row, dict) and canonical_artifact_type(row.get("artifact_type", "")) == canonical:
                ref = RuntimeArtifactRef(**row)
                if Path(ref.path).is_file() and (version is None or ref.version == version):
                    return ref
        legacy_key = TYPE_TO_LEGACY.get(canonical, artifact_type)
        run_id = str(self.snapshot.get("run_id") or "")
        if not run_id:
            return None
        path = None
        if legacy_key in self.snapshot.get("artifacts", {}):
            try:
                from core.services.pipeline import resolve_artifact
                path, _ = resolve_artifact(run_id, legacy_key)
            except Exception:
                path = None
        if path is None:
            relative = LEGACY_LAYOUT_PATHS.get(canonical)
            if not relative:
                return None
            try:
                from core.services.pipeline import RUNS_DIR
                path = (Path(RUNS_DIR) / run_id / relative).resolve()
            except Exception:
                return None
            if not path.is_file():
                return None
        return RuntimeArtifactRef(
            artifact_id=f"{run_id}:{canonical}", artifact_type=canonical, producer=producer,
            run_id=run_id, stage=producer, path=str(path), version=version or "1",
            content_hash=_sha256(path), created_at=self.snapshot.get("updated_at") or self.snapshot.get("created_at"),
            source_execution_id=run_id, metadata={"legacy_key": legacy_key})

    def register(self, artifact_type: str, path: str | Path, producer: str, source_execution_id: str,
                 *, stage: str | None = None, version: str = "1", schema_version: str = "runtime-artifact-v1",
                 metadata: dict[str, Any] | None = None) -> RuntimeArtifactRef:
        canonical = canonical_artifact_type(artifact_type)
        artifact_path = Path(path).resolve()
        ref = RuntimeArtifactRef(
            artifact_id=f"artifact_{uuid4().hex[:16]}", artifact_type=canonical, producer=producer,
            run_id=str(self.snapshot.get("run_id") or source_execution_id), stage=stage or producer,
            path=str(artifact_path), version=version, schema_version=schema_version,
            content_hash=_sha256(artifact_path), metadata=metadata or {},
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"), source_execution_id=source_execution_id)
        self._state_refs()[canonical] = ref
        return ref

    def write_json(self, artifact_type: str, payload: Any, output: str | Path, producer: str,
                   source_execution_id: str, **kwargs) -> RuntimeArtifactRef:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return self.register(artifact_type, path, producer, source_execution_id, **kwargs)

    def write_frame(self, artifact_type: str, frame: pd.DataFrame, output: str | Path, producer: str,
                    source_execution_id: str, **kwargs) -> RuntimeArtifactRef:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.reset_index().to_csv(path, index=False, encoding="utf-8-sig")
        return self.register(artifact_type, path, producer, source_execution_id, **kwargs)

    def load_json(self, artifact_type: str) -> Any:
        ref = self.resolve(artifact_type)
        if ref:
            payload = json.loads(Path(ref.path).read_text(encoding="utf-8"))
            if canonical_artifact_type(artifact_type) == ArtifactType.FIELD_DICTIONARY and isinstance(payload, dict):
                return payload.get("fields", payload)
            return payload
        if canonical_artifact_type(artifact_type) == ArtifactType.FIELD_DICTIONARY:
            return self.snapshot.get("results", {}).get("standardization", {}).get("dictionary")
        return None

    def load_frame(self, artifact_type: str) -> pd.DataFrame | None:
        ref = self.resolve(artifact_type)
        if not ref:
            return None
        data = pd.read_csv(ref.path)
        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(data["timestamp"], errors="raise")
            data = data.set_index("timestamp")
        return data

    def compatibility_workspace(self, output_dir: str | Path, artifact_types: Iterable[str],
                                fallback_frames: dict[str, pd.DataFrame] | None = None,
                                fallback_json: dict[str, Any] | None = None) -> Path:
        """Materialize legacy service layout here, never in individual Executors."""
        root = Path(output_dir)
        clean_dir = root / "03_cleaning"
        clean_dir.mkdir(parents=True, exist_ok=True)
        names = {ArtifactType.CLEANED_TRAIN: "train.csv", ArtifactType.CLEANED_VALIDATION: "validation.csv",
                 ArtifactType.CLEANED_TEST: "test.csv", ArtifactType.FROZEN_SPLIT: "split_manifest.json",
                 ArtifactType.MODELING_DATASET: "modeling_dataset.csv"}
        for artifact_type in artifact_types:
            canonical = canonical_artifact_type(artifact_type)
            ref = self.resolve(canonical)
            if ref and canonical in names:
                destination = clean_dir / names[canonical]
                if Path(ref.path).resolve() != destination.resolve():
                    shutil.copy2(ref.path, destination)
            elif canonical in names and canonical in (fallback_frames or {}):
                (fallback_frames or {})[canonical].reset_index().to_csv(clean_dir / names[canonical], index=False, encoding="utf-8-sig")
            elif canonical in names and canonical in (fallback_json or {}):
                (clean_dir / names[canonical]).write_text(json.dumps((fallback_json or {})[canonical], ensure_ascii=False, indent=2), encoding="utf-8")
        return root


def snapshot_artifact_registry(snapshot: dict[str, Any], run_dir: str | Path | None = None) -> list[dict[str, Any]]:
    resolver = RuntimeArtifactResolver(snapshot)
    rows = []
    for legacy_key, relative in snapshot.get("artifacts", {}).items():
        ref = None
        if run_dir is not None:
            path = (Path(run_dir) / relative).resolve()
            if path.is_file():
                ref = RuntimeArtifactRef(
                    artifact_id=f"{snapshot.get('run_id')}:{canonical_artifact_type(legacy_key)}",
                    artifact_type=canonical_artifact_type(legacy_key), producer="pipeline",
                    run_id=str(snapshot.get("run_id") or ""), stage="pipeline", path=str(path),
                    content_hash=_sha256(path), metadata={"legacy_key": legacy_key},
                    created_at=snapshot.get("updated_at") or snapshot.get("created_at"),
                    source_execution_id=str(snapshot.get("run_id") or ""))
        if ref is None:
            ref = resolver.resolve(legacy_key)
        if ref:
            rows.append(ref.public())
    return rows
