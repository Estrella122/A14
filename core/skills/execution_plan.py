from __future__ import annotations

from typing import Any

from .artifacts import ArtifactType, EXECUTOR_ARTIFACT_CONTRACTS, EXECUTOR_INPUT_CONTRACTS, canonical_artifact_types
from .contracts import get_skill_contract


GROUP_SKILLS = {
    "simulation": ("industrial_simulation_generator",),
    "standardization": ("dataset_scenario_profiler", "semantic_field_unit_standardizer"),
    "cleaning": ("time_axis_alignment_resampler", "missing_anomaly_cleaner"),
    "segmentation": ("steady_transient_state_detector", "signal_noise_ratio_estimator", "high_snr_dynamic_segment_extractor", "segment_quality_scorer_ranker"),
    "modeling": ("time_delay_estimator_compensator", "collinearity_detector_reducer", "modeling_dataset_assembler", "arx_structure_order_selector", "system_identification_trainer", "multi_model_benchmark", "model_diagnostics_evaluator"),
    "optimization": ("closed_loop_preprocessing_optimizer",),
    "review": ("engineering_result_interpreter",),
    "report": ("expert_report_writer",),
    "visualization": ("engineering_visualization_builder",),
    "experiment": ("experiment_tracker_comparator",),
    "supervision": ("execution_supervisor_replanner",),
}
SKILL_GROUP = {skill_id: group for group, skill_ids in GROUP_SKILLS.items() for skill_id in skill_ids}
DEDICATED_EXECUTORS = {
    "missing_anomaly_cleaner", "high_snr_dynamic_segment_extractor", "time_delay_estimator_compensator",
    "system_identification_trainer", "model_diagnostics_evaluator", "closed_loop_preprocessing_optimizer",
}


