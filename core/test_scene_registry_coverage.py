from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase

from integrations.standardization.standard_agent.engine import StandardizationAgent
from integrations.standardization.standard_agent.repository import ScenarioRepository


class SceneRegistryCoverageTests(SimpleTestCase):
    def setUp(self):
        self.repository = ScenarioRepository()
        self.agent = StandardizationAgent(self.repository)

    def test_new_scenes_have_complete_recognition_contracts(self):
        for scenario_id in (
            "steel_industry_energy",
            "thermal_power_boiler_long_tail",
            "vapor_pressure_soft_sensor",
        ):
            template = self.repository.get(scenario_id)
            recognition = template.recognition
            self.assertTrue(recognition["required_features"])
            self.assertTrue(recognition["supporting_features"])
            self.assertTrue(recognition["conflicting_features"])
            self.assertGreaterEqual(recognition["min_evidence"], 2)
            self.assertGreaterEqual(recognition["min_confidence"], 0.52)
            self.assertGreaterEqual(recognition["min_required_coverage"], 0.55)

    def test_exact_published_point_is_resolved(self):
        result = self.agent.map_columns(["TE_8332A.AV_0#"], "thermal_power_boiler_long_tail")
        item = result["mappings"][0]
        self.assertEqual(item["standard"], "boiler_outlet_steam_temperature")
        self.assertEqual(item["method"], "point_dictionary")
        self.assertEqual(item["point_resolution"]["equipment"], "boiler")

    def test_prefix_only_point_remains_unresolved(self):
        result = self.agent.map_columns(["TE_101"], "thermal_power_boiler_long_tail")
        item = result["mappings"][0]
        self.assertIsNone(item["standard"])
        self.assertEqual(item["point_resolution"]["status"], "unresolved")
        self.assertEqual(item["point_resolution"]["measurement_type"], "temperature")
        self.assertIn("equipment", item["point_resolution"]["missing_knowledge"])

    def test_point_from_another_scene_is_not_cross_mapped(self):
        result = self.agent.map_columns(["FT_8301.AV_0#"], "industrial_dryer")
        item = result["mappings"][0]
        self.assertIsNone(item["standard"])
        self.assertEqual(item["point_resolution"]["status"], "known_other_scene")

    def test_real_files_when_available(self):
        cases = {
            Path("/Users/komi/Downloads/Steel_industry_data.csv"): ("steel_industry_energy", "confirmed"),
            Path("/Users/komi/Downloads/vapor-pressure.csv"): (None, "uncertain"),
            Path("/Users/komi/Downloads/data/xinan_completed_data.csv"): ("thermal_power_boiler_long_tail", "confirmed"),
            Path("/Users/komi/Downloads/data/xinan_uncompleted_data.csv"): ("thermal_power_boiler_long_tail", "confirmed"),
        }
        missing = [str(path) for path in cases if not path.exists()]
        if missing:
            self.skipTest("本机真实验收文件不存在：" + "、".join(missing))
        for path, expected in cases.items():
            with self.subTest(path=path.name):
                frame = pd.read_csv(path, encoding="utf-8-sig")
                result = self.agent.standardize(frame)
                self.assertEqual((result["detection"]["final_scene"], result["detection"]["status"]), expected)
