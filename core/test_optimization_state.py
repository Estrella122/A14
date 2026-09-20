"""Failure injection around the real search loop and its durable read protocol."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from django.test import TestCase
from core.services import pipeline
from core.services.optimization_state import recover_snapshot
from core.models import PipelineRunRecord, RuntimeJob


class SearchEvidenceTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.run = self.root/'case1'; self.run.mkdir()
        self.frame = pd.DataFrame({'output': range(100)}, index=pd.date_range('2026-01-01', periods=100, freq='h'))
        self.segments = pd.DataFrame([{'segment_id':'s1', 'level':'优质动态段'}])
        self.snapshot = {'run_id':'case1','status':'running','artifacts':{},'results':{},'stages':[]}
        self.progress = []
        for name, value in [('RUNS_DIR',self.root),('LATEST_PATH',self.root/'latest.json')]:
            context=patch.object(pipeline,name,value);context.start();self.addCleanup(context.stop)
        for target, value in [('core.services.pipeline._select_modeling_rows', self.frame.iloc[:30]), ('core.services.segmentation_service.select_modeling_windows',self.segments)]:
            context=patch(target,return_value=value);context.start();self.addCleanup(context.stop)
        context=patch('core.services.pipeline._model',side_effect=self.model);self.model_mock=context.start();self.addCleanup(context.stop)
        self.call_count=0

    def model(self, data, dictionary, root, lag, **kwargs):
        self.call_count+=1
        out=kwargs['output_dir'];out.mkdir(parents=True,exist_ok=True)
        return {'config':{'max_lag':lag,'family':'AR'},'metrics':{'validation':{'r2':.9,'rmse':.1,'mae':.08,'n_samples':20}},
                'diagnostics':{'evaluation_target_hash':'frozen'},'modeling_path':str(kwargs['modeling_path'].relative_to(root)),
                'output_dir':str(out.relative_to(root)),'output_col':'output','artifacts':{'fitted_state_json':str(out.relative_to(root))+'/state.json'},'fitted_inputs':[]}

    def progress_saved(self, report):
        # Callback is reached only after the report has been atomically replaced.
        disk=json.loads((self.run/'05_optimization/optimization_report.json').read_text())
        self.assertEqual(disk['candidate_counts'],report['candidate_counts'])
        self.snapshot['results']['optimization']=report
        pipeline._write_json(self.run/'snapshot.json',self.snapshot)
        self.progress.append(report)

    def search(self, **kwargs):
        constraints=kwargs.pop('constraints',{'min_r2':0,'min_coverage':.8})
        return pipeline._optimize_real_data(self.frame,self.segments,[],{},self.run,12,primary_output='output',constraints=constraints,on_progress=self.progress_saved,**kwargs)

    def assert_consistent(self):
        disk=json.loads((self.run/'snapshot.json').read_text())['results']['optimization']
        db=PipelineRunRecord.objects.get(run_id='case1').snapshot['results']['optimization']
        api=self.client.get('/api/pipeline/runs/case1/').json()['data']['results']['optimization']
        for result in (db,api,self.progress[-1]):
            self.assertEqual(result['candidate_counts'],disk['candidate_counts'])
            self.assertEqual(result['optimization_outcome'],disk['optimization_outcome'])
        self.assertEqual(disk['progress_events'][-1]['candidate_counts'],disk['candidate_counts'])
        return disk

    def test_no_feasible_retains_every_attempt_without_test_or_winner(self):
        with patch.dict('sys.modules', {'validated_modeling':__import__('unittest.mock',fromlist=['Mock']).Mock()}) as _:
            with self.assertRaises(pipeline.OptimizationStopped):self.search()
        report=self.assert_consistent()
        self.assertEqual(report['execution_status'],'completed')
        self.assertEqual(report['candidate_counts']['attempted'],16)
        self.assertEqual(report['candidate_counts']['evaluated'],16)
        self.assertEqual(report['test_evaluations'],0)
        self.assertIsNone(report['best_round'])
        self.assertNotIn('best_selection_receipt',report)
        self.assertIn('覆盖率',report['iterations'][0]['reason_message'])
        self.assertTrue(all(row['started_at'] and row['finished_at'] for row in report['iterations']))

    def test_input_conditions_are_not_code_failure(self):
        self.model_mock.side_effect=ValueError('连续有效训练样本不足以辨识当前阶次')
        with self.assertRaises(pipeline.OptimizationStopped):self.search()
        report=self.assert_consistent()
        self.assertEqual(report['optimization_outcome'],'insufficient_input')
        self.assertEqual(report['candidate_counts']['evaluated'],0)
        self.assertEqual(report['candidate_counts']['failed'],0)
        self.assertEqual(report['iterations'][0]['training_rows'],30)

    def test_real_error_after_one_completed_preserves_both(self):
        def fault(*args,**kwargs):
            if self.call_count:raise KeyError('injected-code-defect')
            return self.model(*args,**kwargs)
        self.model_mock.side_effect=fault
        with self.assertRaisesRegex(KeyError,'injected-code-defect'):self.search()
        report=self.assert_consistent()
        self.assertEqual(report['optimization_outcome'],'failed')
        self.assertEqual(report['candidate_counts']['attempted'],2)
        self.assertEqual(report['candidate_counts']['evaluated'],1)
        self.assertEqual(report['candidate_counts']['failed'],1)
        self.assertEqual(report['error']['type'],'KeyError')

    def test_before_first_candidate_exception_preserves_known_zero(self):
        with patch('core.services.pipeline._search_optimization',side_effect=RuntimeError('before-first')):
            with self.assertRaisesRegex(RuntimeError,'before-first'):self.search()
        report=self.assert_consistent()
        self.assertEqual(report['candidate_counts']['attempted'],0)
        self.assertEqual(report['optimization_outcome'],'failed')

    def test_cancel_keeps_first_completed_result(self):
        with self.assertRaises(pipeline.OptimizationStopped):self.search(cancel_check=lambda:self.call_count>=1)
        report=self.assert_consistent()
        self.assertEqual(report['optimization_outcome'],'cancelled')
        self.assertEqual(report['candidate_counts']['attempted'],1)
        self.assertEqual(report['candidate_counts']['evaluated'],1)

    def test_timeout_is_terminal_and_not_quality_failure(self):
        with self.assertRaises(pipeline.OptimizationStopped):self.search(timeout_seconds=-1)
        report=self.assert_consistent()
        self.assertEqual(report['optimization_outcome'],'timed_out')
        self.assertEqual(report['candidate_counts']['attempted'],0)

    def test_storage_failure_does_not_mask_original_code_exception(self):
        def failed_write(path,payload):
            if payload.get('optimization_outcome')=='failed':raise OSError('disk-full')
            return pipeline._write_json_original(path,payload)
        original=pipeline._write_json
        with patch.object(pipeline,'_write_json_original',original,create=True),patch.object(pipeline,'_write_json',side_effect=failed_write),patch.object(pipeline,'_search_optimization',side_effect=KeyError('original-code-error')):
            with self.assertRaisesRegex(KeyError,'original-code-error') as raised:self.search()
        self.assertEqual(raised.exception.optimization_report['persistence_error']['type'],'OSError')

    def test_success_freezes_winner_before_single_test_evaluation(self):
        import sys
        from types import SimpleNamespace
        calls=[]
        def finalize(out,test_path):
            report=json.loads((self.run/'05_optimization/optimization_report.json').read_text())
            self.assertTrue(report['frozen_winner_round'])
            calls.append(test_path)
            return {'validation':{'r2':.9},'test':{'r2':.8}},{}
        with patch.dict(sys.modules,{'validated_modeling':SimpleNamespace(finalize_test=finalize)}),patch.object(pipeline,'_read_csv',return_value=pd.DataFrame({'y':[1,2]})):
            report,model=self.search(constraints={'min_r2':0,'min_coverage':.05})
        self.assertEqual(len(calls),1)
        self.assertEqual(report['optimization_outcome'],'qualified_candidate')
        self.assertTrue(report['best_round'])
        self.assert_consistent()

    def test_history_missing_is_unknown_read_only_not_zero(self):
        original={'run_id':'old1','status':'failed','error':{'stage':'optimization'},'results':{'modeling':{'status':'pending_candidate_search'}},'stages':[{'key':'modeling','status':'completed'}]}
        recovered=recover_snapshot(original,self.root)
        self.assertIsNone(recovered['results']['optimization']['candidate_counts']['attempted'])
        self.assertEqual(original['stages'][0]['status'],'completed')
        self.assertNotEqual(recovered['stages'][0]['status'],'completed')
        self.assertFalse((self.root/'old1').exists())

    def test_completed_answer_does_not_mutate_terminal_pipeline_or_call_llm(self):
        from core.services.agent_chat import chat
        snap={'run_id':'case1','status':'needs_review','results':{'optimization':{'optimization_outcome':'no_feasible_candidate','stop_reason':'覆盖率不足','candidate_counts':{'attempted':16}}},'artifacts':{}}
        with patch('core.services.agent_chat.get_run',return_value=snap),patch('core.services.agent_chat.rerun_pipeline') as rerun,patch('core.services.llm_gateway.propose_task_spec') as llm:
            response=chat('为什么卡住了',run_id='case1',llm_config={'provider':'deepseek'})
        self.assertIn('已尝试16',response['answer']);self.assertEqual(response['snapshot']['status'],'needs_review')
        self.assertTrue(response['answer_sources']);self.assertEqual(response['intent']['key'],'optimization');rerun.assert_not_called();llm.assert_not_called()

    def test_worker_keeps_blocked_terminal_result(self):
        from core.services.jobs import execute
        job=RuntimeJob.objects.create(job_id='job1',job_type='pipeline',payload={},status='running')
        with patch('core.services.jobs._execute_pipeline',side_effect=lambda _:RuntimeJob.objects.filter(pk=job.pk).update(status='blocked')):
            execute(job)
        job.refresh_from_db();self.assertEqual(job.status,'blocked')

    def test_worker_preserves_recorded_timeout_and_does_not_retry_same_run(self):
        from core.services.jobs import execute
        job=RuntimeJob.objects.create(job_id='timeout1',job_type='pipeline',payload={'run_id':'case1'},result_ref='case1',status='running')
        self.snapshot['status']='timed_out'
        pipeline._write_json(self.run/'snapshot.json',self.snapshot)
        with patch('core.services.jobs._execute_pipeline',side_effect=TimeoutError('deadline')):
            execute(job)
        job.refresh_from_db();self.assertEqual(job.status,'timed_out');self.assertEqual(job.error_code,'TIMEOUT')

    def test_unrelated_quality_block_is_not_called_optimization_failure(self):
        from core.services.optimization_state import readable_stop
        self.assertIsNone(readable_stop({'status':'needs_review','current_stage':'standardization','results':{}}))

    def test_malformed_history_degrades_to_unknown_without_zero(self):
        folder=self.root/'old1'/'05_optimization';folder.mkdir(parents=True)
        (folder/'optimization_report.json').write_text('[]')
        result=recover_snapshot({'run_id':'old1','status':'failed','error':{'stage':'optimization','message':'原始错误'},'results':{}},self.root)
        self.assertIsNone(result['results']['optimization']['candidate_counts']['attempted'])
        self.assertEqual(result['results']['optimization']['stop_reason'],'原始错误')
