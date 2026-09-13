from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.skills.artifacts import ArtifactType
from core.skills.catalog import SKILL_MAP
from core.skills.contracts import EXECUTION_STATES, SKILL_CONTRACTS, execution_state_for
from core.skills.execution_plan import GROUP_SKILLS, build_execution_plan
from core.skills.runtime import execute_skill_plan, list_skills


class SkillExecutionContractTests(SimpleTestCase):
    def test_every_registered_skill_has_a_machine_readable_contract(self):
        self.assertEqual(set(SKILL_MAP), set(SKILL_CONTRACTS))
        for skill_id, contract in SKILL_CONTRACTS.items():
            with self.subTest(skill_id=skill_id):
                self.assertEqual(skill_id, contract.skill_id)
                self.assertTrue(contract.executor)
                self.assertTrue(contract.capability)
                self.assertIn(contract.execution_mode, {"orchestrate", "compute", "evidence"})
                self.assertTrue(contract.quality_gates)

    def test_catalog_exposes_typed_contracts(self):
        catalog = list_skills()
        for skill in catalog["skills"]:
            with self.subTest(skill_id=skill["id"]):
                contract = skill["execution_contract"]
                self.assertEqual(skill["id"], contract["skill_id"])
                self.assertEqual(skill["input_contract"], list(contract["requires"]))
                self.assertEqual(skill["output_contract"], list(contract["produces"]))

    def test_six_key_skills_have_explicit_capability_dispatch(self):
        expected = {
            "missing_anomaly_cleaner": ("cleaning", "clean_missing_and_anomalies"),
            "high_snr_dynamic_segment_extractor": ("segmentation", "extract_high_snr_segments"),
            "time_delay_estimator_compensator": ("industrial-analysis", "estimate_and_compensate_delay"),
            "system_identification_trainer": ("modeling", "train_system_identification_model"),
            "model_diagnostics_evaluator": ("modeling", "evaluate_model_diagnostics"),
            "closed_loop_preprocessing_optimizer": ("optimization", "optimize_preprocessing_closed_loop"),
        }
        for skill_id, (executor, capability) in expected.items():
            contract = SKILL_CONTRACTS[skill_id]
            self.assertEqual(executor, contract.executor)
            self.assertEqual(capability, contract.capability)

    def test_shared_executor_marks_direct_and_stage_support_skills(self):
        context = {
            "available_artifacts": [
                ArtifactType.MODELING_DATASET,
                ArtifactType.CLEANED_VALIDATION,
                ArtifactType.CLEANED_TEST,
                ArtifactType.FIELD_DICTIONARY,
            ],
            "available_contract_fields": ["input_fields", "output_field", "split_manifest"],
        }
        task = {"execution_mode": "execute", "response_intents": ["modeling"], "requested_outputs": [],
                "requested_capabilities": [], "constraints": {}, "objective": "训练系统辨识模型"}
        plan = build_execution_plan(task, ["system_identification_trainer"], context)
        modeling = next(item for item in plan["steps"] if item["id"] == "modeling")
        dispatch = {item["skill_id"]: item["selection_kind"] for item in modeling["capability_dispatch"]}
        self.assertEqual("core-executor-dag-v2", plan["version"])
        self.assertEqual("shared_stage", modeling["dispatch_mode"])
        self.assertEqual(["system_identification_trainer"], modeling["requested_skill_ids"])
        self.assertEqual("direct", dispatch["system_identification_trainer"])
        self.assertEqual("stage_support", dispatch["model_diagnostics_evaluator"])
        self.assertEqual(set(GROUP_SKILLS["modeling"]), set(dispatch))

    def test_canonical_execution_states_are_closed_and_deterministic(self):
        cases = {
            "executed": execution_state_for(status="success", invoked=True),
            "evidence_only": execution_state_for(status="success", evidence_read=True),
            "blocked": execution_state_for(status="unavailable"),
            "skipped": execution_state_for(status="skipped"),
            "failed": execution_state_for(status="failed"),
        }
        self.assertEqual(EXECUTION_STATES, set(cases))
        self.assertEqual(cases, {key: key for key in cases})

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_runtime_preserves_shared_stage_attribution(self):
        class Executor:
            def execute(self, skill_id, capability_ids, *_args):
                return {
                    "schema_version": "skill-execution-result-v2", "skill_id": skill_id, "executor": skill_id,
                    "status": "success", "execution_state": "executed", "algorithm_invoked": True,
                    "capabilities_executed": capability_ids, "facts": [], "findings": [], "hypotheses": [],
                    "limitations": [], "metrics": {}, "artifacts": [], "evidence": [], "warnings": [],
                    "execution_trace": [], "duration_ms": 1,
                }

        dispatch = [
            {"skill_id": skill_id, "capability": SKILL_CONTRACTS[skill_id].capability,
             "selection_kind": "direct" if skill_id == "system_identification_trainer" else "stage_support"}
            for skill_id in GROUP_SKILLS["modeling"]
        ]
        plan = {
            "mode": "execute", "objective": "训练系统辨识模型", "parameters": {},
            "direct_skill_ids": ["system_identification_trainer"],
            "steps": [{"skill_id": skill_id, "status": "selected"} for skill_id in GROUP_SKILLS["modeling"]],
            "analysis": {
                "task_understanding": {"parameters": [], "task_kind": "execute_pipeline"},
                "data_context": {}, "analysis_plan": {}, "skill_resolution": {"selected_skills": []},
                "execution_plan": {"fallback": {}, "core": {"target_groups": ["modeling"], "steps": [{
                    "id": "modeling", "executor": "modeling", "dispatch_mode": "shared_stage",
                    "skill_ids": list(GROUP_SKILLS["modeling"]),
                    "requested_skill_ids": ["system_identification_trainer"], "capability_dispatch": dispatch,
                    "dependencies": [], "requires_artifacts": [], "readiness_status": "executable",
                }]}},
            },
        }
        with TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)), patch("core.skills.runtime.get_executor", return_value=Executor()):
            result = execute_skill_plan(plan, {"run_id": "contract_test"})
        records = {item["skill_id"]: item for item in result["executions"]}
        self.assertEqual("direct", records["system_identification_trainer"]["executor_selection_kind"])
        self.assertEqual("stage_support", records["model_diagnostics_evaluator"]["executor_selection_kind"])
        self.assertEqual("executed", records["system_identification_trainer"]["execution_state"])
        self.assertEqual("executed", records["model_diagnostics_evaluator"]["execution_state"])
        self.assertTrue(all(item["algorithm_invoked"] for item in records.values()))
        runtime_dispatch = {item["skill_id"]: item for item in result["core_skill_execution_results"][0]["capability_dispatch"]}
        self.assertEqual("modeling", runtime_dispatch["system_identification_trainer"]["executor"])
        self.assertEqual("executed", runtime_dispatch["model_diagnostics_evaluator"]["execution_state"])
