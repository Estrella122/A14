from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .artifacts import RuntimeArtifactResolver


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
    row_count: int = 0
    column_count: int = 0
    numeric_column_count: int = 0
    estimated_memory: int = 0
    estimated_memory_bytes: int = 0
    time_series_length: int = 0
    timestamp: str | None = None
    ordered_data: bool = False
    regular_time_axis: bool = False
    missing_rate: Any = None
    anomaly_rate: Any = None
    data_quality: Any = None
    equipment_context: dict[str, Any] = field(default_factory=dict)
    process_context: dict[str, Any] = field(default_factory=dict)
    available_artifacts: list[str] = field(default_factory=list)
    available_contract_fields: list[str] = field(default_factory=list)
    scene_context: dict[str, Any] = field(default_factory=dict)

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
    resolver = RuntimeArtifactResolver(snapshot)
    optimization_contract = (snapshot.get("runtime_state", {}) or {}).get("optimization_contract") or snapshot.get("optimization_contract") or {}
    def contract_value_present(value: Any) -> bool:
        if value is None or isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict, tuple, set)):
            return bool(value)
        return True
    estimated_memory = sample_count * max(len(rows), 1) * 8
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
        row_count=sample_count,
        column_count=len(rows),
        numeric_column_count=numeric_count,
        estimated_memory=estimated_memory,
        estimated_memory_bytes=estimated_memory,
        time_series_length=sample_count if timestamp else 0,
        timestamp=timestamp,
        ordered_data=bool(timestamp and sample_count),
        regular_time_axis=bool(timestamp and scenario.get("sampling_seconds")),
        missing_rate=cleaning.get("missing_rate"),
        anomaly_rate=cleaning.get("anomaly_rate") or cleaning.get("anomaly_rates"),
        data_quality=quality,
        equipment_context=equipment,
        process_context=process,
        available_artifacts=sorted(resolver.available_types()),
        available_contract_fields=sorted(key for key, value in optimization_contract.items() if contract_value_present(value)),
        scene_context=build_scene_context(snapshot).public(),
    )


@dataclass
class SceneContext:
    scenario_id: str | None = None
    scenario_name: str = ""
    dataset_ref: str | None = None
    timestamp_column: str = "timestamp"
    input_columns: list[str] = field(default_factory=list)
    target_column: str | None = None
    units: dict = field(default_factory=dict)
    sampling_interval: float | None = None
    constraints: dict = field(default_factory=dict)
    default_parameters: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def public(self):
        return asdict(self)


def build_scene_context(snapshot, repository=None):
    """Resolve data roles from the existing Registry, never the UI project scene."""
    from integrations.standardization.standard_agent.repository import ScenarioRepository
    standard = (snapshot or {}).get("results", {}).get("standardization", {})
    scene = standard.get("scenario", {})
    trace = {**standard.get("runtime_trace", {}), **(snapshot or {}).get("runtime_trace", {})}
    scenario_id = trace.get("final_scene") or trace.get("selected_scene") or trace.get("agent_scene") or trace.get("detected_scene") or scene.get("scenario_id")
    config = dict(scene)
    dictionary = standard.get("dictionary", [])
    repository = repository or ScenarioRepository()
    template = next((t for t in repository.list() if t.scenario_id == scenario_id), None)
    if template:
        config = {**template.config, **scene}
        dictionary = [f.as_dict() for f in template.fields]
    roles = config.get("field_roles", {})
    inputs = roles.get("inputs", [f["standard_name"] for f in dictionary if f.get("role") in {"manipulated", "disturbance", "state"}])
    target = roles.get("target") or config.get("primary_output")
    defaults = dict(config.get("default_parameters", {}))
    seconds = config.get("sampling_seconds")
    if seconds:
        defaults.setdefault("resample_seconds", seconds)
    return SceneContext(scenario_id=scenario_id, scenario_name=config.get("scenario_name", ""),
        dataset_ref=(snapshot or {}).get("dataset_ref") or (snapshot or {}).get("run_id"), timestamp_column=roles.get("timestamp", config.get("timestamp_field", "timestamp")),
        input_columns=list(inputs), target_column=target, units={f["standard_name"]: f.get("unit", "") for f in dictionary},
        sampling_interval=seconds, constraints=config.get("constraints", {}), default_parameters=defaults,
        metadata={"algorithm_profile": config.get("algorithm_profile", {}), "family": config.get("family", config.get("industry")), "display": config.get("display", {}),
                  "model_outputs": config.get("model_outputs", [target]), "source": config.get("source"),
                  "skill_overrides": config.get("skill_overrides", {}), "config_source": "ScenarioRepository" if template else "snapshot",
                  "project_context_scene": (snapshot or {}).get("project_scene")})