def build_execution_plan(task_spec: dict[str, Any], direct_skill_ids: list[str], data_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the minimal executor DAG. Catalog dependencies remain planning metadata."""
    if task_spec.get("execution_mode") in {"analyze", "explain"}:
        return {"version": "core-executor-dag-v2", "steps": [], "target_groups": []}
    direct = set(direct_skill_ids)
    data_context = data_context or {}
    available_artifacts = canonical_artifact_types(data_context.get("available_artifacts") or ())
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
    if task_spec.get("constraints", {}).get("use_existing_model") and "optimization" in targets:
        targets.discard("modeling")
        targets.discard("review")
    if task_spec.get("constraints", {}).get("selection_only"):
        targets.discard("modeling")
        targets.discard("review")

    # Anomaly detection belongs to industrial-analysis. Lexical recall of the
    # cleaner must not silently turn it into a data mutation request.
    if "ANOMALY_DETECTION" in requested_capabilities and "MISSING_DATA_ANALYSIS" not in requested_capabilities:
        targets.discard("cleaning")
        targets.discard("standardization")

    # Execution dependencies describe data production, not every Catalog/document dependency.
    auto_dependencies = task_spec.get("constraints", {}).get("allow_upstream_execution", True)
    if auto_dependencies and "cleaning" in targets and not set(EXECUTOR_ARTIFACT_CONTRACTS["cleaning"]["requires"]) <= available_artifacts:
        targets.add("standardization")
    if auto_dependencies and "segmentation" in targets and not set(EXECUTOR_ARTIFACT_CONTRACTS["segmentation"]["requires"]) <= available_artifacts:
        targets.update(("standardization", "cleaning"))
    modeling_pipeline_requested = "modeling" in targets and (
        bool(direct & {"modeling_dataset_assembler", "arx_structure_order_selector", "system_identification_trainer", "multi_model_benchmark", "collinearity_detector_reducer"})
        or not (direct & set(GROUP_SKILLS["modeling"]))
    )
    modeling_data_requested = bool(direct & {"time_delay_estimator_compensator", "modeling_dataset_assembler", "arx_structure_order_selector", "system_identification_trainer", "multi_model_benchmark"})
    if "modeling" in targets and modeling_data_requested and auto_dependencies and ArtifactType.MODELING_DATASET not in available_artifacts:
        targets.update(("standardization", "cleaning"))
    if "modeling" in targets and modeling_pipeline_requested:
        if auto_dependencies and not set(EXECUTOR_ARTIFACT_CONTRACTS["modeling"]["requires"]) <= available_artifacts:
            targets.update(("standardization", "cleaning"))
        targets.add("review")
    if auto_dependencies and "optimization" in targets and "modeling" in targets and ArtifactType.SELECTED_SEGMENTS not in available_artifacts:
        targets.update(("standardization", "cleaning", "segmentation"))

    order = ("simulation", "standardization", "cleaning", "segmentation", "modeling", "optimization", "review", "report", "visualization", "experiment", "supervision")
    node_specs = {}
    for group in order:
        if group not in targets:
            continue
        requested = [skill_id for skill_id in GROUP_SKILLS[group] if skill_id in direct]
        dedicated = requested[0] if len(requested) == 1 and requested[0] in DEDICATED_EXECUTORS else None
        if dedicated:
            skill_contract = get_skill_contract(dedicated)
            node_specs[group] = {
                "executor": dedicated, "dispatch_mode": "dedicated_capability", "skill_ids": [dedicated],
                "requested_skill_ids": [dedicated],
                "requires": tuple(skill_contract.requires), "produces": tuple(skill_contract.produces),
            }
        else:
            group_contract = EXECUTOR_ARTIFACT_CONTRACTS.get(group, {"requires": (), "produces": ()})
            node_specs[group] = {
                "executor": group, "dispatch_mode": "shared_stage", "skill_ids": list(GROUP_SKILLS[group]),
                "requested_skill_ids": requested, "requires": tuple(group_contract["requires"]), "produces": tuple(group_contract["produces"]),
            }
    producers = {artifact: group for group, spec in node_specs.items() for artifact in spec["produces"]}
    steps = []
    for group in order:
        if group not in targets:
            continue
        spec = node_specs[group]
        contract = {"requires": spec["requires"], "produces": spec["produces"]}
        missing_artifacts = [item for item in contract["requires"] if item not in available_artifacts]
        dependencies = list(dict.fromkeys(producers[item] for item in missing_artifacts if item in producers and producers[item] != group))
        if dependencies:
            dependencies = [max(dependencies, key=order.index)]
        if group == "review" and "optimization" in targets:
            dependencies = ["optimization"]
        missing_unproducible = [item for item in missing_artifacts if item not in producers]
        required_inputs = EXECUTOR_INPUT_CONTRACTS.get(group, ()) if spec["executor"] in {group, "closed_loop_preprocessing_optimizer"} else ()
        available_inputs = set(data_context.get("available_contract_fields") or ())
        missing_requirements = [item for item in required_inputs if item not in available_inputs]
        readiness_status = "blocked" if missing_unproducible or missing_requirements else "deferred" if dependencies else "executable"
        readiness_reason = "前置 artifact 和输入合同已满足" if readiness_status == "executable" else (
            "等待上游生成 " + "、".join(item for item in missing_artifacts if item in producers)
            if readiness_status == "deferred" else "缺少 " + "、".join([*missing_unproducible, *missing_requirements]))
        steps.append({
            "id": group,
            "executor": spec["executor"],
            "dispatch_mode": spec["dispatch_mode"],
            "skill_ids": spec["skill_ids"],
            "requested_skill_ids": spec["requested_skill_ids"],
            "capability_dispatch": [
                {
                    "skill_id": skill_id,
                    "capability": get_skill_contract(skill_id).capability,
                    "selection_kind": "direct" if skill_id in direct else "stage_support",
                }
                for skill_id in spec["skill_ids"]
            ],
            "dependencies": dependencies,
            "requires_artifacts": list(contract["requires"]),
            "produces_artifacts": list(contract["produces"]),
            "artifact_readiness": {item: item in available_artifacts or item in producers for item in contract["requires"]},
            "missing_artifacts": missing_artifacts,
            "missing_requirements": missing_requirements,
            "readiness_status": readiness_status,
            "readiness_reason": readiness_reason,
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
    return {"version": "core-executor-dag-v2", "steps": steps, "target_groups": [item["id"] for item in steps]}
