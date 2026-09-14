import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


STANDARDIZATION = Path(settings.BASE_DIR) / "integrations" / "standardization"
if str(STANDARDIZATION) not in sys.path:
    sys.path.insert(0, str(STANDARDIZATION))

from standard_agent import ScenarioRepository, StandardizationAgent
from core.services.pipeline import _effective_resample_rule


class SceneContextRegressionTests(SimpleTestCase):
    xinan_columns = [
        "date", "PT_8313A.AV_0#", "PT_8313B.AV_0#", "PT_8313C.AV_0#",
        "PT_8313D.AV_0#", "PT_8313E.AV_0#", "PT_8313F.AV_0#",
        "PTCA_8322A.AV_0#", "PTCA_8324.AV_0#", "TE_8319A.AV_0#",
        "TE_8319B.AV_0#", "TE_8313B.AV_0#", "TE_8303.AV_0#",
        "TE_8304.AV_0#", "TV_8329ZC.AV_0#", "FT_8301.AV_0#",
        "FT_8302.AV_0#", "FT_8306A.AV_0#", "AIR_8301A.AV_0#",
        "FT_8306B.AV_0#", "AIR_8301B.AV_0#", "YFJ3_AI.AV_0#",
        "YFJ3_ZD1.AV_0#", "YFJ3_ZD2.AV_0#", "SXLTCYZ.AV_0#",
        "SXLTCYY.AV_0#", "ZCLCCY.AV_0#", "YCLCCY.AV_0#",
        "YJJWSLL.AV_0#", "ZZQBCHLL.AV_0#", "TE_8332A.AV_0#",
    ]
    vapor_columns = [
        "hours_elapsed", *[f"temp_{index:02d}" for index in range(1, 14)],
        "valve_out_01", "valve_out_02", "flow_01", "flow_02", "flow_03",
        "pres_01", "analyzer_01", "reb_temp_rise", "reb_temp_avg",
        "inv_reb_temp", "inv_feed_temp", "inv_bot_temp", "inv_cond_pres",
        "antoine_estimate", "current_estimator", "vapour_pressure_kpa",
    ]

    def setUp(self):
        self.repository = ScenarioRepository()
        self.agent = StandardizationAgent(self.repository)

    def test_registry_keeps_reusable_auto_detection_scenes(self):
        loaded = {scenario.scenario_id for scenario in self.repository.list()}
        self.assertTrue({
            "debutanizer_column",
            "steel_industry_energy",
            "thermal_power_boiler_long_tail",
            "vapor_pressure_soft_sensor",
        }.issubset(loaded))

    def test_xinan_auto_detection_uses_point_semantics(self):
        detection = self.agent.detect_scenario(self.xinan_columns)
        self.assertEqual("thermal_power_boiler_long_tail", detection["selected"]["scenario_id"])
        self.assertEqual(0.948, detection["selected"]["confidence"])
        mapping = self.agent.map_columns(self.xinan_columns, "thermal_power_boiler_long_tail")
        self.assertEqual(31, sum(row["status"] == "matched" for row in mapping["mappings"]))
        resolved = {row["raw"]: row for row in mapping["mappings"]}
        self.assertEqual("upper_furnace_pressure_a", resolved["PT_8313A.AV_0#"]["standard"])
        self.assertEqual("point_dictionary", resolved["PT_8313A.AV_0#"]["method"])

    def test_vapor_auto_detection_does_not_inherit_project_scene(self):
        detection = self.agent.detect_scenario(self.vapor_columns)
        self.assertEqual("vapor_pressure_soft_sensor", detection["selected"]["scenario_id"])
        mapping = self.agent.map_columns(self.vapor_columns, "vapor_pressure_soft_sensor")
        self.assertEqual(30, sum(row["status"] == "matched" for row in mapping["mappings"]))
        self.assertNotIn("bottom_butane_content", mapping["missing_required"])

    def test_cross_scene_upload_uses_detected_sampling_period(self):
        scenario = {"scenario_id": "industrial_dryer", "sampling_seconds": 10}
        self.assertEqual(_effective_resample_rule("1h", scenario, "auto", "blast_furnace"), "10s")
        self.assertEqual(_effective_resample_rule("30s", scenario, "industrial_dryer", "industrial_dryer"), "30s")
