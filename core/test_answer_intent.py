from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.expert_qa import answer_expert_question
from core.skills.task_understanding import understand_task
from core.services.agent_chat import _explicit_execution_authorized


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

    def test_negated_snr_does_not_override_field_review_question(self):
        snapshot = {
            "run_id": "run_vapor_review",
            "results": {
                "standardization": {
                    "scenario": {"scenario_name": "蒸气压力软测量实验", "primary_output": "vapour_pressure_kpa"},
                    "mapping": {"required_coverage": 0.714, "missing_required": ["timestamp"], "mappings": []},
                    "detection": {"selected": {"review_fields": 1}},
                    "data_decision": {"status": "review", "scenario_confidence": 0.928, "reasons": ["缺少必需字段"]},
                    "schema_validation": {"failure_count": 2},
                }
            },
        }
        result = answer_expert_question(
            "为什么字段标准化需要人工复核？列出必需字段和字段覆盖率，不要讨论SNR。",
            snapshot,
        )
        self.assertEqual(result["topics"], ["standardization"])
        self.assertIn("71.4%", result["answer"])
        self.assertNotIn("二阶差分", result["answer"])

    def test_missing_rate_question_returns_actual_cleaning_evidence(self):
        snapshot = {
            "run_id": "run_missing",
            "results": {
                "cleaning": {
                    "overall_score": 88,
                    "missing_rate": {"primary_water_flow": 0.0006},
                    "logs": ["primary_water_flow 缺失率 0.06%，处理策略：仅向前填充最多6个采样点；不读取未来值。"],
                }
            },
        }
        result = answer_expert_question("哪个字段缺失，缺失率是多少，是否读取未来值？", snapshot)
        self.assertEqual(result["topics"], ["cleaning", "leakage"])
        self.assertIn("primary_water_flow=0.06%", result["answer"])
        self.assertIn("不读取未来值", result["answer"])

    def test_professional_question_does_not_authorize_pipeline_rerun(self):
        self.assertFalse(_explicit_execution_authorized("锅炉数据的时滞是怎么处理的？"))
        self.assertFalse(_explicit_execution_authorized("最终用了哪些外部输入？"))
        self.assertTrue(_explicit_execution_authorized("请从当前数据中重新筛选高信噪比动态段"))
