from django.test import SimpleTestCase

from core.skills.catalog import SKILLS, SUPPORTED_SCENARIOS
from core.skills.runtime import plan_skills


class MultiScenarioSkillTests(SimpleTestCase):
    def test_every_skill_advertises_all_supported_scenarios(self):
        expected = set(SUPPORTED_SCENARIOS)
        self.assertEqual(len(expected), 8)
        for skill in SKILLS:
            self.assertEqual(set(skill.public()["supported_scenarios"]), expected)

    def test_industrial_entities_route_to_specific_scenario(self):
        cases = {
            "分析2号锅炉燃煤数据": "thermal_power_boiler",
            "清洗3号曝气池氨氮数据": "wastewater_aeration",
            "评审1号回转窑游离钙模型": "cement_rotary_kiln",
            "分析4号脱丁烷塔": "debutanizer_column",
            "处理5号加热炉板坯数据": "steel_reheating_furnace",
            "分析6号蒸馏塔数据": "distillation_column",
            "提取7号工业干燥器快速动态段并做MIMO辨识": "industrial_dryer",
            "分析8号高炉铁水硅含量数据": "blast_furnace",
        }
        for message, scenario_id in cases.items():
            with self.subTest(message=message):
                self.assertEqual(plan_skills(message)["entities"]["scenario_id"], scenario_id)
