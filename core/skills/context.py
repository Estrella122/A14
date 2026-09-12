from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DataContext:
    run_id: str | None = None
    project_context_scene: str | None = None
    detected_scene: str | None = None
    scene_confidence: float | None = None
    scene_status: str | None = None
    standardized_fields: list[dict[str, Any]] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)
    mapping_confidence: float | None = None
    numeric_field_count: int = 0
    sample_count: int = 0
    timestamp: str | None = None
    ordered_data: bool = False
    regular_time_axis: bool = False
    missing_rate: Any = None
    anomaly_rate: Any = None
    data_quality: Any = None
    equipment_context: dict[str, Any] = field(default_factory=dict)
    process_context: dict[str, Any] = field(default_factory=dict)
    available_artifacts: list[str] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return asdict(self)


def build_data_context(snapshot: dict[str, Any] | None, run_id: str | None = None) -> DataContext:
    if not snapshot:
        return DataContext(run_id=run_id)
    results = snapshot.get("results", {})
    standard = results.get("standardization", {})
    scenario = standard.get("scenario", {})
    mapping = standard.get("mapping", {})
    cleaning = results.get("cleaning", {})
    rows = mapping.get("mappings", [])
    fields = []
    confidences = []
    semantic_types = set()
    numeric_count = 0
    timestamp = None
    for row in rows:
        if row.get("status") not in {"matched", "review"} or not row.get("standard"):
            continue
        field_info = {
            "name": row.get("standard"),
            "raw": row.get("raw"),
            "role": row.get("role"),
            "data_type": row.get("data_type"),
            "semantic_type": row.get("point_resolution", {}).get("measurement_type") or row.get("role"),
            "mapping_confidence": row.get("confidence"),
        }
        fields.append(field_info)
        semantic_types.update(filter(None, (field_info["semantic_type"], field_info["role"])))
        if field_info["data_type"] in {"float", "integer", "number", "int"}:
            numeric_count += 1
        if field_info["data_type"] == "datetime" or field_info["name"] == "timestamp":
            timestamp = field_info["name"]
        if isinstance(row.get("confidence"), (int, float)):
            confidences.append(float(row["confidence"]))
    root_trace = snapshot.get("runtime_trace") or {}
    standard_trace = standard.get("runtime_trace") or {}
    trace = {**standard_trace, **root_trace}
    time_axis_type = scenario.get("time_axis_type")
    sample_count = int(standard.get("source_row_count") or cleaning.get("cleaned_row_count") or 0)
    quality = cleaning.get("overall_score")
    if quality is None:
        quality = standard.get("data_decision", {}).get("status")
    equipment = {key: scenario.get(key) for key in ("industry", "process_unit") if scenario.get(key)}
    process = {key: scenario.get(key) for key in ("primary_output", "model_outputs", "sampling_seconds") if scenario.get(key) is not None}
    return DataContext(
        run_id=snapshot.get("run_id") or run_id,
        project_context_scene=snapshot.get("project_scene"),
        detected_scene=trace.get("final_scene") or trace.get("selected_scene") or trace.get("agent_scene") or trace.get("detected_scene") or scenario.get("scenario_id"),
        scene_confidence=trace.get("scene_confidence", trace.get("confidence")),
        scene_status=trace.get("scene_status", trace.get("status")),
        standardized_fields=fields,
        semantic_types=sorted(semantic_types),
        mapping_confidence=round(sum(confidences) / len(confidences), 3) if confidences else None,
        numeric_field_count=numeric_count,
        sample_count=sample_count,
        timestamp=timestamp,
        ordered_data=bool(timestamp and sample_count),
        regular_time_axis=bool(timestamp and scenario.get("sampling_seconds")),
        missing_rate=cleaning.get("missing_rate"),
        anomaly_rate=cleaning.get("anomaly_rate") or cleaning.get("anomaly_rates"),
        data_quality=quality,
        equipment_context=equipment,
        process_context=process,
        available_artifacts=sorted(set(snapshot.get("artifacts", {}).keys()) | {key for key, value in results.items() if value}),
    )
