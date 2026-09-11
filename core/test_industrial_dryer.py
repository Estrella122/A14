from django.test import SimpleTestCase

from integrations.standardization.standard_agent.engine import StandardizationAgent
from integrations.standardization.standard_agent.repository import ScenarioRepository


class IndustrialDryerScenarioTests(SimpleTestCase):
    columns = [
        "TIME", "入口热风温度", "热风流量", "给料量",
        "产品水分", "物料出口温度", "尾气湿度",
    ]

    def test_dryer_contract_is_three_inputs_three_outputs(self):
        template = ScenarioRepository().get("industrial_dryer")
        inputs = [field for field in template.fields if field.role == "manipulated"]
        outputs = [field for field in template.fields if field.role == "controlled"]
        self.assertEqual(len(inputs), 3)
        self.assertEqual(len(outputs), 3)
        self.assertEqual(template.config["sampling_seconds"], 10)
        self.assertEqual(template.config["model_outputs"], [field.standard_name for field in outputs])

    def test_dryer_aliases_map_all_required_fields(self):
        result = StandardizationAgent().map_columns(self.columns, "industrial_dryer")
        self.assertEqual(result["required_coverage"], 1.0)
