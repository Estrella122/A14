import json
import math
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, override_settings

from core.skills.artifacts import RuntimeArtifactResolver
from core.skills.loader import load_manifest, ManifestError
from core.skills.registry import SkillRegistry, get_registry
from core.skills.runtime import execute_skill_plan, plan_skills


ROOT = Path(__file__).parent / "skills"
SNR = "signal_noise_ratio_estimator"
MULTI = "检查信噪比、时滞和共线性，并判断数据是否适合 ARX 建模。"


def snapshot_fixture(directory):
    # Deterministic test input; all metrics are computed by the real algorithms.
    rows = 700
    u = [math.sin(i / 7) + .3 * math.cos(i / 2.3) for i in range(rows)]
    v = [math.cos(i / 11) + .1 * math.sin(i * 1.7) for i in range(rows)]
    y = [0.] * rows
    for i in range(3, rows):
        y[i] = .5 * y[i-1] + .4 * u[i-3] + .15 * v[i-2] + .03 * math.sin(i * 2.7)
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=rows, freq="10s"), "air_flow": u, "fuel": v, "temperature": y}).set_index("timestamp")
    dictionary = [{"standard_name": name, "role": role} for name, role in [("air_flow", "manipulated"), ("fuel", "disturbance"), ("temperature", "controlled")]]
    snapshot = {"run_id": "md-fixture", "status": "completed", "results": {"standardization": {
        "scenario": {"primary_output": "temperature", "sampling_seconds": 10, "scenario_id": "custom"}, "dictionary": dictionary}}, "artifacts": {}}
    resolver = RuntimeArtifactResolver(snapshot)
    refs = []
    for kind, data in [("CLEANED_TRAIN", frame.iloc[:450]), ("MODELING_DATASET", frame.iloc[:450]), ("CLEANED_VALIDATION", frame.iloc[450:])]:
        refs.append(resolver.write_frame(kind, data, Path(directory)/f"{kind}.csv", "fixture", "input").public())
    snapshot["artifact_registry"] = refs
    return snapshot


class SkillMDLoaderTests(SimpleTestCase):
    def setUp(self):
        self.manifest = load_manifest(ROOT / "signal-noise-ratio-estimator/SKILL.md")

    def test_load_and_body(self):
        self.assertEqual(SNR, self.manifest.id)
        self.assertIn("证据边界", self.manifest.body)
        self.assertEqual(64, len(self.manifest.digest))

    def test_invalid_yaml_missing_fields_and_executor(self):
        source = self.manifest.path.read_text()
        versions = ["---\nid: [\n---\nbody", source.replace("id: signal_noise_ratio_estimator\n", ""),
            source.replace("requires:\n- CLEANED_TRAIN", "requires: wrong"),
            source.replace("function: execute", "function: absent"),
            source.replace("core.skills.signal-noise-ratio-estimator.executor", "core.skills.nonexistent.executor"),
            source.replace("version: 1.0.0", "version: 1.0.0\nversion: 2.0.0")]
        with TemporaryDirectory() as directory:
            path = Path(directory)/"SKILL.md"
            for text in versions:
                path.write_text(text)
                with self.subTest(text=text[:80]), self.assertRaises(ManifestError):
                    load_manifest(path)

    def test_registry_list_get_search_and_duplicates(self):
        registry = get_registry("md")
        self.assertEqual(13, len(registry.list()))
        self.assertIsNotNone(registry.get(SNR))
        self.assertEqual(SNR, registry.search("信噪比")[0]["skill_id"])
        with self.assertRaisesRegex(ManifestError, "duplicate"):
            registry.register(self.manifest)

    def test_body_only_matching_reads_actual_document(self):
        manifest = replace(self.manifest, body="设备振荡幅度诊断检查机械冲击", metadata={**self.manifest.metadata, "triggers": [], "name": "能力", "description": "能力"})
        registry = SkillRegistry(); registry.register(manifest)
        matches = registry.search("机械冲击幅度诊断")
        self.assertGreaterEqual(matches[0]["score"], .45)
        self.assertFalse(matches[0]["lexical_recall"])

    def test_dependency_graph_missing_and_cycle(self):
        registry = get_registry("md")
        order = registry.resolve_dependencies(["arx_structure_order_selector"])
        self.assertLess(order.index("time_delay_estimator_compensator"), order.index("collinearity_detector_reducer"))
        broken = replace(self.manifest, metadata={**self.manifest.metadata, "depends_on": ["absent"]})
        registry = SkillRegistry(); registry.register(broken)
        with self.assertRaisesRegex(ManifestError, "missing dependency"):
            registry.validate_dependency_graph()
        registry = SkillRegistry(); registry.register(replace(broken, metadata={**broken.metadata, "depends_on": [SNR]}))
        with self.assertRaisesRegex(ManifestError, "cyclic"):
            registry.validate_dependency_graph()


