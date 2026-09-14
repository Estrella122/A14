from decimal import Decimal

import pandas as pd
from django.test import TestCase, override_settings

from core.models import OptimizationRun, OptimizationStudy, PipelineRunRecord, RuntimeJob
from core.services.control_safety import assess_candidate
from core.services.jobs import claim_next, enqueue
from core.services.pipeline import _persist_snapshot, get_run
from core.services.scene_registry import get_scene_config, identify_registered_scene, list_scene_configs
from core.skills.industrial_executor import execute_capability
from core.skills.runtime_events import RuntimeEventStore


class RuntimePersistenceTests(TestCase):
    def test_pipeline_snapshot_is_indexed_and_queryable(self):
        snapshot = {"run_id": "persist_001", "status": "running", "current_stage": "cleaning", "scenario_request": "blast_furnace", "original_name": "input.csv", "artifacts": {}, "results": {}}
        _persist_snapshot(snapshot)
        self.assertEqual(PipelineRunRecord.objects.get(run_id="persist_001").current_stage, "cleaning")
        self.assertEqual(get_run("persist_001")["status"], "running")

    def test_database_queue_claims_a_job_once(self):
        queued = enqueue("agent_chat", {"message": "test"}, result_ref="skillrun_test")
        claimed = claim_next()
        self.assertEqual(claimed.pk, queued.pk)
        self.assertEqual(RuntimeJob.objects.get(pk=queued.pk).status, "running")
        self.assertIsNone(claim_next())

    def test_skill_events_survive_file_store_loss(self):
        store = RuntimeEventStore("skillrun_db_test", "pipeline_1")
        store.emit("started", stage="runtime", status="running", message="开始")
        store.finish("completed", result={"answer": "ok"})
        store.state_path.unlink(missing_ok=True)
        store.events_path.unlink(missing_ok=True)
        snapshot = store.snapshot()
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["events"][0]["event_type"], "started")


class ControlSafetyTests(TestCase):
    def _candidate(self, mode="uploaded_csv", failures=None):
        study = OptimizationStudy.objects.create(
            project_code="SAFE-1", project_name="安全测试", dataset_mode=mode,
            status="completed", total_rounds=2, current_round=2,
        )
        run = OptimizationRun.objects.create(
            study=study, round_number=1, dynamic_segment_threshold=Decimal("0.2"),
            outlier_threshold="3σ", collinearity_threshold=Decimal("0.9"), lag_search_range="0-60s",
            min_segment_length="5min", model_r2=Decimal("0.8"), model_fit=Decimal("0.8"),
            rmse=Decimal("1.0"), overall_score=Decimal("80"), review_result="候选",
            candidate_parameters={"constraint_failures": failures or []}, is_best=True,
        )
        return study, run

    def test_even_approved_candidate_can_never_actuate(self):
        study, run = self._candidate()
        result = assess_candidate(study, run)
        self.assertTrue(result["shadow_trial_eligible"])
        self.assertFalse(result["actuation_allowed"])
        self.assertIn("plant_interlock_verified", result["blocking_checks"])

    def test_simulation_candidate_cannot_enter_shadow_trial(self):
        study, run = self._candidate(mode="synthetic_benchmark")
        self.assertFalse(assess_candidate(study, run)["shadow_trial_eligible"])


class SceneRegistryTests(TestCase):
    def test_registry_is_unique_and_drives_alias_resolution(self):
        rows = list_scene_configs()
        self.assertEqual(len(rows), len({row["id"] for row in rows}))
        self.assertEqual(identify_registered_scene("分析2号脱丁烷塔")["id"], "debutanizer_column")
        self.assertTrue(get_scene_config("industrial_dryer")["official"])


class IndustrialCapabilityDepthTests(TestCase):
    def test_every_declared_industrial_capability_has_a_specific_method(self):
        frame = pd.DataFrame({
            "fuel_gas_flow": [10, 11, 10, 14, 12, 11],
            "product_moisture": [8, 8.2, 8.1, 9.5, 8.3, 8.1],
            "bearing_temperature": [40, 41, 40, 55, 42, 41],
        })
        context = {"variable_roles": {"quality": ["product_moisture"]}, "scene_confidence": .9}
        capabilities = (
            "ENERGY_ANALYSIS", "EQUIPMENT_HEALTH", "QUALITY_ANALYSIS", "OPERATING_STATE",
            "BOTTLENECK_ANALYSIS", "ROOT_CAUSE_CANDIDATES",
        )
        for capability in capabilities:
            with self.subTest(capability=capability):
                result = execute_capability(capability, frame, context, {})
                self.assertEqual(result["status"], "success")
                self.assertNotEqual(result["metrics"].get("method"), None)
                self.assertNotIn("generic-context-analysis", str(result))
