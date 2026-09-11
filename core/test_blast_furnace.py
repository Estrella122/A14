import sys
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase


BASE_DIR = Path(settings.BASE_DIR)


class BlastFurnaceScenarioTests(SimpleTestCase):
    def test_real_demo_csv_uses_only_past_laboratory_values(self):
        frame = pd.read_csv(BASE_DIR / "frontend/public/datasets/blast_furnace_real_720h.csv")
        process_time = pd.to_datetime(frame["timestamp"])
        lab_time = pd.to_datetime(frame["lab_source_timestamp"])

        self.assertEqual(len(frame), 720)
        self.assertEqual(int((lab_time > process_time).sum()), 0)
        self.assertGreater(int(frame["hot_metal_si"].isna().sum()), 0)
        self.assertLessEqual(float(frame["lab_age_minutes"].max()), 180.0)

    def test_blast_furnace_dictionary_maps_source_tags_and_target(self):
        module_path = str(BASE_DIR / "integrations/standardization")
        sys.path.insert(0, module_path)
        try:
            from standard_agent import ScenarioRepository, StandardizationAgent

            raw = pd.DataFrame(
                {
                    "dt": pd.date_range("2026-01-01", periods=4, freq="h"),
                    "Fb": [3500, 3510, 3520, 3540],
                    "Fo": [15000, 15100, 15200, 15400],
                    "Th": [1100, 1102, 1105, 1107],
                    "R": [3.8, 3.82, 3.81, 3.84],
                    "Si": [0.51, 0.50, 0.49, 0.48],
                }
            )
            result = StandardizationAgent(ScenarioRepository()).standardize(raw, scenario_id="blast_furnace")
        finally:
            sys.path.remove(module_path)

        self.assertEqual(result["scenario"]["primary_output"], "hot_metal_si")
        self.assertIn("hot_metal_si", result["standardized_data"].columns)
        self.assertEqual(result["mapping"]["required_coverage"], 1.0)

    def test_causal_target_is_not_interpolated_by_cleaning(self):
        module_path = str(BASE_DIR / "integrations/data_cleaning/src")
        sys.path.insert(0, module_path)
        try:
            from data_cleaning_agent import DataCleaningSelectionAgent

            frame = pd.DataFrame(
                {
                    "timestamp": pd.date_range("2026-01-01", periods=3, freq="h"),
                    "blast_flow_rate": [3500.0, 3520.0, 3540.0],
                    "hot_metal_si": [0.51, None, 0.48],
                }
            )
            spec = {
                "blast_flow_rate": {"role": "input", "unit": "m3/min", "min": 0, "max": 10000, "max_step": 2000},
                "hot_metal_si": {"role": "output", "unit": "percent", "min": 0, "max": 5, "max_step": 1},
            }
            agent = DataCleaningSelectionAgent(spec, resample_rule="1h", causal_columns={"hot_metal_si"})
            aligned = agent.align_timestamp(frame)
            cleaned = agent.process_missing_values(aligned)
        finally:
            sys.path.remove(module_path)

        self.assertTrue(pd.isna(cleaned.iloc[1]["hot_metal_si"]))
        self.assertIn("不使用未来观测插值", " ".join(agent.logs))
