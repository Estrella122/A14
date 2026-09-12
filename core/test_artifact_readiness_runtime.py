import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.skills.artifacts import (
    ArtifactType,
    EXECUTOR_ARTIFACT_CONTRACTS,
    RuntimeArtifactResolver,
    RuntimeArtifactRef,
    snapshot_artifact_registry,
)
from core.skills.capability_resolver import resolve_capabilities
from core.skills.core_executors import OptimizationExecutor
from core.skills.execution_plan import build_execution_plan
from core.skills.executor import EXECUTOR_DESCRIPTORS
from core.skills.runtime import execute_skill_plan


def task(*intents, capabilities=(), allow_upstream=True):
    return {
        "task_kind": "execute_pipeline", "execution_mode": "execute",
        "semantic_intents": list(intents), "response_intents": list(intents),
        "requested_capabilities": list(capabilities), "requested_outputs": ["findings"],
        "constraints": {"allow_upstream_execution": allow_upstream}, "objective": "runtime readiness test",
    }


def context(artifacts=(), contract=()):
    return {
        "available_artifacts": list(artifacts), "available_contract_fields": list(contract),
        "detected_scene": "thermal_power_boiler_long_tail", "scene_confidence": .95,
        "data_quality": 90, "sample_count": 100, "numeric_field_count": 5,
        "ordered_data": True, "timestamp": "timestamp",
    }


class ArtifactReferenceTests(SimpleTestCase):
    def test_runtime_artifact_ref_contains_full_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "train.csv"; path.write_text("x\n1\n", encoding="utf-8")
            ref = RuntimeArtifactResolver({}, {}).register(ArtifactType.CLEANED_TRAIN, path, "cleaning", "exec-1")
        self.assertTrue({"artifact_id", "artifact_type", "producer", "run_id", "stage", "path", "version",
                         "schema_version", "content_hash", "metadata"}.issubset(ref.public()))
        self.assertEqual(len(ref.content_hash), 64)

    def test_legacy_snapshot_is_adapted_without_second_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "train.csv").write_text("x\n1\n", encoding="utf-8")
            snapshot = {"run_id": "r1", "artifacts": {"train_csv": "train.csv"}}
            rows = snapshot_artifact_registry(snapshot, root)
        self.assertEqual(rows[0]["artifact_type"], ArtifactType.CLEANED_TRAIN)

    def test_old_snapshot_can_resolve_partition_from_central_legacy_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "r1" / "03_cleaning"
            run_dir.mkdir(parents=True)
            (run_dir / "train.csv").write_text("x\n1\n", encoding="utf-8")
            resolver = RuntimeArtifactResolver({"run_id": "r1", "artifacts": {}}, {})
            with patch("core.services.pipeline.RUNS_DIR", Path(directory)):
                ref = resolver.resolve(ArtifactType.CLEANED_TRAIN)
                self.assertIn(ArtifactType.CLEANED_TRAIN, resolver.available_types())
        self.assertEqual(Path(ref.path).name, "train.csv")

    def test_missing_legacy_file_is_not_reported_ready(self):
        snapshot = {"run_id": "missing", "artifacts": {"train_csv": "03_cleaning/train.csv"}}
        with tempfile.TemporaryDirectory() as directory, patch("core.services.pipeline.RUNS_DIR", Path(directory)):
            self.assertNotIn(ArtifactType.CLEANED_TRAIN, RuntimeArtifactResolver(snapshot, {}).available_types())

    def test_executor_registry_exposes_requires_and_produces(self):
        for name in ("standardization", "cleaning", "segmentation", "modeling", "optimization"):
            with self.subTest(name=name):
                self.assertEqual(EXECUTOR_DESCRIPTORS[name]["requires_artifacts"], list(EXECUTOR_ARTIFACT_CONTRACTS[name]["requires"]))
                self.assertEqual(EXECUTOR_DESCRIPTORS[name]["produces_artifacts"], list(EXECUTOR_ARTIFACT_CONTRACTS[name]["produces"]))


