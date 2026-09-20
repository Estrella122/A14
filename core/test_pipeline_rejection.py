import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from integrations.standardization.standard_agent import StandardizationAgent


class StandardizationDatetimeTests(SimpleTestCase):
    def test_day_first_datetime_is_used_when_it_parses_more_rows(self):
        source = pd.Series(["13/01/2018 00:15", "31/12/2018 23:45"])

        converted, errors = StandardizationAgent._coerce_type(source, "datetime")

        self.assertEqual(errors, 0)
        self.assertEqual(converted.dt.day.tolist(), [13, 31])
        self.assertEqual(converted.dt.month.tolist(), [1, 12])


class RejectedUploadTests(TestCase):
    def test_rejected_standardization_returns_review_snapshot_without_running_downstream(self):
        rows = ["date,value"]
        rows.extend(f"2026-01-01 00:{index % 60:02d}:00,{index}" for index in range(200))
        upload = SimpleUploadedFile(
            "unsupported.csv",
            ("\n".join(rows) + "\n").encode("utf-8"),
            content_type="text/csv",
        )

        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder)
            with (
                override_settings(PROCESSPILOT_RUNTIME_ROOT=folder),
                patch("core.services.pipeline.RUNS_DIR", runtime),
                patch("core.services.pipeline.LATEST_PATH", runtime / "latest.json"),
            ):
                response = self.client.post(
                    "/api/pipeline/runs/",
                    {"file": upload, "scenario_id": "auto", "instruction": "未知工业数据"},
                )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertTrue(payload["ok"])
        snapshot = payload["data"]
        self.assertEqual(snapshot["status"], "needs_review")
        self.assertEqual(snapshot["current_stage"], "standardization")
        self.assertEqual(snapshot["execution_scope"]["reason"], "data_decision_reject")
        self.assertNotIn("cleaning", snapshot["results"])
        self.assertTrue(snapshot["review_required"]["reasons"])
        self.assertEqual(snapshot["results"]["standardization"]["source_row_count"], 200)
        self.assertEqual(snapshot["results"]["standardization"]["source_column_count"], 2)
        downstream = [stage for stage in snapshot["stages"] if stage["key"] != "standardization"]
        self.assertTrue(all(stage["status"] == "skipped" for stage in downstream))
