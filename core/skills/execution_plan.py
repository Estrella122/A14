from __future__ import annotations

from typing import Any


GROUP_SKILLS = {
    "simulation": ("industrial_simulation_generator",),
    "standardization": ("dataset_scenario_profiler", "semantic_field_unit_standardizer"),
    "cleaning": ("time_axis_alignment_resampler", "missing_anomaly_cleaner"),
    "segmentation": ("steady_transient_state_detector", "signal_noise_ratio_estimator", "high_snr_dynamic_segment_extractor", "segment_quality_scorer_ranker"),
    "modeling": ("modeling_dataset_assembler", "arx_structure_order_selector", "system_identification_trainer", "multi_model_benchmark", "model_diagnostics_evaluator"),
    "optimization": ("closed_loop_preprocessing_optimizer",),
    "review": ("engineering_result_interpreter",),
    "report": ("expert_report_writer",),
    "visualization": ("engineering_visualization_builder",),
    "experiment": ("experiment_tracker_comparator",),
    "supervision": ("execution_supervisor_replanner",),
}
SKILL_GROUP = {skill_id: group for group, skill_ids in GROUP_SKILLS.items() for skill_id in skill_ids}


def build_execution_plan(task_spec: dict[str, Any], direct_skill_ids: list[str]) -> dict[str, Any]:
    """Build the minimal executor DAG. Catalog dependencies remain planning metadata."""
    direct = set(direct_skill_ids)
    response_intents = set(task_spec.get("response_intents") or [])
    requested_outputs = set(task_spec.get("requested_outputs") or [])
    requested_capabilities = set(task_spec.get("requested_capabilities") or [])
    targets = {SKILL_GROUP[item] for item in direct if item in SKILL_GROUP}
    if "standardization" in response_intents:
        targets.add("standardization")
    if "cleaning" in response_intents:
        targets.add("cleaning")
    if "selection" in response_intents:
        targets.add("segmentation")
    if "modeling" in response_intents:
        targets.add("modeling")
    if "optimization" in response_intents:
        targets.add("optimization")
    if "review" in response_intents and "artifact" not in requested_outputs:
        targets.add("review")
    if "artifact" in requested_outputs and ("report" in task_spec.get("objective", "") or "expert_report_writer" in direct):
        targets.add("report")

    # Anomaly detection belongs to industrial-analysis. Lexical recall of the
    # cleaner must not silently turn it into a data mutation request.
    if "ANOMALY_DETECTION" in requested_capabilities and "MISSING_DATA_ANALYSIS" not in requested_capabilities:
        targets.discard("cleaning")
        if direct <= {"missing_anomaly_cleaner"}:
            targets.discard("standardization")

    # Execution dependencies describe data production, not every Catalog/document dependency.
    if "cleaning" in targets:
        targets.add("standardization")
    if "segmentation" in targets:
        targets.update(("standardization", "cleaning"))
    if "modeling" in targets:
        targets.update(("standardization", "cleaning", "review"))

    order = ("simulation", "standardization", "cleaning", "segmentation", "modeling", "optimization", "review", "report", "visualization", "experiment", "supervision")
    dependencies = {
        "simulation": [], "standardization": [], "cleaning": ["standardization"], "segmentation": ["cleaning"],
        "modeling": ["cleaning"], "optimization": [], "review": ["modeling"], "report": [],
        "visualization": [], "experiment": [], "supervision": [],
    }
    steps = []
    for group in order:
        if group not in targets:
            continue
        steps.append({
            "id": group,
            "executor": group,
            "skill_ids": list(GROUP_SKILLS[group]),
            "dependencies": [item for item in dependencies[group] if item in targets],
            "inputs": {
                "simulation": ["scenario", "generation_parameters"],
                "standardization": ["source_csv|dataframe"],
                "cleaning": ["standardized_data", "dictionary"],
                "segmentation": ["cleaning_result"],
                "modeling": ["modeling_data", "dictionary", "split_manifest"],
                "optimization": ["objective", "model", "bounds", "constraints", "real_data"],
                "review": ["standardization_result", "cleaning_result", "modeling_result"],
                "report": ["prior_skill_results|pipeline_snapshot"],
                "visualization": ["pipeline_snapshot|prediction_artifact"],
                "experiment": ["pipeline_run_registry"],
                "supervision": ["prior_skill_results", "pipeline_snapshot"],
            }[group],
            "expected_outputs": [group + "_result"],
            "blocking_rules": ["missing_required_inputs", "failed_dependency"],
        })
    return {"version": "core-executor-dag-v1", "steps": steps, "target_groups": [item["id"] for item in steps]}
