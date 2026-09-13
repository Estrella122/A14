from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .industrial_executor import execute_analysis
from .artifacts import EXECUTOR_ARTIFACT_CONTRACTS
from .core_executors import (CleaningExecutor, ExperimentExecutor, ModelingExecutor, OptimizationExecutor,
                             ModelDiagnosticsCapabilityExecutor, StageCapabilityExecutor, TimeDelayCapabilityExecutor,
                             ReportExecutor, ReviewExecutor, SegmentationExecutor, SimulationExecutor, StandardizationExecutor,
                             SupervisionExecutor, VisualizationExecutor)


class SkillExecutor(ABC):
    skill_id: str

    @abstractmethod
    def execute(self, skill_id: str, capability_ids: list[str], task_spec: dict[str, Any], data_context: dict[str, Any], inputs: dict[str, Any], runtime_context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class IndustrialAnalysisExecutor(SkillExecutor):
    skill_id = "industrial-analysis"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        analysis_plan = runtime_context["analysis_plan"]
        return execute_analysis(task_spec, analysis_plan, data_context, data=inputs.get("data"), data_path=inputs.get("data_path"), runtime_context=runtime_context)


EXECUTOR_DESCRIPTORS = {
    "industrial-analysis": {"status": "executable", "executor": IndustrialAnalysisExecutor()},
    "standardization": {"status": "executable", "executor": StandardizationExecutor()},
    "cleaning": {"status": "executable", "executor": CleaningExecutor()},
    "segmentation": {"status": "executable", "executor": SegmentationExecutor()},
    "modeling": {"status": "executable", "executor": ModelingExecutor()},
    "optimization": {"status": "executable", "executor": OptimizationExecutor()},
    "review": {"status": "executable", "executor": ReviewExecutor()},
    "report": {"status": "executable", "executor": ReportExecutor()},
    "simulation": {"status": "executable", "executor": SimulationExecutor()},
    "visualization": {"status": "executable", "executor": VisualizationExecutor()},
    "experiment": {"status": "executable", "executor": ExperimentExecutor()},
    "supervision": {"status": "executable", "executor": SupervisionExecutor()},
    "missing_anomaly_cleaner": {"status": "executable", "executor": StageCapabilityExecutor("missing_anomaly_cleaner", CleaningExecutor())},
    "high_snr_dynamic_segment_extractor": {"status": "executable", "executor": StageCapabilityExecutor("high_snr_dynamic_segment_extractor", SegmentationExecutor())},
    "time_delay_estimator_compensator": {"status": "executable", "executor": TimeDelayCapabilityExecutor()},
    "system_identification_trainer": {"status": "executable", "executor": StageCapabilityExecutor("system_identification_trainer", ModelingExecutor())},
    "model_diagnostics_evaluator": {"status": "executable", "executor": ModelDiagnosticsCapabilityExecutor()},
    "closed_loop_preprocessing_optimizer": {"status": "executable", "executor": StageCapabilityExecutor("closed_loop_preprocessing_optimizer", OptimizationExecutor())},
}
for _executor_id, _contract in EXECUTOR_ARTIFACT_CONTRACTS.items():
    if _executor_id in EXECUTOR_DESCRIPTORS:
        EXECUTOR_DESCRIPTORS[_executor_id]["requires_artifacts"] = list(_contract["requires"])
        EXECUTOR_DESCRIPTORS[_executor_id]["produces_artifacts"] = list(_contract["produces"])
EXECUTORS = {key: value["executor"] for key, value in EXECUTOR_DESCRIPTORS.items() if value["executor"] is not None}


def get_executor(skill_id: str) -> SkillExecutor | None:
    return EXECUTORS.get(skill_id)


def executor_status(skill_id: str) -> str:
    return EXECUTOR_DESCRIPTORS.get(skill_id, {"status": "unavailable"})["status"]
