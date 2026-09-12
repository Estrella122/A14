from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, override_settings

from core.skills.capability_resolver import resolve_capabilities
from core.skills.context import build_data_context
from core.skills.runtime import execute_skill_plan, plan_skills
from core.skills.task_understanding import understand_task
from core.skills.skill_loader import load_skill_context
from core.services.agent_chat import chat


class AgentSkillRuntimeArchitectureTests(SimpleTestCase):
    def snapshot(self, frame=None, *, scene="thermal_power_boiler_long_tail", rows=120):
        frame = frame if frame is not None else pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="min"),
            "pressure": [1.0] * (rows - 1) + [8.0],
            "temperature": [100 + index * 0.1 for index in range(rows)],
        })
        mappings = [
            {"raw": "timestamp", "standard": "timestamp", "status": "matched", "role": "time", "data_type": "datetime", "confidence": .95},
            {"raw": "pressure", "standard": "pressure", "status": "matched", "role": "state", "data_type": "float", "confidence": .95},
            {"raw": "temperature", "standard": "temperature", "status": "matched", "role": "controlled", "data_type": "float", "confidence": .95},
        ]
        return {
            "run_id": "runtime_test", "_dataframe": frame, "runtime_trace": {"confidence": .94, "status": "confirmed"},
            "results": {"standardization": {"source_row_count": len(frame), "scenario": {"scenario_id": scene, "sampling_seconds": 60, "industry": "工业锅炉", "process_unit": "锅炉", "primary_output": "temperature"}, "mapping": {"mappings": mappings}, "data_decision": {"status": "ready"}}, "cleaning": {"overall_score": 90}},
            "artifacts": {"source_csv": "source.csv", "standardized_csv": "standardized.csv"},
        }

    def test_natural_language_builds_summarized_multi_intent_task_spec(self):
        task = understand_task("最近设备的数据老是忽高忽低，帮我看看是不是越来越不稳定。")
        self.assertNotEqual(task["objective"], "最近设备的数据老是忽高忽低，帮我看看是不是越来越不稳定。")
        self.assertIn("anomaly_detection", task["semantic_intents"])
        self.assertIn("process_stability", task["semantic_intents"])
        self.assertIn("ANOMALY_DETECTION", task["requested_capabilities"])
        self.assertIn("PROCESS_STABILITY", task["requested_capabilities"])

    def test_negation_removes_denied_intent(self):
        task = understand_task("检查异常，但不要分析趋势")
        self.assertIn("anomaly_detection", task["semantic_intents"])
        self.assertNotIn("trend_analysis", task["semantic_intents"])
        self.assertTrue(task["negations"])

    def test_explain_execute_and_multiturn(self):
        explanation = understand_task("解释一下异常检测是什么")
        execution = understand_task("执行异常检测")
        follow_up = understand_task("继续看看", {"previous_task_spec": execution})
        self.assertEqual("knowledge_explanation", explanation["task_kind"])
        self.assertEqual("execute", execution["execution_mode"])
        self.assertIn("anomaly_detection", follow_up["semantic_intents"])

    def test_explicit_scene_question_does_not_inherit_previous_anomaly_intent(self):
        previous = understand_task("哪些时间段值得重点检查")
        task = understand_task("这个数据是什么场景的工业数据", {"previous_task_spec": previous})
        self.assertEqual(["scene_identification"], task["semantic_intents"])
        self.assertEqual("识别当前数据的工业场景", task["objective"])
        self.assertEqual("standardization", task["response_intent"])

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_scene_and_colloquial_snr_questions_keep_their_direct_answers(self):
        snapshot = self.snapshot()
        snapshot["results"]["standardization"]["scenario"].update({
            "scenario_name": "热电锅炉长尾数据", "status": "confirmed", "confidence": .948,
        })
        with TemporaryDirectory() as directory, patch("core.services.agent_chat.get_run", return_value=snapshot), patch("core.skills.runtime.RUNS_DIR", Path(directory)):
            scene = chat("这个数据是什么场景的工业数据")
            snr = chat("它的噪声比是多少")
        self.assertIn("当前上传数据识别为【热电锅炉长尾数据】", scene["answer"])
        self.assertEqual("识别当前数据的工业场景", scene["skill_plan"]["analysis"]["task_understanding"]["objective"])
        self.assertEqual("snr", snr["expert_topic"])
        self.assertIn("信噪比", snr["answer"])

    def test_unknown_scene_blocks_specific_but_allows_generic(self):
        context = build_data_context(self.snapshot(scene=None)).public()
        resolution = resolve_capabilities(understand_task("检查异常和设备故障"), context)
        states = {item["candidate"]: item["status"] for item in resolution["candidates"]}
        self.assertEqual("selected", states["ANOMALY_DETECTION"])
        self.assertEqual("blocked", states["EQUIPMENT_HEALTH"])

    def test_blocked_and_skipped_are_distinct(self):
        context = build_data_context(self.snapshot(rows=10)).public()
        blocked = resolve_capabilities(understand_task("检查异常"), context)
        self.assertIn("ANOMALY_DETECTION", [item["candidate"] for item in blocked["candidates"] if item["status"] == "blocked"])
        ready = build_data_context(self.snapshot()).public()
        skipped = resolve_capabilities(understand_task("分析数据"), ready, lexical_candidates=[{"skill_id": "engineering_visualization_builder"}])
        self.assertIn("TREND_ANALYSIS", [item["candidate"] for item in skipped["candidates"] if item["status"] == "deferred"])

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_industrial_analysis_executes_and_writes_contract_in_temp_dir(self):
        snapshot = self.snapshot()
        plan = plan_skills("最近设备的数据老是忽高忽低，帮我看看是不是越来越不稳定。", snapshot=snapshot)
        with TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)):
            result = execute_skill_plan(plan, snapshot)
            self.assertGreater(result["summary"]["executed"], 0)
            contract = result["skill_execution_result"]
            for key in ("analysis_plan", "facts", "findings", "hypotheses", "limitations"):
                self.assertIn(key, contract)
            self.assertTrue(contract["cache"]["shared_numeric_matrix"])
            self.assertIn("capabilities_ms", contract["timing_trace"])
            self.assertTrue(Path(contract["artifact"]).is_file())

    @override_settings(AGENT_RUNTIME_MODE="legacy")
    def test_legacy_mode_preserves_evidence_reader(self):
        snapshot = self.snapshot()
        plan = plan_skills("检查异常", snapshot=snapshot)
        with TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)):
            result = execute_skill_plan(plan, snapshot)
        self.assertEqual(0, result["summary"]["executed"])
        self.assertIsNone(result["skill_execution_result"])

    @override_settings(AGENT_RUNTIME_MODE="hybrid")
    def test_hybrid_falls_back_when_standardized_data_is_unavailable(self):
        snapshot = self.snapshot()
        snapshot.pop("_dataframe")
        plan = plan_skills("检查异常", snapshot=snapshot)
        with TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)), patch("core.services.pipeline.resolve_artifact", side_effect=FileNotFoundError):
            result = execute_skill_plan(plan, snapshot)
        self.assertEqual(0, result["summary"]["executed"])
        self.assertIsNone(result["skill_execution_result"])

    @override_settings(AGENT_RUNTIME_MODE="skill_runtime")
    def test_skill_runtime_chat_does_not_use_pipeline_rerun(self):
        snapshot = self.snapshot()
        with TemporaryDirectory() as directory, patch("core.services.agent_chat.get_run", return_value=snapshot), patch("core.services.agent_chat.rerun_pipeline") as rerun, patch("core.skills.runtime.RUNS_DIR", Path(directory)):
            result = chat("执行异常检测")
        rerun.assert_not_called()
        self.assertGreater(result["skill_summary"]["executed"], 0)
        observability = result["runtime_observability"]
        self.assertTrue(observability["capabilities"])
        self.assertIn("steps", observability["execution_dag"])
        self.assertEqual(observability["skill_loading"]["selected_skill"], "industrial-analysis")
        self.assertIn("executor_results", observability)
        self.assertIn("artifacts", observability)

    def test_selected_skill_document_policy_controls_executor(self):
        source = Path(__file__).parent / "skills" / "industrial-analysis"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            copied = root / "industrial-analysis"
            shutil.copytree(source, copied)
            skill_path = copied / "SKILL.md"
            text = skill_path.read_text(encoding="utf-8").replace('"anomaly_zscore_threshold": 3.0', '"anomaly_zscore_threshold": 9.0')
            skill_path.write_text(text, encoding="utf-8")
            loaded = load_skill_context("检查异常", (root,), scene="test", selected_capabilities=["ANOMALY_DETECTION"], selected_skill_name="industrial-analysis")
        self.assertEqual(9.0, loaded["manifest"]["execution_policy"]["anomaly_zscore_threshold"])

    @override_settings(AGENT_RUNTIME_MODE="hybrid")
    def test_manifest_execution_policy_changes_executor_behavior(self):
        snapshot = self.snapshot()
        plan = plan_skills("帮我找异常", snapshot=snapshot)
        with TemporaryDirectory() as directory, patch("core.skills.runtime.RUNS_DIR", Path(directory)):
            plan["analysis"]["skill_runtime"]["manifest"]["execution_policy"]["anomaly_zscore_threshold"] = 1.0
            low = execute_skill_plan(plan, snapshot)["skill_execution_result"]
            plan["analysis"]["skill_runtime"]["manifest"]["execution_policy"]["anomaly_zscore_threshold"] = 10.0
            high = execute_skill_plan(plan, snapshot)["skill_execution_result"]
        def count(result):
            return next(item["metrics"]["anomaly_count"] for item in result["capability_executions"] if item["capability_id"] == "ANOMALY_DETECTION")
        self.assertGreater(count(low), count(high))