@override_settings(SKILL_MANIFEST_MODE="md", AGENT_RUNTIME_MODE="hybrid")
class MDSkillRuntimeTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.snapshot = snapshot_fixture(self.temp.name)
        log = patch("core.skills.runtime.RUNS_DIR", Path(self.temp.name)/"runs"); log.start(); self.addCleanup(log.stop)

    def test_snr_real_execution_without_catalog(self):
        with patch("core.skills.catalog.SKILLS", []), patch("core.skills.catalog.SKILL_MAP", {}):
            plan = plan_skills("当前数据的信噪比是多少？", snapshot=self.snapshot)
            result = execute_skill_plan(plan, self.snapshot)
        self.assertEqual([SNR], plan["direct_skill_ids"])
        execution = result["core_skill_execution_results"][0]
        self.assertEqual("success", execution["status"])
        self.assertTrue(execution["algorithm_invoked"])
        self.assertEqual(450, execution["metrics"]["sample_count"])
        self.assertEqual(3, execution["metrics"]["estimated_fields"])
        self.assertTrue(all(row["noise_power"] > 0 for row in execution["metrics"]["fields"]))
        self.assertIn("SKILL.md", execution["audit"]["manifest_path"])
        self.assertTrue(execution["audit"]["input_refs"])

    def test_multi_skill_real_dag_and_metrics(self):
        plan = plan_skills(MULTI, snapshot=self.snapshot)
        self.assertEqual(5, len(plan["steps"]))
        result = execute_skill_plan(plan, self.snapshot)
        rows = result["core_skill_execution_results"]
        self.assertEqual(5, len(rows))
        self.assertTrue(all(row["status"] in {"success", "read"} for row in rows), [(r["skill_id"],r["status"],r.get("warnings")) for r in rows])
        arx = next(row for row in rows if row["skill_id"] == "arx_structure_order_selector")
        self.assertEqual(12, arx["metrics"]["candidate_count"])
        self.assertTrue(math.isfinite(arx["metrics"]["validation"]["rmse"]))
        self.assertFalse(arx["evidence"][0]["test_accessed"])
        self.assertEqual(2, len(arx["audit"]["dependency_runs"]))

    def test_explanation_no_execution(self):
        plan = plan_skills("解释一下信噪比是什么", snapshot=self.snapshot)
        self.assertEqual("knowledge_explanation", plan["analysis"]["task_understanding"]["task_kind"])
        self.assertFalse(plan["analysis"]["execution_plan"]["core"]["steps"])
        self.assertIn("二阶差分", plan["analysis"]["agent_context"]["loaded_skill_context"])
        self.assertEqual([], execute_skill_plan(plan, self.snapshot)["core_skill_execution_results"])

    def test_missing_inputs_block_and_no_fabricated_metrics(self):
        empty = {"run_id": "no-files", "results": {}, "artifacts": {}}
        result = execute_skill_plan(plan_skills("当前数据的信噪比是多少？", snapshot=empty), empty)
        self.assertEqual("blocked", result["status"])
        self.assertEqual({}, result["core_skill_execution_results"][0]["metrics"])

    def test_api_details_and_plan(self):
        self.assertEqual(13, self.client.get("/api/agent/skills/").json()["data"]["total"])
        detail = self.client.get(f"/api/agent/skills/{SNR}/").json()["data"]
        self.assertEqual("SKILL.md", detail["manifest_source"])
        response = self.client.post("/api/agent/plans/", data=json.dumps({"message": "当前数据的信噪比是多少？"}), content_type="application/json")
        self.assertEqual(201, response.status_code)

    def test_unrelated_request_no_fallback(self):
        self.assertEqual([], plan_skills("帮我订机票")["steps"])

    def test_new_md_id_executes_without_catalog_registration(self):
        manifest = load_manifest(ROOT / "signal-noise-ratio-estimator/SKILL.md")
        manifest = replace(manifest, metadata={**manifest.metadata, "id": "new_signal_measurement"})
        registry = SkillRegistry(); registry.register(manifest)
        with patch("core.skills.registry.get_registry", return_value=registry), patch("core.skills.catalog.SKILLS", []):
            plan = plan_skills("当前数据的信噪比是多少？", snapshot=self.snapshot)
            result = execute_skill_plan(plan, self.snapshot)
        self.assertEqual(["new_signal_measurement"], plan["direct_skill_ids"])
        self.assertEqual("success", result["core_skill_execution_results"][0]["status"])

    def test_stale_manifest_rejected(self):
        plan = plan_skills("当前数据的信噪比是多少？", snapshot=self.snapshot)
        plan["analysis"]["execution_plan"]["core"]["steps"][0]["manifest_hash"] = "changed"
        with self.assertRaisesRegex(ValueError, "重新规划"):
            execute_skill_plan(plan, self.snapshot)

    def test_constant_short_and_non_numeric_data_are_unavailable(self):
        ref = self.snapshot["artifact_registry"][0]
        for frame in [pd.DataFrame({"x": [1.] * 40}), pd.DataFrame({"x": [1., 2., 4.]}), pd.DataFrame({"label": ["abc"] * 50})]:
            frame.to_csv(ref["path"], index=False)
            result = execute_skill_plan(plan_skills("当前数据的信噪比是多少？", snapshot=self.snapshot), self.snapshot)
            row = result["core_skill_execution_results"][0]
            self.assertEqual("unavailable", row["status"])
            self.assertTrue(all(item["snr_db"] is None for item in row["metrics"].get("fields", [])))
            self.assertTrue(row["audit"])

    def test_missing_time_axis_not_invented(self):
        path = self.snapshot["artifact_registry"][1]["path"]
        pd.read_csv(path).drop(columns="timestamp").to_csv(path,index=False)
        result = execute_skill_plan(plan_skills("估计时滞", snapshot=self.snapshot), self.snapshot)
        row = result["core_skill_execution_results"][0]
        self.assertEqual("unavailable", row["status"])
        self.assertFalse(row["algorithm_invoked"])

    def test_hypothetical_and_negations_protect_execution(self):
        for message in ["如果估计信噪比会发生什么", "不要计算信噪比，只解释原理", "按钮写着信噪比估计是什么意思"]:
            plan = plan_skills(message, snapshot=self.snapshot)
            self.assertFalse(plan.get("analysis",{}).get("execution_plan",{}).get("core",{}).get("steps",[]))

    @override_settings(SKILL_MANIFEST_MODE="hybrid")
    def test_mixed_workflow_preserves_unmigrated_request(self):
        plan = plan_skills("检查信噪比并导出报告", snapshot=self.snapshot)
        self.assertIn("final_artifact_exporter", plan["direct_skill_ids"])
        self.assertIn("manifest_fallback", plan["analysis"])

    @override_settings(SKILL_MANIFEST_MODE="hybrid")
    def test_chat_uses_current_executor_metrics(self):
        from core.services.agent_chat import chat
        with patch("core.services.agent_chat.get_run", return_value=self.snapshot):
            result = chat("当前数据的信噪比是多少？", self.snapshot["run_id"])
        self.assertEqual("md_registry", result["skill_plan"]["analysis"]["routing_source"])
        self.assertFalse(result["executed"])
        self.assertIn("SNR", result["answer"])
        self.assertIn("不能给出真实数值", result["answer"])
        self.assertFalse(result["runtime_observability"]["executor_results"])