class ArtifactReadinessTests(SimpleTestCase):
    def candidate(self, resolution, name):
        return next(row for row in resolution["candidates"] if row["candidate"] == name)

    def test_a_segmentation_with_artifacts_is_selected(self):
        required = EXECUTOR_ARTIFACT_CONTRACTS["segmentation"]["requires"]
        row = self.candidate(resolve_capabilities(task("selection", capabilities=("SEGMENTATION",)), context(required)), "SEGMENTATION")
        self.assertEqual((row["status"], row["artifact_readiness_score"]), ("selected", 1.0))

    def test_b_segmentation_without_train_or_upstream_is_blocked(self):
        row = self.candidate(resolve_capabilities(task("selection", capabilities=("SEGMENTATION",), allow_upstream=False), context()), "SEGMENTATION")
        self.assertEqual(row["status"], "blocked")
        self.assertIn(ArtifactType.CLEANED_TRAIN, row["missing_artifacts"])

    def test_c_segmentation_waits_for_cleaning(self):
        row = self.candidate(resolve_capabilities(task("selection", capabilities=("SEGMENTATION",)), context()), "SEGMENTATION")
        self.assertEqual(row["status"], "deferred")
        self.assertIn(ArtifactType.CLEANED_TRAIN, row["producible_artifacts"])

    def test_d_optimization_with_complete_artifacts_is_selected(self):
        required = EXECUTOR_ARTIFACT_CONTRACTS["optimization"]["requires"]
        policy = ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data")
        row = self.candidate(resolve_capabilities(task("optimization", capabilities=("OPTIMIZATION",)), context(required, policy)), "OPTIMIZATION")
        self.assertEqual(row["status"], "selected")

    def test_e_optimization_without_model_or_modeling_plan_is_blocked(self):
        policy = ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data")
        row = self.candidate(resolve_capabilities(task("optimization", capabilities=("OPTIMIZATION",)), context(contract=policy)), "OPTIMIZATION")
        self.assertEqual(row["status"], "blocked")
        self.assertIn(ArtifactType.MODEL_ARTIFACT, row["missing_artifacts"])

    def test_f_optimization_waits_for_planned_model(self):
        policy = ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data")
        row = self.candidate(resolve_capabilities(task("modeling", "optimization", capabilities=("OPTIMIZATION",)), context(contract=policy)), "OPTIMIZATION")
        self.assertEqual(row["status"], "deferred")
        self.assertIn(ArtifactType.MODEL_ARTIFACT, row["producible_artifacts"])

    def test_missing_optimization_policy_is_blocked_before_executor(self):
        required = EXECUTOR_ARTIFACT_CONTRACTS["optimization"]["requires"]
        row = self.candidate(resolve_capabilities(task("optimization", capabilities=("OPTIMIZATION",)), context(required)), "OPTIMIZATION")
        self.assertEqual(row["status"], "blocked")
        self.assertIn("bounds", row["missing_contract_fields"])


