import json
import subprocess
from pathlib import Path

from django.test import SimpleTestCase
from pathlib import Path
import json

from core.skills.analysis_plan import CAPABILITIES, GENERIC_UNKNOWN_SAFE, build_analysis_plan
from core.skills.catalog import identify_scene_from_text
from core.skills.work_repair import route_work_repair_task


class WorkRepairSkillTests(SimpleTestCase):
    def test_multi_label_project_routing(self):
        result = route_work_repair_task("Steel 数据识别正确，但页面要求高炉字段")
        self.assertTrue({"SCENE_RECOGNITION", "PIPELINE", "FRONTEND_PAGE", "BUG_DIAGNOSIS"}.issubset(result["task_types"]))
        self.assertNotIn("industrial_analysis", result["lazy_loading"]["references"])

    def test_required_capability_contract(self):
        self.assertEqual(14, len(CAPABILITIES))
        self.assertTrue(all(item["requires"] for item in CAPABILITIES.values()))

    def test_five_scene_plans_and_unknown_safety(self):
        cases = {
            "steel_industry_energy": "分析钢厂加热炉能耗与趋势",
            "thermal_power_boiler_long_tail": "分析锅炉长尾异常和稳定性",
            "vapor_pressure_soft_sensor": "分析蒸汽压力软测量时序相关性",
            "blast_furnace": "分析高炉铁水硅含量质量与工况",
            "unknown_scene": "分析这份未知数据的趋势、相关和异常",
        }
        plans = {scene: build_analysis_plan(text, scene=scene) for scene, text in cases.items()}
        for scene, plan in plans.items():
            self.assertEqual(scene, plan["scene"])
            self.assertTrue(plan["selected_capabilities"])
            self.assertEqual({"facts", "findings", "hypotheses", "limitations"}, set(plan["result_contract"]["layers"]))
        selected_unknown = {item["capability"] for item in plans["unknown_scene"]["selected_capabilities"]}
        self.assertTrue(selected_unknown.issubset(GENERIC_UNKNOWN_SAFE))
        self.assertNotIn("EQUIPMENT_HEALTH", selected_unknown)
        self.assertNotIn("ROOT_CAUSE_CANDIDATES", selected_unknown)

    def test_specific_furnaces_are_not_blast_furnace(self):
        self.assertEqual("steel_industry_energy", identify_scene_from_text("钢厂加热炉能耗")[0])
        self.assertEqual("thermal_power_boiler_long_tail", identify_scene_from_text("锅炉长尾分析")[0])

    def test_low_mapping_confidence_blocks_domain_conclusion(self):
        plan = build_analysis_plan(
            "分析设备故障根因和能耗",
            scene="custom_scene",
            evidence={
                "dataset_ref": "caller://dataset/1",
                "mapping_confidence": 0.4,
                "fields": [{"semantic_type": "energy", "data_type": "float", "mapping_confidence": 0.4}],
            },
        )
        selected = {item["capability"] for item in plan["selected_capabilities"]}
        self.assertNotIn("ENERGY_ANALYSIS", selected)
        self.assertNotIn("EQUIPMENT_HEALTH", selected)
        self.assertNotIn("ROOT_CAUSE_CANDIDATES", selected)

    def test_standalone_skill_contracts_are_valid_json(self):
        skill_dir = Path(__file__).parent / "skills" / "industrial-analysis"
        self.assertTrue((skill_dir / "SKILL.md").is_file())
        for name in ("analysis-plan.schema.json", "analysis-result.schema.json"):
            with (skill_dir / "contracts" / name).open(encoding="utf-8") as source:
                self.assertEqual("object", json.load(source)["type"])

    def test_standalone_skill_has_no_project_import_dependency(self):
        script = Path(__file__).parent / "skills" / "industrial-analysis" / "scripts" / "build_analysis_plan.py"
        payload = {
            "scene": "steel_industry_energy", "objective": "分析能耗趋势", "dataset_ref": "caller://data",
            "timestamp": "timestamp", "sample_size": 100,
            "fields": [{"semantic_type": "energy", "data_type": "float", "mapping_confidence": 0.98}],
        }
        completed = subprocess.run(["python3", str(script)], input=json.dumps(payload), text=True, capture_output=True, check=True)
        plan = json.loads(completed.stdout)
        selected = {item["capability"] for item in plan["selected_capabilities"]}
        self.assertIn("ENERGY_ANALYSIS", selected)
        self.assertIn("TREND_ANALYSIS", selected)
