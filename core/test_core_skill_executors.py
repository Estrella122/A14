import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, override_settings

from core.skills.core_executors import (ExperimentExecutor, OptimizationExecutor, ReportExecutor, ReviewExecutor,
                                        SimulationExecutor, StandardizationExecutor, SupervisionExecutor,
                                        VisualizationExecutor)
from core.skills.execution_plan import build_execution_plan
from core.skills.executor import EXECUTOR_DESCRIPTORS, executor_status, get_executor
from core.skills.runtime import plan_skills


class CoreExecutionPlanTests(SimpleTestCase):
    def plan(self, response, direct=(), outputs=("findings",), objective="task"):
        return build_execution_plan({"response_intents": list(response), "requested_outputs": list(outputs), "objective": objective}, list(direct))

    def test_cleaning_has_only_standardization_and_cleaning(self):
        self.assertEqual(self.plan(["cleaning"])["target_groups"], ["standardization", "cleaning"])

    def test_modeling_has_review_and_no_optimizer(self):
        groups = self.plan(["modeling"])["target_groups"]
        self.assertEqual(groups, ["standardization", "cleaning", "modeling", "review"])
        self.assertNotIn("optimization", groups)

    def test_optimization_does_not_implicitly_recompute_model(self):
        self.assertEqual(self.plan(["optimization"])["target_groups"], ["optimization"])

    def test_report_does_not_implicitly_recompute(self):
        groups = self.plan(["review"], ["expert_report_writer"], ["artifact"], "整理报告")["target_groups"]
        self.assertEqual(groups, ["report"])

    def test_standardization_is_single_node(self):
        self.assertEqual(self.plan(["standardization"])["target_groups"], ["standardization"])

    def test_segmentation_adds_data_dependencies(self):
        self.assertEqual(self.plan(["selection"])["target_groups"], ["standardization", "cleaning", "segmentation"])

    def test_catalog_cleaner_maps_to_cleaning(self):
        self.assertEqual(self.plan([], ["missing_anomaly_cleaner"])["target_groups"], ["standardization", "cleaning"])

    def test_catalog_model_maps_to_modeling(self):
        self.assertIn("modeling", self.plan([], ["system_identification_trainer"])["target_groups"])

    def test_empty_request_has_empty_dag(self):
        self.assertEqual(self.plan([])["steps"], [])

    def test_dependencies_are_explicit(self):
        nodes = {item["id"]: item for item in self.plan(["modeling"])["steps"]}
        self.assertEqual(nodes["modeling"]["dependencies"], ["cleaning"])

    def test_acceptance_phrases_build_expected_dags(self):
        cases = {
            "帮我检查这份数据并清洗缺失值。": ["standardization", "cleaning"],
            "用这份数据建一个预测模型，并告诉我是否优于基线。": ["standardization", "cleaning", "modeling", "review"],
            "直接优化运行参数。": ["optimization"],
            "给我生成这次分析报告。": ["report"],
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(plan_skills(message)["analysis"]["execution_plan"]["core"]["target_groups"], expected)

    def test_explicit_replanning_request_selects_supervisor_executor(self):
        groups = plan_skills("重新执行失败任务并自动重规划")["analysis"]["execution_plan"]["core"]["target_groups"]
        self.assertEqual(groups, ["supervision"])


class ExecutorRegistryTests(SimpleTestCase):
    def test_industrial_executor_available(self):
        self.assertEqual(executor_status("industrial-analysis"), "executable")

    def test_standardization_executor_available(self):
        self.assertIsNotNone(get_executor("standardization"))

    def test_cleaning_executor_available(self):
        self.assertIsNotNone(get_executor("cleaning"))

    def test_modeling_executor_available(self):
        self.assertIsNotNone(get_executor("modeling"))

    def test_review_executor_available(self):
        self.assertIsNotNone(get_executor("review"))

    def test_report_executor_available(self):
        self.assertIsNotNone(get_executor("report"))

    def test_segmentation_is_reader_only(self):
        self.assertEqual(EXECUTOR_DESCRIPTORS["segmentation"]["status"], "reader_only")

    def test_previously_unavailable_product_skills_are_executable(self):
        for executor in ("simulation", "visualization", "experiment", "supervision"):
            with self.subTest(executor=executor):
                self.assertEqual(executor_status(executor), "executable")
                self.assertIsNotNone(get_executor(executor))

    def test_unknown_executor_is_unavailable(self):
        self.assertEqual(executor_status("unknown"), "unavailable")


class ExecutorBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def test_optimization_blocks_without_all_inputs(self):
        result = OptimizationExecutor().execute("optimization", [], {}, {}, {"optimization_request": {}}, {})
        self.assertEqual(result["status"], "blocked")
        self.assertIn("synthetic", result["warnings"][0])

    def test_optimization_result_uses_uniform_schema(self):
        result = OptimizationExecutor().execute("optimization", [], {}, {}, {"optimization_request": {}}, {})
        required = {"status", "skill_id", "capabilities_executed", "facts", "findings", "hypotheses", "limitations", "metrics", "artifacts", "evidence", "warnings", "execution_trace", "duration_ms"}
        self.assertTrue(required.issubset(result))

    def test_optimization_never_calls_pipeline(self):
        with patch("core.services.pipeline.run_pipeline") as pipeline:
            OptimizationExecutor().execute("optimization", [], {}, {}, {"optimization_request": {}}, {})
        pipeline.assert_not_called()

    def test_report_consumes_snapshot_without_pipeline(self):
        snapshot = {"run_id": "r1", "results": {"cleaning": {"status": "done"}}}
        with patch("core.services.pipeline.run_pipeline") as pipeline:
            result = ReportExecutor().execute("report", ["expert_report_writer"], {}, {}, {"snapshot": snapshot}, {"output_dir": self.output, "results": []})
        pipeline.assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["artifacts"][0]).exists())

    def test_report_blocks_without_prior_results(self):
        result = ReportExecutor().execute("report", [], {}, {}, {"snapshot": {}}, {"output_dir": self.output, "results": []})
        self.assertEqual(result["status"], "blocked")

    def test_review_blocks_without_evidence(self):
        result = ReviewExecutor().execute("review", [], {}, {}, {"snapshot": {"results": {}}}, {"output_dir": self.output, "state": {}})
        self.assertEqual(result["status"], "blocked")

    def test_standardization_blocks_without_source(self):
        result = StandardizationExecutor().execute("standardization", [], {}, {}, {"snapshot": {}}, {"output_dir": self.output, "state": {}})
        self.assertEqual(result["status"], "blocked")

    def test_standardization_accepts_dataframe_reference(self):
        fake_report = {"scenario": {"scenario_id": "s"}, "mapping": {}, "issues": [], "dictionary": [], "artifacts": {}, "runtime_trace": {}}
        frame = pd.DataFrame({"x": [1, 2]})
        with patch("core.services.pipeline.run_standardization_stage", return_value=(frame, fake_report)) as service:
            result = StandardizationExecutor().execute("standardization", ["dataset_scenario_profiler"], {}, {}, {"snapshot": {"_dataframe": frame}}, {"output_dir": self.output, "state": {}})
        service.assert_called_once()
        self.assertEqual(result["status"], "success")

    def test_simulation_writes_reproducible_csv(self):
        context = {"output_dir": self.output}
        inputs = {"parameters": {"rows": 160, "seed": 7}}
        first = SimulationExecutor().execute("simulation", ["industrial_simulation_generator"], {}, {}, inputs, context)
        content = Path(first["artifacts"][0]).read_bytes()
        second = SimulationExecutor().execute("simulation", ["industrial_simulation_generator"], {}, {}, inputs, context)
        self.assertEqual(first["status"], "success")
        self.assertEqual(content, Path(second["artifacts"][0]).read_bytes())
        self.assertTrue(first["metrics"]["synthetic"])

    def test_visualization_uses_real_prediction_rows(self):
        snapshot = {"run_id": "r1", "results": {"modeling": {"prediction_preview": [
            {"y_true": 1.0, "y_pred": .9}, {"y_true": 2.0, "y_pred": 2.1},
        ]}}}
        result = VisualizationExecutor().execute("visualization", ["engineering_visualization_builder"], {}, {}, {"snapshot": snapshot}, {"output_dir": self.output})
        self.assertEqual(result["status"], "success")
        self.assertTrue(Path(result["artifacts"][0]).exists())

    def test_experiment_comparison_reads_registry(self):
        runs = [{"run_id": "a", "results": {"modeling": {"config": {"family": "ARX"}, "metrics": {"test": {"r2": .7, "rmse": 1, "mae": .8}}}}},
                {"run_id": "b", "results": {"modeling": {"config": {"family": "AR"}, "metrics": {"test": {"r2": .8, "rmse": .9, "mae": .7}}}}}]
        with patch("core.services.pipeline.list_runs", return_value=runs):
            result = ExperimentExecutor().execute("experiment", ["experiment_tracker_comparator"], {}, {}, {}, {"output_dir": self.output})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metrics"]["best_run_id"], "b")

    def test_supervisor_generates_replan_for_failed_executor(self):
        result = SupervisionExecutor().execute("supervision", ["execution_supervisor_replanner"], {}, {}, {"snapshot": {"run_id": "r1"}},
                                               {"output_dir": self.output, "results": [{"skill_id": "modeling", "status": "failed"}]})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metrics"]["decision"], "replan")
        self.assertTrue(result["metrics"]["automatic_replanning"])


class UploadResourceLimitTests(SimpleTestCase):
    @override_settings(PROCESSPILOT_MAX_CSV_COLUMNS=2, PROCESSPILOT_MAX_CSV_ROWS=10)
    def test_standardization_rejects_oversized_shape_before_agent_execution(self):
        from core.services.pipeline import PipelineError, _standardize
        with tempfile.TemporaryDirectory() as directory, patch("core.services.pipeline._read_csv", return_value=pd.DataFrame({"a": [1], "b": [2], "c": [3]})):
            with self.assertRaisesRegex(PipelineError, "列数"):
                _standardize(Path(directory) / "source.csv", Path(directory), "auto", "")
