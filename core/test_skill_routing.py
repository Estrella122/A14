"""Regression contracts for routing boundaries and real execution scope."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from django.test import SimpleTestCase, override_settings
from . import tests as original_tests
from .skills.runtime import plan_skills, _with_dependencies, execute_skill_plan
from .skills.catalog import SKILL_MAP
from .skills.capability_resolver import resolve_capabilities, understand_task
from .skills.context import build_data_context
from .services.agent_chat import chat
from .services import pipeline


@override_settings(SKILL_MANIFEST_MODE="legacy")
class TrainedRoutingTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.logs=patch('core.skills.runtime.RUNS_DIR',Path(self.temp.name)/'skill-runs')
        self.logs.start();self.addCleanup(self.logs.stop)

    def snapshot(self):return original_tests.AgentChatTests().snapshot()

    def test_download_does_not_select_report_writer_or_train(self):
        p=plan_skills('不要训练模型，只导出已有报告')
        self.assertEqual(p['direct_skill_ids'],['final_artifact_exporter'])
        self.assertFalse(p['analysis']['needs_clarification'])
        self.assertNotIn('system_identification_trainer',{s['skill_id'] for s in p['steps']})
        snapshot=self.snapshot();snapshot['artifacts']={'analysis_report_md':'report.md'}
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory, patch('core.services.pipeline.RUNS_DIR', Path(directory)), patch('core.services.agent_chat.get_run',return_value=snapshot),patch('core.services.agent_chat.rerun_pipeline') as rerun:
            path = Path(directory) / snapshot['run_id'] / 'report.md'
            path.parent.mkdir(); path.write_text('frozen existing report')
            result=chat('不要训练模型，只导出已有报告', run_id=self.snapshot()['run_id'])
            path.unlink()
            missing=chat('不要训练模型，只导出已有报告', run_id=self.snapshot()['run_id'])
            self.assertEqual(missing['deliverables'], [])
        rerun.assert_not_called()
        self.assertFalse(result['executed'])
        self.assertEqual(result['deliverables'][0]['key'],'analysis_report_md')

    def test_snr_does_not_request_dynamic_segment_extraction(self):
        p=plan_skills('只检查信噪比，不要提取动态段')
        self.assertEqual(p['direct_skill_ids'],['signal_noise_ratio_estimator'])
        self.assertEqual(p['mode'],'analyze')

    def test_compound_retains_distinct_requested_targets(self):
        p=plan_skills('先清洗缺失值，再训练模型')
        self.assertEqual(set(p['direct_skill_ids']),{'missing_anomaly_cleaner','system_identification_trainer'})
        self.assertEqual(p['mode'],'execute')
        positions={s['skill_id']:s['order'] for s in p['steps']}
        for s in p['steps']:
            for dependency in SKILL_MAP[s['skill_id']].depends_on:
                self.assertLess(positions[dependency],s['order'])

    def test_negation_and_hypothetical_never_authorize_rerun(self):
        messages=['不要重新执行，只解释残差','如果重新运行会发生什么','假如重新执行全流程，结果会改变吗','按钮写着“重新执行”，这句话是什么意思','这次请先不要重新执行','模型不能重新运行','重新运行会不会变差','系统提示重新执行','请重新执行吗']
        for message in messages:
            with self.subTest(message=message),patch('core.services.agent_chat.get_run',return_value=self.snapshot()),patch('core.services.agent_chat.rerun_pipeline') as rerun:
                result=chat(message, run_id=self.snapshot()['run_id'])
                rerun.assert_not_called()
                self.assertFalse(result['executed'])

    def test_unknown_request_does_not_default_to_report(self):
        for message in ['帮我订机票','随便弄一下','明天会下雨吗']:
            p=plan_skills(message)
            self.assertEqual(p['direct_skill_ids'],[])
            self.assertTrue(p['analysis']['needs_clarification'])
            self.assertEqual(p['mode'],'analyze')

    def test_missing_model_fails_closed(self):
        with patch('core.skills.routing.predict',side_effect=FileNotFoundError('model missing')):
            p=plan_skills('训练系统辨识模型')
        self.assertEqual(p['direct_skill_ids'],[])
        self.assertEqual(p['mode'],'analyze')
        self.assertEqual(p['analysis']['routing_source'],'model_unavailable')

    def test_dependency_cycle_and_missing_target_rejected(self):
        from dataclasses import replace
        sid='industrial_intent_parser'
        with patch.dict(SKILL_MAP,{sid:replace(SKILL_MAP[sid],depends_on=(sid,))}):
            with self.assertRaisesRegex(ValueError,'环'):_with_dependencies({sid})
        with self.assertRaisesRegex(ValueError,'未知'):_with_dependencies({'nonexistent'})

    def test_conflicting_dependency_is_not_silently_executed(self):
        p=plan_skills('不要清洗缺失值，训练系统辨识模型')
        self.assertTrue(p['analysis']['needs_clarification'])
        self.assertEqual(p['mode'],'analyze')
        self.assertIn('missing_anomaly_cleaner',p['analysis']['dependency_conflicts'])

    def test_evidence_read_is_never_labeled_algorithm_execution(self):
        p=plan_skills('训练系统辨识模型')
        result=execute_skill_plan(p,self.snapshot())
        self.assertNotIn('executed',{e['activity'] for e in result['executions']})

    def test_pure_lag_request_does_not_trigger_model_training(self):
        with patch('core.services.agent_chat.get_run',return_value=self.snapshot()),patch('core.services.agent_chat.rerun_pipeline') as rerun:
            result=chat('估计输入输出时滞', run_id=self.snapshot()['run_id'])
        rerun.assert_not_called()
        lag=next(item for item in result['skill_executions'] if item['skill_id']=='time_delay_estimator_compensator')
        self.assertEqual(lag['executor'],'time_delay_estimator_compensator')
        self.assertEqual(lag['execution_state'],'blocked')
        self.assertNotIn('system_identification_trainer',{item['skill_id'] for item in result['skill_executions']})

    def test_cleaning_stops_before_model_and_optimizer(self):
        folder=Path(self.temp.name);source=folder/'source.csv';source.write_text('x\n1\n')
        standard={'dictionary':[],'artifacts':{'standardized_csv':'std.csv'}}
        frame=pd.DataFrame({'x':[1,2,3]})
        cleaned={'overall_score':90,'artifacts':{},'selected_segment_count':1,'segments_preview':[]}
        with patch.object(pipeline,'RUNS_DIR',folder/'runs'),patch.object(pipeline,'LATEST_PATH',folder/'latest.json'),patch.object(pipeline,'_standardize',return_value=(frame,standard)),patch.object(pipeline,'_read_csv',return_value=frame),patch.object(pipeline,'_clean',return_value=(frame,frame,cleaned)),patch.object(pipeline,'_model') as model,patch.object(pipeline,'_optimize_real_data') as optimize:
            result=pipeline.run_pipeline(source,'source.csv',stop_after='cleaning')
        model.assert_not_called();optimize.assert_not_called()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['results'].keys(),{'standardization','cleaning'})
        self.assertEqual(next(s for s in result['stages'] if s['key']=='modeling')['status'],'skipped')

    def test_model_training_does_not_trigger_optimizer(self):
        with patch('core.services.agent_chat.get_run',return_value=self.snapshot()),patch('core.services.agent_chat.rerun_pipeline',return_value=self.snapshot()) as rerun:
            result=chat('训练系统辨识模型', run_id=self.snapshot()['run_id'])
        rerun.assert_not_called()
        self.assertEqual(result['skill_plan']['analysis']['execution_plan']['core']['target_groups'],['standardization','cleaning','modeling','review'])
        self.assertNotIn('optimization',result['execution_scope'])


class ContextAwareCapabilityResolutionTests(SimpleTestCase):
    def context_snapshot(self, *, numeric=True, timestamp=True, rows=200, mapping_confidence=.95):
        mappings = []
        if timestamp:
            mappings.append({"raw": "time", "standard": "timestamp", "status": "matched", "role": "time", "data_type": "datetime", "confidence": mapping_confidence})
        if numeric:
            mappings.extend([
                {"raw": "x", "standard": "pressure", "status": "matched", "role": "state", "data_type": "float", "confidence": mapping_confidence},
                {"raw": "y", "standard": "temperature", "status": "matched", "role": "controlled", "data_type": "float", "confidence": mapping_confidence},
            ])
        return {"run_id": "context_run", "project_scene": "debutanizer_column", "runtime_trace": {"confidence": .94, "status": "confirmed"}, "results": {"standardization": {"source_row_count": rows, "scenario": {"scenario_id": "thermal_power_boiler_long_tail", "industry": "工业锅炉", "process_unit": "锅炉", "sampling_seconds": 5}, "mapping": {"mappings": mappings}, "data_decision": {"status": "ready"}}, "cleaning": {"overall_score": 88}}, "artifacts": {"source_csv": "01_input/source.csv", "standardized_csv": "02_standardization/standardized.csv"}}

    def test_five_anomaly_paraphrases_share_core_capabilities(self):
        messages = ["帮我找异常", "这批数据有没有不正常的地方", "看看哪里和正常运行不一样", "哪些时间段值得重点检查", "这批数据波动是不是有问题"]
        core = {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "ANOMALY_DETECTION"}
        for message in messages:
            with self.subTest(message=message):
                plan = plan_skills(message, snapshot=self.context_snapshot())
                self.assertTrue(core.issubset(plan["analysis"]["capability_resolution"]["selected"]))

    def test_knowledge_explanations_load_docs_without_analysis_or_execution(self):
        cases = {"异常检测是什么意思？": "ANOMALY_DETECTION", "介绍一下趋势分析": "TREND_ANALYSIS", "相关性和因果有什么区别": "CORRELATION_ANALYSIS"}
        for message, capability in cases.items():
            with self.subTest(message=message):
                plan = plan_skills(message, snapshot=self.context_snapshot())
                self.assertEqual("knowledge_explanation", plan["analysis"]["task_understanding"]["task_kind"])
                self.assertEqual([], plan["analysis"]["capability_resolution"]["selected"])
                self.assertIn(capability, plan["analysis"]["capability_resolution"]["documentation"])
                self.assertEqual("analyze", plan["mode"])

    def test_anomaly_preconditions_block_missing_numeric_time_or_samples(self):
        for kwargs, missing in (({"numeric": False}, "numeric_fields"), ({"timestamp": False}, "ordered_data"), ({"rows": 10}, "sufficient_samples")):
            context = build_data_context(self.context_snapshot(**kwargs)).public()
            resolved = resolve_capabilities(understand_task("帮我找异常"), context)
            anomaly = next(item for item in resolved["candidates"] if item["candidate"] == "ANOMALY_DETECTION")
            self.assertEqual("blocked", anomaly["status"])
            self.assertIn(missing, anomaly["reason"])

    def test_data_context_keeps_project_and_detected_scene_separate(self):
        context = build_data_context(self.context_snapshot()).public()
        self.assertEqual("debutanizer_column", context["project_context_scene"])
        self.assertEqual("thermal_power_boiler_long_tail", context["detected_scene"])
        self.assertEqual(2, context["numeric_field_count"])
        self.assertTrue(context["regular_time_axis"])
        self.assertEqual(200, context["row_count"])
        self.assertEqual(3, context["column_count"])
        self.assertEqual(2, context["numeric_column_count"])
        self.assertEqual(context["estimated_memory"], context["estimated_memory_bytes"])
        self.assertGreater(context["estimated_memory_bytes"], 0)

    def test_resolution_exposes_cost_budget_and_planning_timing(self):
        plan = plan_skills("这批数据波动是不是有问题", snapshot=self.context_snapshot())
        resolution = plan["analysis"]["capability_resolution"]
        self.assertEqual(1, resolution["analysis_budget"]["max_high_cost_capabilities"])
        self.assertTrue(all(item["estimated_cost"] in {"LOW", "MEDIUM", "HIGH"} for item in resolution["candidates"]))
        self.assertIn("task_understanding_ms", plan["analysis"]["timing_trace"])
        self.assertIn("total_ms", plan["analysis"]["timing_trace"])

    def test_explicit_full_deep_analysis_raises_budget(self):
        plan = plan_skills("请做完整深度分析，找异常并检查过程稳定性", snapshot=self.context_snapshot())
        budget = plan["analysis"]["capability_resolution"]["analysis_budget"]
        self.assertEqual("extended", budget["mode"])
        self.assertGreater(budget["max_high_cost_capabilities"], 1)

    def test_mapping_quality_and_dependency_readiness_are_scored(self):
        low = build_data_context(self.context_snapshot(mapping_confidence=.4)).public()
        resolved = resolve_capabilities(understand_task("分析产品质量"), low)
        quality = next(item for item in resolved["candidates"] if item["candidate"] == "QUALITY_ANALYSIS")
        self.assertEqual("blocked", quality["status"])
        no_artifacts = build_data_context(self.context_snapshot()).public()
        no_artifacts["available_artifacts"] = []
        resolved = resolve_capabilities(understand_task("帮我找异常"), no_artifacts)
        anomaly = next(item for item in resolved["candidates"] if item["candidate"] == "ANOMALY_DETECTION")
        self.assertEqual(.7, anomaly["dependency_readiness_score"])

    def test_non_industrial_task_does_not_load_industrial_skill(self):
        plan = plan_skills("修改登录页面按钮颜色", snapshot=self.context_snapshot())
        self.assertIsNone(plan["analysis"]["skill_runtime"]["selected_skill"])

    def test_object_prefixed_visualization_and_download_commands_route_precisely(self):
        chart = plan_skills("把闭环寻优每轮得分可视化")
        download = plan_skills("把已经做好的报告下载给我")
        self.assertEqual(["engineering_visualization_builder"], chart["direct_skill_ids"])
        self.assertEqual(["final_artifact_exporter"], download["direct_skill_ids"])

    def test_unit_circle_is_not_treated_as_field_unit(self):
        plan = plan_skills("验证模型极点是否落在单位圆以内")
        self.assertNotIn("semantic_field_unit_standardizer", plan["direct_skill_ids"])
