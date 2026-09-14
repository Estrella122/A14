import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.test import SimpleTestCase, override_settings

from core.skills.artifacts import RuntimeArtifactResolver
from core.skills.core_executors import CleaningExecutor, OptimizationExecutor, SegmentationExecutor
from core.skills.execution_plan import build_execution_plan
from core.skills.executor import EXECUTOR_DESCRIPTORS
from core.skills.runtime import execute_skill_plan, plan_skills
from core.services.segmentation_service import run_segmentation_stage
from core.services.pipeline import PipelineError, run_optimization_stage


def training_frame(rows=180):
    index = pd.date_range("2026-01-01", periods=rows, freq="10s")
    x = np.sin(np.arange(rows) / 8) * 10 + np.arange(rows) * .03
    return pd.DataFrame({"input": x, "output": np.roll(x, 2) * .7 + np.sin(np.arange(rows) / 4)}, index=index)


DICTIONARY = [
    {"standard_name": "input", "data_type": "float", "role": "manipulated", "lower_bound": -100, "upper_bound": 100},
    {"standard_name": "output", "data_type": "float", "role": "controlled", "lower_bound": -100, "upper_bound": 100},
]


class SegmentationServiceTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def run_service(self, **kwargs):
        return run_segmentation_stage(training_frame(), DICTIONARY, self.output, upstream_run_id="clean-1", **kwargs)

    def test_independent_segmentation_succeeds(self):
        self.assertEqual(self.run_service()["status"], "success")

    def test_only_training_partition_is_read(self):
        evidence = self.run_service()["evidence"][0]
        self.assertEqual((evidence["validation_rows_read"], evidence["test_rows_read"]), (0, 0))

    def test_snr_artifact_exists(self):
        self.assertTrue(Path(self.run_service()["artifacts"]["snr_csv"]).exists())

    def test_segment_score_artifact_exists(self):
        self.assertTrue(Path(self.run_service()["artifacts"]["segment_scores_csv"]).exists())

    def test_modeling_dataset_artifact_exists(self):
        self.assertTrue(Path(self.run_service()["artifacts"]["modeling_csv"]).exists())

    def test_report_contains_provenance(self):
        report = self.run_service()
        self.assertEqual(report["provenance"]["upstream_cleaning_run"], "clean-1")
        self.assertEqual(report["provenance"]["selection_scope"], "training_only")

    def test_missing_frozen_split_blocks(self):
        self.assertEqual(self.run_service(split_version="")["status"], "blocked")

    def test_invalid_time_axis_blocks(self):
        result = run_segmentation_stage(training_frame().reset_index(drop=True), DICTIONARY, self.output)
        self.assertEqual(result["status"], "blocked")

    def test_insufficient_samples_blocks(self):
        result = run_segmentation_stage(training_frame(10), DICTIONARY, self.output)
        self.assertEqual(result["status"], "blocked")

    def test_invalid_window_step_blocks(self):
        self.assertEqual(self.run_service(window_length=30, step=31)["status"], "blocked")

    def test_missing_numeric_process_fields_blocks(self):
        frame = pd.DataFrame({"state": ["a"] * 40}, index=pd.date_range("2026-01-01", periods=40, freq="10s"))
        self.assertEqual(run_segmentation_stage(frame, [], self.output)["status"], "blocked")

    def test_executor_returns_uniform_result(self):
        state = {"train_data": training_frame(), "dictionary": DICTIONARY, "cleaning": {"split": {"protocol": "v1"}}}
        result = SegmentationExecutor().execute("segmentation", ["high_snr_dynamic_segment_extractor"], {}, {}, {"snapshot": {}}, {"state": state, "output_dir": self.output, "execution_id": "e1"})
        required = {"status", "skill_id", "capabilities_executed", "facts", "findings", "limitations", "metrics", "artifacts", "evidence", "warnings", "execution_trace", "duration_ms"}
        self.assertTrue(required.issubset(result))

    def test_executor_blocks_without_training_split(self):
        result = SegmentationExecutor().execute("segmentation", [], {}, {}, {"snapshot": {}}, {"state": {}, "output_dir": self.output})
        self.assertEqual(result["status"], "blocked")

    def test_cleaning_executor_never_runs_segmentation(self):
        report = {"_partitions": {"train": training_frame(60), "validation": training_frame(20), "test": training_frame(20)},
                  "split": {"protocol": "v1"}, "artifacts": {}, "logs": [], "overall_score": 90, "cleaned_row_count": 100}
        state = {"standardized_data": training_frame(100).reset_index(names="timestamp"), "dictionary": DICTIONARY,
                 "standardization": {"scenario": {"primary_output": "output"}}}
        with patch("core.services.pipeline.run_cleaning_stage", return_value=(training_frame(60), pd.DataFrame(), report)) as service:
            CleaningExecutor().execute("cleaning", [], {}, {}, {"snapshot": {}}, {"state": state, "output_dir": self.output, "target_groups": ["segmentation"]})
        self.assertFalse(service.call_args.kwargs["include_segmentation"])


class OptimizationExecutorTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        frame = training_frame(80)
        self.request = {
            "objective": "maximize validation score", "model_artifact": {"status": "ready"}, "frozen_split": {"protocol": "v1"},
            "training_data": frame.iloc[:48], "validation_data": frame.iloc[48:64], "test_data": frame.iloc[64:],
            "segments": [{"start_time": str(frame.index[0]), "end_time": str(frame.index[40]), "level": "优质动态段", "segment_score": 90}],
            "decision_variables": ["top_k", "max_lag"], "bounds": {"top_k": {"min": 2, "max": 20}, "max_lag": {"min": 10, "max": 600}},
            "constraints": {"min_r2": 0, "min_coverage": .05}, "search_space": {"top_k": [2, 20], "max_lag": [10, 600]},
            "optimization_policy": {"mode": "real_data", "test_policy": "winner_once"}, "field_dictionary": DICTIONARY,
            "primary_output": "output", "real_data": True,
        }
        self.fake_report = {"iterations": [{"status": "completed", "feasible": True}], "best_round": 1, "best_score": 88,
                            "best_parameters": {"top_k": 5, "max_lag": 60}, "best_metrics": {"r2": .8},
                            "objective": "maximize validation score", "validation_target_hash": "h", "artifacts": {"optimization_json": "result.json"}}
        self.fake_model = {"metrics": {"test": {"r2": .75}}}

    def execute(self, request=None):
        with patch("core.services.pipeline.run_optimization_stage", return_value=(self.fake_report, self.fake_model)) as service:
            result = OptimizationExecutor().execute("optimization", ["closed_loop_preprocessing_optimizer"], {}, {}, {"snapshot": {}, "optimization_request": self.request if request is None else request}, {"state": {}, "output_dir": self.output})
        return result, service

    def test_real_data_optimization_executes_service(self):
        result, service = self.execute(); service.assert_called_once(); self.assertEqual(result["status"], "success")

    def test_objective_missing_blocks(self):
        request = {**self.request, "objective": ""}; self.assertEqual(self.execute(request)[0]["status"], "blocked")

    def test_model_missing_blocks(self):
        request = {**self.request, "model_artifact": None}; self.assertEqual(self.execute(request)[0]["status"], "blocked")

    def test_bounds_missing_blocks(self):
        request = {**self.request, "bounds": {}}; self.assertEqual(self.execute(request)[0]["status"], "blocked")

    def test_constraints_missing_blocks(self):
        request = {**self.request, "constraints": {}}; self.assertEqual(self.execute(request)[0]["status"], "blocked")

    def test_real_data_missing_blocks(self):
        request = {**self.request, "real_data": None}; self.assertEqual(self.execute(request)[0]["status"], "blocked")

    def test_synthetic_mode_is_rejected(self):
        request = {**self.request, "optimization_policy": {"mode": "synthetic_benchmark"}}
        result, service = self.execute(request); service.assert_not_called(); self.assertEqual(result["status"], "blocked")

    def test_test_is_not_used_for_search(self):
        self.assertFalse(self.execute()[0]["evidence"][0]["test_used_for_search"])

    def test_test_is_evaluated_once(self):
        self.assertEqual(self.execute()[0]["evidence"][0]["test_evaluation_count"], 1)

    def test_synthetic_fallback_is_false(self):
        self.assertFalse(self.execute()[0]["evidence"][0]["synthetic_fallback"])

    def test_optimization_artifact_is_returned(self):
        self.assertEqual(self.execute()[0]["artifacts"][-1]["artifact_type"], "OPTIMIZATION_WINNER")

    def test_infeasible_result_is_partial(self):
        self.fake_report["iterations"][0]["feasible"] = False
        self.assertEqual(self.execute()[0]["status"], "partial")

    def test_out_of_bounds_candidate_is_recorded_infeasible(self):
        frame = training_frame(40)
        with self.assertRaises(PipelineError):
            run_optimization_stage(
                frame, pd.DataFrame(), DICTIONARY, {}, self.output, 60,
                primary_output="output", bounds={"top_k": {"min": 9, "max": 10}, "max_lag": {"min": 10, "max": 20}},
                optimization_policy={"candidates": [{"round": 1, "top_k": 5, "max_lag": 60, "label": "outside"}]},
            )
        report = (self.output / "05_optimization" / "optimization_report.json").read_text(encoding="utf-8")
        self.assertIn('"status": "infeasible"', report)

    def test_runtime_artifacts_do_not_invent_policy_contract(self):
        state = {
            "train_data": self.request["training_data"], "validation_data": self.request["validation_data"],
            "test_data": self.request["test_data"], "segments": pd.DataFrame(self.request["segments"]),
            "modeling": self.request["model_artifact"], "dictionary": DICTIONARY,
            "cleaning": {"split": self.request["frozen_split"]},
        }
        result = OptimizationExecutor().execute(
            "optimization", [], {}, {}, {"snapshot": {}, "optimization_request": None},
            {"state": state, "output_dir": self.output},
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("objective", result["limitations"][0])
        self.assertIn("bounds", result["limitations"][0])


class RuntimeClosureTests(SimpleTestCase):
    def test_all_eight_core_skills_are_executable(self):
        core = {"industrial-analysis", "standardization", "cleaning", "segmentation", "modeling", "optimization", "review", "report"}
        self.assertTrue(all(EXECUTOR_DESCRIPTORS[name]["status"] == "executable" for name in core))

    def test_dynamic_request_minimal_dag(self):
        task = {"response_intents": ["selection", "modeling"], "requested_outputs": ["findings"], "constraints": {"selection_only": True}}
        self.assertEqual(build_execution_plan(task, ["high_snr_dynamic_segment_extractor"])["target_groups"], ["standardization", "cleaning", "segmentation"])

    def test_existing_model_optimization_skips_upstream(self):
        task = {"response_intents": ["modeling", "optimization"], "requested_outputs": ["findings"], "constraints": {"use_existing_model": True}}
        self.assertEqual(build_execution_plan(task, ["closed_loop_preprocessing_optimizer"])["target_groups"], ["optimization"])

    def test_artifact_resolver_registers_provenance(self):
        state = {}; resolver = RuntimeArtifactResolver({"run_id": "r1"}, state)
        ref = resolver.register("segments_csv", self_path := Path("segments.csv"), "segmentation", "exec-1")
        self.assertEqual((Path(ref.path).name, ref.source_execution_id), (str(self_path), "exec-1"))

    def test_case_a_dynamic_segment_request_has_no_modeling(self):
        groups = plan_skills("找出这批数据里最适合建模的动态工况段。")["analysis"]["execution_plan"]["core"]["target_groups"]
        self.assertIn("high_snr_dynamic_segment_extractor", groups)
        self.assertNotIn("system_identification_trainer", groups)

    def test_case_b_existing_model_request_is_optimization_only(self):
        groups = plan_skills("用已有模型和这批数据优化运行参数。")["analysis"]["execution_plan"]["core"]["target_groups"]
        self.assertEqual(groups, ["optimization"])

    def test_case_d_rebuild_request_has_complete_ordered_dag(self):
        core = plan_skills("重新找最优动态段并重新建模，再优化。")["analysis"]["execution_plan"]["core"]
        self.assertEqual(core["target_groups"], ["standardization", "cleaning", "segmentation", "modeling", "optimization", "review"])
        dependencies = {step["id"]: step["dependencies"] for step in core["steps"]}
        self.assertEqual(dependencies["modeling"], ["segmentation"])
        self.assertEqual(dependencies["optimization"], ["modeling"])
        self.assertEqual(dependencies["review"], ["optimization"])

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_failed_dependency_blocks_downstream_executor(self):
        calls = []

        class StubExecutor:
            def __init__(self, status): self.status = status
            def execute(self, skill_id, *_args):
                calls.append(skill_id)
                return {"status": self.status, "skill_id": skill_id, "capabilities_executed": [], "facts": [],
                        "findings": [], "hypotheses": [], "limitations": [], "metrics": {}, "artifacts": [],
                        "evidence": [], "warnings": [], "execution_trace": [], "duration_ms": 0}

        plan = {"mode": "execute", "objective": "dependency propagation", "parameters": {}, "steps": [],
                "direct_skill_ids": [], "selected_count": 0, "analysis": {"task_understanding": {}, "analysis_plan": {},
                "execution_plan": {"core": {"target_groups": ["segmentation", "modeling"], "steps": [
                    {"id": "segmentation", "executor": "segmentation", "skill_ids": [], "dependencies": []},
                    {"id": "modeling", "executor": "modeling", "skill_ids": [], "dependencies": ["segmentation"]},
                ]}}}}
        with tempfile.TemporaryDirectory() as directory, \
                patch("core.skills.runtime.RUNS_DIR", Path(directory)), \
                patch("core.skills.runtime.get_executor", side_effect=lambda name: StubExecutor("blocked") if name == "segmentation" else StubExecutor("success")):
            result = execute_skill_plan(plan, {})
        self.assertEqual(calls, ["segmentation"])
        self.assertEqual([item["status"] for item in result["core_skill_execution_results"]], ["blocked", "blocked"])
