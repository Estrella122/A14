from pathlib import Path
import sys

import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase


STANDARDIZATION = Path(settings.BASE_DIR) / "integrations" / "standardization"
if str(STANDARDIZATION) not in sys.path:
    sys.path.insert(0, str(STANDARDIZATION))

from standard_agent import ScenarioRepository, StandardizationAgent


class IndustrialEnergyStandardizationTests(SimpleTestCase):
    def setUp(self):
        self.agent = StandardizationAgent(ScenarioRepository())

    def test_uci_steel_energy_columns_are_ready(self):
        frame = pd.DataFrame({
            "date": ["01/01/2018 00:15", "01/01/2018 00:30"],
            "Usage_kWh": [3.17, 4.00],
            "Lagging_Current_Reactive.Power_kVarh": [2.95, 3.10],
            "Leading_Current_Reactive_Power_kVarh": [0.0, 0.0],
            "CO2(tCO2)": [0.0, 0.0],
            "Lagging_Current_Power_Factor": [73.21, 79.0],
            "Leading_Current_Power_Factor": [100.0, 100.0],
            "NSM": [900, 1800],
            "WeekStatus": ["Weekday", "Weekday"],
            "Day_of_week": ["Monday", "Monday"],
            "Load_Type": ["Light_Load", "Light_Load"],
        })
        result = self.agent.standardize(frame)
        self.assertEqual(result["scenario"]["scenario_id"], "steel_industry_energy")
        self.assertEqual(result["mapping"]["required_coverage"], 1.0)
        self.assertEqual(result["data_decision"]["status"], "ready")
        self.assertEqual(result["standardized_data"]["timestamp"].notna().sum(), 2)

    def test_opaque_plant_tags_require_dictionary(self):
        mapping = self.agent.map_columns(["PT_8313A.AV_0#", "FT_8301.AV_0#"], "steel_reheating_furnace")
        self.assertTrue(all(item["standard"] is None for item in mapping["mappings"]))
        self.assertTrue(all(item["method"] == "opaque_tag_requires_dictionary" for item in mapping["mappings"]))

    def test_manual_ignore_is_audited_without_mapping(self):
        frame = pd.DataFrame({"date": ["01/01/2018 00:15"], "unknown_tag": [1]})
        result = self.agent.standardize(frame, scenario_id="steel_industry_energy", overrides={"unknown_tag": "__ignore__"})
        ignored = next(item for item in result["mapping"]["mappings"] if item["raw"] == "unknown_tag")
        self.assertEqual(ignored["method"], "manual_ignore")
        self.assertIsNone(ignored["standard"])
