from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .artifacts import ArtifactType


EXECUTION_STATES = frozenset({"executed", "evidence_only", "blocked", "skipped", "failed"})


@dataclass(frozen=True)
class SkillContract:
    skill_id: str
    skill_type: str
    executor: str
    capability: str
    execution_mode: str
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    quality_gates: tuple[str, ...] = ()
    version: str = "1.0.0"

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _c(skill_id, skill_type, executor, capability, execution_mode, requires=(), produces=(), gates=()):
    return SkillContract(skill_id, skill_type, executor, capability, execution_mode,
                         tuple(requires), tuple(produces), tuple(gates))


SKILL_CONTRACTS = {
    row.skill_id: row for row in (
        _c("industrial_intent_parser", "orchestration", "task_understanding", "parse_industrial_intent", "orchestrate", gates=("objective_present", "execution_mode_resolved")),
        _c("equipment_entity_resolver", "orchestration", "task_understanding", "resolve_equipment_entity", "orchestrate", gates=("scene_consistency",)),
        _c("constraint_parameter_extractor", "orchestration", "task_understanding", "extract_constraints", "orchestrate", gates=("parameter_bounds",)),
        _c("skill_capability_matcher", "orchestration", "routing", "match_skill_capabilities", "orchestrate", gates=("negation_preserved", "unknown_rejection")),
        _c("workflow_dag_planner", "orchestration", "planning", "build_execution_dag", "orchestrate", gates=("acyclic_dependencies", "artifact_readiness")),
        _c("execution_supervisor_replanner", "orchestration", "supervision", "inspect_and_replan", "compute", gates=("failed_targets_identified", "bounded_retry")),

        _c("csv_asset_manager", "artifact", "asset", "register_csv_asset", "evidence", requires=(ArtifactType.SOURCE_DATA,), gates=("shape_limits", "content_hash")),
        _c("industrial_simulation_generator", "compute", "simulation", "generate_industrial_simulation", "compute", produces=(ArtifactType.SOURCE_DATA,), gates=("synthetic_label", "fixed_seed")),
        _c("dataset_scenario_profiler", "compute", "standardization", "profile_dataset_scene", "compute", requires=(ArtifactType.SOURCE_DATA,), produces=(ArtifactType.FIELD_DICTIONARY,), gates=("scene_confidence", "unknown_scene_rejection")),
        _c("semantic_field_unit_standardizer", "compute", "standardization", "standardize_fields_and_units", "compute", requires=(ArtifactType.SOURCE_DATA,), produces=(ArtifactType.STANDARDIZED_DATA, ArtifactType.FIELD_DICTIONARY), gates=("unit_compatibility", "mapping_coverage")),
        _c("time_axis_alignment_resampler", "compute", "cleaning", "align_and_resample_time_axis", "compute", requires=(ArtifactType.STANDARDIZED_DATA, ArtifactType.FIELD_DICTIONARY), produces=(ArtifactType.CLEANED_TRAIN, ArtifactType.CLEANED_VALIDATION, ArtifactType.CLEANED_TEST, ArtifactType.FROZEN_SPLIT), gates=("monotonic_time", "causal_partitioning")),
        _c("missing_anomaly_cleaner", "compute", "cleaning", "clean_missing_and_anomalies", "compute", requires=(ArtifactType.STANDARDIZED_DATA, ArtifactType.FIELD_DICTIONARY), produces=(ArtifactType.CLEANED_TRAIN, ArtifactType.CLEANED_VALIDATION, ArtifactType.CLEANED_TEST), gates=("no_future_fill", "target_missing_preserved")),

        _c("steady_transient_state_detector", "compute", "segmentation", "detect_operating_states", "compute", requires=(ArtifactType.CLEANED_TRAIN, ArtifactType.FROZEN_SPLIT), produces=(ArtifactType.SEGMENTATION_REPORT,), gates=("training_partition_only",)),
        _c("signal_noise_ratio_estimator", "compute", "segmentation", "estimate_signal_noise_ratio", "compute", requires=(ArtifactType.CLEANED_TRAIN,), produces=(ArtifactType.SNR_ESTIMATES,), gates=("estimator_method_recorded",)),
        _c("high_snr_dynamic_segment_extractor", "compute", "segmentation", "extract_high_snr_segments", "compute", requires=(ArtifactType.CLEANED_TRAIN, ArtifactType.SNR_ESTIMATES), produces=(ArtifactType.SELECTED_SEGMENTS,), gates=("training_partition_only", "minimum_valid_samples")),
        _c("segment_quality_scorer_ranker", "compute", "segmentation", "score_and_rank_segments", "compute", requires=(ArtifactType.SELECTED_SEGMENTS,), produces=(ArtifactType.SEGMENT_SCORES, ArtifactType.MODELING_DATASET), gates=("score_components_available",)),
        _c("time_delay_estimator_compensator", "compute", "industrial-analysis", "estimate_and_compensate_delay", "compute", requires=(ArtifactType.STANDARDIZED_DATA,), gates=("causal_delay", "maximum_lag_bound")),
        _c("collinearity_detector_reducer", "compute", "industrial-analysis", "diagnose_and_reduce_collinearity", "compute", requires=(ArtifactType.STANDARDIZED_DATA,), gates=("vif_or_correlation_evidence",)),

        _c("modeling_dataset_assembler", "compute", "modeling", "assemble_modeling_dataset", "compute", requires=(ArtifactType.CLEANED_TRAIN, ArtifactType.FROZEN_SPLIT), produces=(ArtifactType.MODELING_DATASET,), gates=("split_hash", "no_test_tuning")),
        _c("arx_structure_order_selector", "compute", "modeling", "select_arx_structure_order", "compute", requires=(ArtifactType.MODELING_DATASET, ArtifactType.CLEANED_VALIDATION), produces=(ArtifactType.MODEL_ARTIFACT,), gates=("common_validation_targets", "candidate_table")),
        _c("system_identification_trainer", "compute", "modeling", "train_system_identification_model", "compute", requires=(ArtifactType.MODELING_DATASET, ArtifactType.FIELD_DICTIONARY), produces=(ArtifactType.MODEL_ARTIFACT,), gates=("external_inputs_declared", "reproducible_fit")),
        _c("multi_model_benchmark", "compute", "modeling", "benchmark_candidate_models", "compute", requires=(ArtifactType.MODEL_ARTIFACT, ArtifactType.CLEANED_VALIDATION), produces=(ArtifactType.MODEL_METRICS,), gates=("uniform_split", "baseline_comparison")),
        _c("model_diagnostics_evaluator", "compute", "modeling", "evaluate_model_diagnostics", "compute", requires=(ArtifactType.MODEL_ARTIFACT, ArtifactType.CLEANED_TEST), produces=(ArtifactType.MODEL_METRICS,), gates=("single_final_test", "residual_diagnostics")),
        _c("closed_loop_preprocessing_optimizer", "compute", "optimization", "optimize_preprocessing_closed_loop", "compute", requires=(ArtifactType.MODEL_ARTIFACT, ArtifactType.CLEANED_TRAIN, ArtifactType.CLEANED_VALIDATION, ArtifactType.FROZEN_SPLIT, ArtifactType.SELECTED_SEGMENTS), produces=(ArtifactType.OPTIMIZATION_REPORT, ArtifactType.OPTIMIZATION_WINNER), gates=("real_data_only", "test_not_in_objective")),

        _c("engineering_result_interpreter", "evidence", "review", "interpret_engineering_results", "evidence", requires=(ArtifactType.MODEL_METRICS,), gates=("evidence_citations", "deployment_claim_guard")),
        _c("engineering_visualization_builder", "artifact", "visualization", "build_engineering_visualization", "compute", requires=(ArtifactType.MODEL_METRICS,), gates=("real_series_only",)),
        _c("expert_report_writer", "artifact", "report", "write_expert_report", "compute", gates=("limitations_included", "evidence_links")),
        _c("final_artifact_exporter", "artifact", "artifact", "export_existing_artifacts", "evidence", gates=("artifact_exists", "content_hash")),
        _c("experiment_tracker_comparator", "evidence", "experiment", "compare_registered_experiments", "compute", requires=(ArtifactType.MODEL_METRICS,), gates=("comparable_split", "registered_runs_only")),
        _c("evidence_audit_reproducer", "evidence", "audit", "audit_and_reproduce_evidence", "evidence", gates=("provenance_complete", "content_hash")),
    )
}


def get_skill_contract(skill_id: str) -> SkillContract | None:
    return SKILL_CONTRACTS.get(skill_id)


def execution_state_for(*, status: str, invoked: bool = False, evidence_read: bool = False) -> str:
    if status == "blocked" or status == "unavailable":
        return "blocked"
    if status == "failed":
        return "failed"
    if status == "skipped":
        return "skipped"
    if invoked and status in {"success", "partial", "completed"}:
        return "executed"
    if evidence_read:
        return "evidence_only"
    return "skipped"
