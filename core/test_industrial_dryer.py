from pathlib import Path

import pandas as pd
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

    def test_acceptance_dataset_has_exact_dryer_sampling_contract(self):
        path = Path(__file__).resolve().parents[1] / "演示数据" / "工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv"
        frame = pd.read_csv(path, encoding="utf-8-sig")
        timestamps = pd.to_datetime(frame["采集时间"])
        self.assertEqual(len(frame), 867)
        self.assertTrue(timestamps.diff().dropna().eq(pd.Timedelta(seconds=10)).all())
        self.assertEqual(list(frame.columns), ["采集时间", "入口热风温度", "热风流量", "给料量", "产品水分", "物料出口温度", "尾气湿度"])
