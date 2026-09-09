"""Regression contracts for routing boundaries and real execution scope."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from django.test import SimpleTestCase
from . import tests as original_tests
from .skills.runtime import plan_skills, _with_dependencies, execute_skill_plan
from .skills.catalog import SKILL_MAP
from .services.agent_chat import chat
from .services import pipeline


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
        with patch('core.services.agent_chat.get_run',return_value=snapshot),patch('core.services.agent_chat.rerun_pipeline') as rerun:
            result=chat('不要训练模型，只导出已有报告')
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
                result=chat(message)
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
            result=chat('估计输入输出时滞')
        rerun.assert_not_called()
        self.assertIn('尚无独立算法执行接口',result['action_note'])

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
            result=chat('训练系统辨识模型')
        self.assertEqual(rerun.call_args.kwargs['stop_after'],'modeling')
        self.assertEqual(result['execution_scope'],'modeling')
