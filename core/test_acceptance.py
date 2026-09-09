import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from acceptance.evaluate_real_routing import load_cases, predicted_stop
from core.skills.runtime import plan_skills


class AcceptanceHarnessTests(SimpleTestCase):
    def test_stage_prediction_matches_execution_scope(self):
        cases = {
            "清洗缺失值": "cleaning",
            "提取高信噪比动态段": "selection",
            "训练系统辨识模型": "modeling",
            "重新执行全流程并生成报告": "report",
            "不要训练，只解释残差": "evidence_only",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(predicted_stop(plan_skills(text)), expected)

    def test_group_cannot_cross_splits(self):
        rows = [
            {"id": "a", "session_group": "same", "text": "清洗", "labels": [], "mode": "execute", "stop_after": "cleaning", "critical_no_execute": False, "split": "train", "review_status": "approved"},
            {"id": "b", "session_group": "same", "text": "再清洗", "labels": [], "mode": "execute", "stop_after": "cleaning", "critical_no_execute": False, "split": "test", "review_status": "approved"},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cases.jsonl"
            path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "泄漏"):
                load_cases(path)
