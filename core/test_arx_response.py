import sys
from pathlib import Path

from django.test import SimpleTestCase


IDENTIFICATION_DIR = Path(__file__).resolve().parents[1] / "integrations" / "identification"
if str(IDENTIFICATION_DIR) not in sys.path:
    sys.path.insert(0, str(IDENTIFICATION_DIR))

from validated_modeling import arx_response_analysis


class ArxResponseAnalysisTests(SimpleTestCase):
    def test_response_preserves_each_input_delay_and_gain(self):
        state = {
            "output": "product_moisture", "seconds": 10, "order": 1,
            "inputs": ["hot_air_temperature", "wet_feed_rate"],
            "delays": {"hot_air_temperature": 2, "wet_feed_rate": 1},
            "coef": [5.0, 0.5, -0.2, 0.3],
        }
        result = arx_response_analysis(state, horizon=8, frequency_points=5)
        channels = {row["input"]: row for row in result["channels"]}

        self.assertEqual(channels["hot_air_temperature"]["delay_seconds"], 20)
        self.assertEqual(channels["hot_air_temperature"]["step"][0]["value"], 0)
        self.assertEqual(channels["hot_air_temperature"]["step"][1]["value"], 0)
        self.assertAlmostEqual(channels["hot_air_temperature"]["step"][2]["value"], -0.2)
        self.assertAlmostEqual(channels["hot_air_temperature"]["dc_gain"], -0.4)
        self.assertAlmostEqual(channels["wet_feed_rate"]["dc_gain"], 0.6)

    def test_ar_model_does_not_claim_external_response_channels(self):
        state = {"output": "product_moisture", "seconds": 10, "order": 1, "inputs": [], "delays": {}, "coef": [5.0, 0.5]}
        result = arx_response_analysis(state, horizon=8, frequency_points=5)
        self.assertEqual(result["channels"], [])
