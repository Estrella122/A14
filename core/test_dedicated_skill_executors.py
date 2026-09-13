from __future__ import annotations

import math
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from django.test import SimpleTestCase

from core.skills.core_executors import ModelDiagnosticsCapabilityExecutor, TimeDelayCapabilityExecutor
from core.skills.executor import get_executor


class DedicatedSkillExecutorTests(SimpleTestCase):
    def test_six_key_skill_ids_resolve_to_dedicated_executor_entries(self):
        skill_ids = {
            "missing_anomaly_cleaner", "high_snr_dynamic_segment_extractor", "time_delay_estimator_compensator",
            "system_identification_trainer", "model_diagnostics_evaluator", "closed_loop_preprocessing_optimizer",
        }
        self.assertTrue(all(get_executor(skill_id) is not None for skill_id in skill_ids))

    def test_time_delay_executor_runs_without_model_training(self):
        rows = 120
        signal = [math.sin(index / 8) + index / 200 for index in range(rows)]
        output = [0.0] * 3 + signal[:-3]
        frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=rows, freq="10s"), "air_flow": signal, "temperature": output})
        dictionary = [
            {"standard_name": "air_flow", "role": "manipulated"},
            {"standard_name": "temperature", "role": "controlled"},
        ]
        state = {"modeling_data": frame.set_index("timestamp"), "dictionary": dictionary,
                 "standardization": {"scenario": {"primary_output": "temperature", "sampling_seconds": 10}}}
        with TemporaryDirectory() as directory:
            result = TimeDelayCapabilityExecutor().execute(
                "modeling", ["time_delay_estimator_compensator"], {}, {}, {"snapshot": {"run_id": "delay"}, "parameters": {"max_lag": 12}},
                {"state": state, "output_dir": Path(directory), "execution_id": "delay-test"},
            )
        self.assertEqual("success", result["status"])
        self.assertEqual("independent_algorithm", result["implementation_scope"])
        self.assertEqual(3, result["metrics"]["delays"][0]["delay_samples"])
        self.assertEqual(2, len(result["artifacts"]))
        self.assertNotIn("system_identification_trainer", result["capabilities_executed"])

    def test_diagnostics_executor_never_retrains_model(self):
        modeling = {
            "config": {"family": "ARX"},
            "metrics": {"test": {"r2": 0.8, "rmse": 0.2, "mae": 0.1}},
            "diagnostics": {"stable_ar_poles": True, "test": {
                "rmse_improvement_over_persistence_pct": 12.0,
                "residual": {"acf_max_abs": 0.08},
            }},
        }
        with TemporaryDirectory() as directory:
            result = ModelDiagnosticsCapabilityExecutor().execute(
                "modeling", ["model_diagnostics_evaluator"], {}, {}, {"snapshot": {"run_id": "diagnostics", "results": {"modeling": modeling}}},
                {"state": {}, "output_dir": Path(directory), "execution_id": "diagnostics-test"},
            )
        self.assertEqual("success", result["status"])
        self.assertFalse(result["provenance"]["model_retrained"])
        self.assertEqual(0, result["provenance"]["test_evaluation_count_added"])
        self.assertEqual("independent_gate_evaluator", result["implementation_scope"])
