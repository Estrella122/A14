from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .industrial_executor import execute_analysis


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


EXECUTORS: dict[str, SkillExecutor] = {IndustrialAnalysisExecutor.skill_id: IndustrialAnalysisExecutor()}


def get_executor(skill_id: str) -> SkillExecutor | None:
    return EXECUTORS.get(skill_id)
