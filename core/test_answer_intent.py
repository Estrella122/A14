from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.expert_qa import answer_expert_question
from core.skills.task_understanding import understand_task


class AnswerIntentTests(SimpleTestCase):
    def setUp(self):
        self.snapshot = {
            "run_id": "run_answer_intent",
            "artifacts": {"snr_csv": "03_cleaning/snr_estimates.csv"},
            "results": {"cleaning": {"snr": {
                "method": "robust_second_difference_white_noise_proxy",
                "threshold_db": 10,
                "calibrated": False,
                "assumptions": "局部平滑信号与加性白噪声",
            }}},
        }
        self.rows = [
            {"start_time": "2026-01-01 00:00", "end_time": "2026-01-01 00:30", "variable": "air_flow", "snr_db": 18.25},
            {"start_time": "2026-01-01 00:30", "end_time": "2026-01-01 01:00", "variable": "air_flow", "snr_db": 26.5},
        ]

    def test_eight_answer_intents_are_extracted(self):
        cases = {
            "信噪比多少？": "VALUE_QUERY", "信噪比怎么算？": "METHOD_QUERY",
            "信噪比的公式是什么？": "FORMULA_QUERY", "这个结果可靠吗？": "EVIDENCE_QUERY",
            "信噪比高说明什么？": "INTERPRETATION_QUERY", "哪个时间段信噪比最高？": "COMPARISON_QUERY",
            "为什么这么算？": "CAUSE_QUERY", "信噪比不足下一步怎么办？": "RECOMMENDATION_QUERY",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(understand_task(question)["answer_intent"]["kind"], expected)

    @patch("core.services.expert_qa._snr_rows")
    def test_six_snr_questions_use_distinct_evidence_grounded_answers(self, mocked_rows):
        mocked_rows.return_value = (self.rows, "snr_estimates.csv")
        cases = [
            ("信噪比多少？", None),
            ("信噪比怎么算？", None),
            ("为什么这么算？", ["snr"]),
            ("这个结果可靠吗？", ["snr"]),
            ("哪个时间段信噪比最高？", None),
            ("信噪比高说明什么？", None),
        ]
        results = [answer_expert_question(question, self.snapshot, topic_hints=hints) for question, hints in cases]
        self.assertEqual(len({item["answer"] for item in results}), 6)
        self.assertIn("26.50 dB", results[0]["answer"])
        self.assertIn("MAD(Δ²x)", results[1]["answer"])
        self.assertIn("二阶差分", results[2]["answer"])
        self.assertIn("calibrated=False", results[3]["answer"])
        self.assertIn("2026-01-01 00:30", results[4]["answer"])
        self.assertIn("不直接说明设备健康", results[5]["answer"])
        self.assertTrue(all(item["answer_intent"]["kind"] for item in results))
