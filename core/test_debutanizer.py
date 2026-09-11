import sys
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase

STANDARDIZATION = Path(settings.BASE_DIR) / "integrations" / "standardization"
if str(STANDARDIZATION) not in sys.path:
    sys.path.insert(0, str(STANDARDIZATION))

from standard_agent import ScenarioRepository, StandardizationAgent


class DebutanizerScenarioTests(SimpleTestCase):
    columns = ["sample_timestamp", "sample_index", "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"]

    def test_public_columns_map_without_relabeling_other_processes(self):
        agent = StandardizationAgent(ScenarioRepository())
        mapping = agent.map_columns(self.columns, "debutanizer_column")
        self.assertEqual(mapping["required_coverage"], 1.0)
        self.assertEqual(mapping["missing_required"], [])
        resolved = {row["raw"]: row["standard"] for row in mapping["mappings"]}
        self.assertEqual(resolved["U3"], "reflux_flow")
        self.assertEqual(resolved["U8"], "bottom_butane_content")

    def test_auto_detection_prefers_debutanizer(self):
        detection = StandardizationAgent(ScenarioRepository()).detect_scenario(
            self.columns, instruction="公开炼油脱丁烷塔数据"
        )
        self.assertEqual(detection["selected"]["scenario_id"], "debutanizer_column")
        self.assertFalse(detection["is_ambiguous"])

    def test_time_axis_limit_is_exposed(self):
        scenario = ScenarioRepository().get("debutanizer_column").summary()
        self.assertEqual(scenario["time_axis_type"], "ordered_samples")
        self.assertIsNone(scenario["sampling_seconds"])
        self.assertEqual(scenario["primary_output"], "bottom_butane_content")

    def test_prepared_public_dataset_is_complete(self):
        path = Path(settings.BASE_DIR) / "datasets/public/debutanizer/debutanizer_processpilot.csv"
        if not path.exists():
            self.skipTest("上游数据未随仓库再分发；取得合法副本并完成转换后执行此项。")
        frame = pd.read_csv(path)
        self.assertEqual(frame.shape, (2394, 10))
        self.assertFalse(frame.isna().any().any())
        self.assertEqual(frame["sample_index"].tolist(), list(range(2394)))
