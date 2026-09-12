from django.test import SimpleTestCase

from core.skills.catalog import SKILLS, SUPPORTED_SCENARIOS
from core.skills.runtime import plan_skills


class MultiScenarioSkillTests(SimpleTestCase):
    def test_every_skill_advertises_all_supported_scenarios(self):
        expected = set(SUPPORTED_SCENARIOS)
        self.assertTrue({"debutanizer_column", "thermal_power_boiler_long_tail", "vapor_pressure_soft_sensor", "steel_industry_energy"}.issubset(expected))
        for skill in SKILLS:
            self.assertEqual(set(skill.public()["supported_scenarios"]), expected)

    def test_industrial_entities_route_to_specific_scenario(self):
        cases = {
            "分析4号脱丁烷塔": "debutanizer_column",
            "提取7号工业干燥器快速动态段并做MIMO辨识": "industrial_dryer",
            "分析8号高炉铁水硅含量数据": "blast_furnace",
        }
        for message, scenario_id in cases.items():
            with self.subTest(message=message):
                self.assertEqual(plan_skills(message)["entities"]["scenario_id"], scenario_id)