class ArtifactDagAndResultTests(SimpleTestCase):
    @staticmethod
    def runtime_plan(nodes):
        return {
            "mode": "execute", "objective": "artifact transition", "parameters": {}, "steps": [],
            "direct_skill_ids": [], "selected_count": 0,
            "analysis": {"task_understanding": {"task_kind": "execute_pipeline"}, "analysis_plan": {},
                         "skill_resolution": {"selected_skills": []},
                         "execution_plan": {"core": {"target_groups": [node["id"] for node in nodes], "steps": nodes}}},
        }

    def test_artifact_contract_builds_cleaning_to_segmentation_edge(self):
        plan = build_execution_plan(task("selection"), ["high_snr_dynamic_segment_extractor"], context())
        nodes = {row["id"]: row for row in plan["steps"]}
        self.assertEqual(nodes["segmentation"]["dependencies"], ["cleaning"])
        self.assertEqual(nodes["segmentation"]["readiness_status"], "deferred")

    def test_artifact_contract_builds_modeling_to_optimization_edge(self):
        policy = ("objective", "decision_variables", "bounds", "constraints", "search_space", "optimization_policy", "real_data")
        plan = build_execution_plan(task("modeling", "optimization"), ["system_identification_trainer", "closed_loop_preprocessing_optimizer"], context(contract=policy))
        nodes = {row["id"]: row for row in plan["steps"]}
        self.assertEqual(nodes["optimization"]["dependencies"], ["modeling"])
        self.assertEqual(nodes["optimization"]["readiness_status"], "deferred")

    def test_skill_execution_result_has_uniform_status_contract(self):
        result = OptimizationExecutor().execute("optimization", [], {}, {}, {"snapshot": {}, "optimization_request": {}}, {"state": {}})
        required = {"skill_id", "executor", "status", "reason", "inputs", "outputs", "missing_requirements",
                    "missing_artifacts", "metrics", "evidence", "provenance", "warnings"}
        self.assertTrue(required.issubset(result))
        self.assertEqual(result["status"], "blocked")

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_c_deferred_segmentation_runs_after_cleaning_registers_artifacts(self):
        calls = []

        class Stub:
            def __init__(self, produces): self.produces = produces
            def execute(self, skill_id, _caps, _task, _context, inputs, runtime):
                calls.append(skill_id)
                resolver = RuntimeArtifactResolver(inputs["snapshot"], runtime["state"])
                for artifact_type in self.produces:
                    path = Path(runtime["output_dir"]) / f"{artifact_type}.json"
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}", encoding="utf-8")
                    resolver.register(artifact_type, path, skill_id, runtime["execution_id"])
                return {"status": "success", "skill_id": skill_id, "executor": skill_id, "reason": "ok",
                        "inputs": [], "outputs": [], "missing_requirements": [], "missing_artifacts": [],
                        "provenance": {}, "capabilities_executed": [], "facts": [], "findings": [],
                        "hypotheses": [], "limitations": [], "metrics": {}, "artifacts": [], "evidence": [],
                        "warnings": [], "execution_trace": [], "duration_ms": 0}

        required = list(EXECUTOR_ARTIFACT_CONTRACTS["segmentation"]["requires"])
        nodes = [
            {"id": "cleaning", "executor": "cleaning", "skill_ids": [], "dependencies": [], "requires_artifacts": []},
            {"id": "segmentation", "executor": "segmentation", "skill_ids": [], "dependencies": ["cleaning"],
             "requires_artifacts": required, "readiness_status": "deferred"},
        ]
        with tempfile.TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)), \
                patch("core.skills.runtime.get_executor", side_effect=lambda name: Stub(required if name == "cleaning" else [])):
            result = execute_skill_plan(self.runtime_plan(nodes), {})
        self.assertEqual(calls, ["cleaning", "segmentation"])
        self.assertEqual([row["status"] for row in result["core_skill_execution_results"]], ["success", "success"])

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_f_deferred_optimization_runs_after_modeling_registers_model(self):
        calls = []

        class Stub:
            def execute(self, skill_id, _caps, _task, _context, inputs, runtime):
                calls.append(skill_id)
                if skill_id == "modeling":
                    path = Path(runtime["output_dir"]) / "model.json"
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}", encoding="utf-8")
                    RuntimeArtifactResolver(inputs["snapshot"], runtime["state"]).register(
                        ArtifactType.MODEL_ARTIFACT, path, skill_id, runtime["execution_id"])
                return {"status": "success", "skill_id": skill_id, "executor": skill_id, "reason": "ok",
                        "inputs": [], "outputs": [], "missing_requirements": [], "missing_artifacts": [],
                        "provenance": {}, "capabilities_executed": [], "facts": [], "findings": [],
                        "hypotheses": [], "limitations": [], "metrics": {}, "artifacts": [], "evidence": [],
                        "warnings": [], "execution_trace": [], "duration_ms": 0}

        with tempfile.TemporaryDirectory() as directory:
            initial = [item for item in EXECUTOR_ARTIFACT_CONTRACTS["optimization"]["requires"] if item != ArtifactType.MODEL_ARTIFACT]
            registry = []
            for artifact_type in initial:
                path = Path(directory) / f"{artifact_type}.json"; path.write_text("{}", encoding="utf-8")
                registry.append(RuntimeArtifactResolver({"run_id": "r1"}, {}).register(artifact_type, path, "fixture", "r1").public())
            snapshot = {"run_id": "r1", "artifact_registry": registry}
            nodes = [
                {"id": "modeling", "executor": "modeling", "skill_ids": [], "dependencies": [], "requires_artifacts": []},
                {"id": "optimization", "executor": "optimization", "skill_ids": [], "dependencies": ["modeling"],
                 "requires_artifacts": list(EXECUTOR_ARTIFACT_CONTRACTS["optimization"]["requires"]), "readiness_status": "deferred"},
            ]
            with patch("core.skills.runtime.RUNS_DIR", Path(directory)), patch("core.skills.runtime.get_executor", return_value=Stub()):
                result = execute_skill_plan(self.runtime_plan(nodes), snapshot)
        self.assertEqual(calls, ["modeling", "optimization"])
        self.assertEqual([row["status"] for row in result["core_skill_execution_results"]], ["success", "success"])
