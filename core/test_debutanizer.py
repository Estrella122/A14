import sys
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase

STANDARDIZATION = Path(settings.BASE_DIR) / "integrations" / "standardization"
if str(STANDARDIZATION) not in sys.path:
    sys.path.insert(0, str(STANDARDIZATION))

from standard_agent import ScenarioRepository, StandardizationAgent
from standard_agent.demo import generate_demo


class DebutanizerScenarioTests(SimpleTestCase):
    columns = ["sample_timestamp", "sample_index", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"]

    def test_public_columns_map_without_relabeling_other_processes(self):
        agent = StandardizationAgent(ScenarioRepository())
        mapping = agent.map_columns(self.columns, "debutanizer_column")
        self.assertEqual(mapping["required_coverage"], 0.111)
        self.assertEqual(len(mapping["missing_required"]), 8)
        self.assertTrue(all(row["decision"] == "REVIEW_REQUIRED" for row in mapping["mappings"] if row["raw"].startswith("U")))
        resolved = {row["raw"]: row["standard"] for row in mapping["mappings"]}
        self.assertEqual(resolved["U3"], "reflux_flow")
        self.assertEqual(resolved["U8"], "bottom_butane_content")

    def test_auto_detection_prefers_debutanizer(self):
        detection = StandardizationAgent(ScenarioRepository()).detect_scenario(
            self.columns, instruction="公开炼油脱丁烷塔数据"
        )
        self.assertEqual(detection["selected"]["scenario_id"], "debutanizer_column")
        self.assertNotEqual(detection["status"], "confirmed")  # Anonymous channels remain candidates, not physical proof.

    def test_time_axis_limit_is_exposed(self):
        scenario = ScenarioRepository().get("debutanizer_column").summary()
        self.assertEqual(scenario["time_axis_type"], "wall_clock")
        self.assertEqual(scenario["sampling_seconds"], 60)
        self.assertEqual(scenario["measurement_delay_minutes"], {"min": 30, "max": 75})
        self.assertEqual(scenario["expected_rows"], 2394)
        self.assertEqual(scenario["primary_output"], "bottom_butane_content")

    def test_physical_debutanizer_demo_matches_second_scene(self):
        frame = generate_demo("debutanizer_column", rows=2394, seed=20260911)
        self.assertEqual(frame.shape, (2394, 9))
        self.assertIn("C4浓度(%)", frame.columns)
        result = StandardizationAgent(ScenarioRepository()).standardize(
            frame,
            scenario_id="auto",
            instruction="炼油脱丁烷精馏塔，7个温度压力流量输入，C4浓度输出，30-75分钟测量滞后",
        )
        self.assertEqual(result["scenario"]["scenario_id"], "debutanizer_column")
        self.assertEqual(result["mapping"]["required_coverage"], 1.0)
        self.assertEqual(result["data_decision"]["status"], "ready")
        resolved = {row["raw"]: row["standard"] for row in result["mapping"]["mappings"]}
        self.assertEqual(resolved["塔顶压力(kPa)"], "top_pressure")
        self.assertEqual(resolved["C4浓度(%)"], "bottom_butane_content")

    def test_prepared_public_dataset_is_complete(self):
        path = Path(settings.BASE_DIR) / "datasets/public/debutanizer/debutanizer_processpilot.csv"
        if not path.exists():
            self.skipTest("上游数据未声明可再分发许可证；按 README.md 在本地获取后运行此项")
        frame = pd.read_csv(path)
        self.assertEqual(frame.shape, (2394, 10))
        self.assertFalse(frame.isna().any().any())
        self.assertEqual(frame["sample_index"].tolist(), list(range(2394)))
