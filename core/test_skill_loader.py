import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from core.skills.runtime import plan_skills
from core.skills.skill_loader import default_skill_roots, discover_skills, load_business_skill_contexts, load_skill_context


class SkillLoaderTests(SimpleTestCase):
    def test_anomaly_loads_only_needed_capability_and_rules(self):
        trace = load_skill_context("分析工业数据中的异常", default_skill_roots(), scene="custom_scene", selected_capabilities=["ANOMALY_DETECTION"], selected_skill_name="industrial-analysis")
        self.assertEqual("industrial-analysis", trace["selected_skill"])
        self.assertEqual(["ANOMALY_DETECTION"], trace["loaded_capabilities"])
        self.assertEqual(["generic-analysis"], trace["loaded_workflows"])
        self.assertEqual(["evidence-rules", "confidence-rules"], trace["loaded_references"])
        self.assertNotIn("ENERGY_ANALYSIS", trace["loaded_capabilities"])

    def test_energy_routes_from_skill_manifest(self):
        trace = load_skill_context("分析工业能耗", default_skill_roots(), scene="custom_scene", selected_capabilities=["ENERGY_ANALYSIS"], selected_skill_name="industrial-analysis")
        self.assertEqual(["ENERGY_ANALYSIS"], trace["loaded_capabilities"])
        self.assertIn("industrial-semantics", trace["loaded_references"])

    def test_unknown_scene_excludes_equipment_fault_capability(self):
        trace = load_skill_context("分析未知工业数据异常和设备故障", default_skill_roots(), scene="unknown_scene", selected_capabilities=["ANOMALY_DETECTION", "EQUIPMENT_HEALTH"], selected_skill_name="industrial-analysis")
        self.assertIn("ANOMALY_DETECTION", trace["loaded_capabilities"])
        self.assertNotIn("EQUIPMENT_HEALTH", trace["loaded_capabilities"])
        self.assertIn("unknown-scene", trace["loaded_workflows"])

    def test_unknown_scene_keeps_generic_time_series_capability(self):
        trace = load_skill_context("分析未知工业数据的时序和滞后", default_skill_roots(), scene="unknown_scene", selected_capabilities=["TIME_SERIES_ANALYSIS"], selected_skill_name="industrial-analysis")
        self.assertEqual(["TIME_SERIES_ANALYSIS"], trace["loaded_capabilities"])

    def test_unrelated_request_does_not_load_industrial_skill(self):
        trace = load_skill_context("修改登录页面按钮颜色", default_skill_roots())
        self.assertIsNone(trace["selected_skill"])
        self.assertEqual("", trace["context"])
        self.assertEqual(0, trace["performance"]["loaded_skill_count"])

    def test_resolver_selects_best_of_two_skills(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_skill(root, "first", ["分析", "异常"])
            self._write_skill(root, "second", ["分析", "能耗", "能源"])
            trace = load_skill_context("分析能源能耗", (root,), selected_capabilities=["ANOMALY_DETECTION"], selected_skill_name="second")
            self.assertEqual("second", trace["selected_skill"])
            self.assertEqual(2, trace["performance"]["skill_count"])

    def test_missing_skill_file_degrades_safely(self):
        with TemporaryDirectory() as directory:
            trace = load_skill_context("工业异常分析", (Path(directory),))
            self.assertIsNone(trace["selected_skill"])
            self.assertEqual([], trace["errors"])

    def test_missing_capability_file_is_traced_without_crash(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_skill(root, "broken", ["异常"], capability_path="capabilities/missing.md")
            trace = load_skill_context("异常", (root,), selected_capabilities=["ANOMALY_DETECTION"], selected_skill_name="broken")
            self.assertEqual("broken", trace["selected_skill"])
            self.assertEqual([], trace["loaded_capabilities"])
            self.assertTrue(any(item["resource"] == "capabilities/ANOMALY_DETECTION" for item in trace["errors"]))

    def test_runtime_injects_skill_context_and_trace(self):
        snapshot = {"run_id": "run", "results": {"standardization": {"source_row_count": 100, "scenario": {"scenario_id": "custom_scene", "sampling_seconds": 10}, "mapping": {"mappings": [{"raw": "time", "standard": "timestamp", "status": "matched", "role": "time", "data_type": "datetime", "confidence": 1}, {"raw": "x", "standard": "x", "status": "matched", "role": "state", "data_type": "float", "confidence": .9}]}}, "cleaning": {}}, "artifacts": {"source_csv": "source.csv"}}
        trace = plan_skills("分析工业数据中的异常", snapshot=snapshot)["analysis"]["skill_runtime"]
        self.assertEqual("industrial-analysis", trace["selected_skill"])
        self.assertIn("SKILL.md", trace["sources"])
        self.assertGreater(trace["performance"]["context_characters"], 0)
        self.assertGreater(trace["performance"]["estimated_tokens"], 0)
        self.assertEqual(["build-analysis-plan"], trace["invoked_scripts"])

    @staticmethod
    def _write_skill(root: Path, name: str, triggers: list[str], capability_path: str = "capabilities/anomaly.md") -> None:
        skill_root = root / name
        skill_root.mkdir()
        if capability_path == "capabilities/anomaly.md":
            (skill_root / "capabilities").mkdir()
            (skill_root / capability_path).write_text("# anomaly", encoding="utf-8")
        manifest = {
            "triggers": triggers,
            "capabilities": {"ANOMALY_DETECTION": {"path": capability_path, "triggers": ["异常"]}},
            "workflows": {}, "references": {}, "scripts": {},
        }
        (skill_root / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: synthetic test skill\n---\n<!-- skill-runtime-manifest\n{json.dumps(manifest, ensure_ascii=False)}\n-->\n",
            encoding="utf-8",
        )


class SkillDiscoveryTests(SimpleTestCase):
    def test_discovery_reads_manifest_metadata(self):
        skills, metrics = discover_skills(default_skill_roots())
        industrial = next(skill for skill in skills if skill.name == "industrial-analysis")
        self.assertIn("capabilities", industrial.manifest)
        self.assertIn("workflows", industrial.manifest)
        self.assertIn("references", industrial.manifest)
        self.assertIn("scripts", industrial.manifest)
        self.assertIn("input_requirements", industrial.manifest)
        self.assertIn("output_contract", industrial.manifest)
        self.assertGreaterEqual(metrics["skill_count"], 1)

    def test_all_catalog_skills_have_independent_document_entrypoints(self):
        from core.skills.catalog import SKILL_MAP
        skills, metrics = discover_skills(default_skill_roots())
        expected = set(SKILL_MAP)
        loaded = load_business_skill_contexts(skills, expected)
        self.assertEqual(expected, set(loaded["loaded_business_skills"]))
        self.assertEqual(30, len(loaded["business_skill_sources"]))
        self.assertFalse(loaded["business_skill_errors"])
        self.assertGreaterEqual(metrics["skill_count"], 31)
