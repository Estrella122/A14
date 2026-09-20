from copy import deepcopy
from django.test import SimpleTestCase
from core.services.evidence_values import number, display, relative_improvement
from core.services.expert_qa import answer_expert_question


class EvidenceTruthTests(SimpleTestCase):
    def test_zero_negative_and_missing_are_distinct(self):
        self.assertEqual(display(0), '0.000')
        self.assertEqual(display(-.5), '-0.500')
        for value in (None, float('nan'), float('inf'), 'invalid'):
            self.assertIsNone(number(value))
            self.assertNotEqual(display(value), '0.000')
        self.assertIsNone(relative_improvement(1, 0))

    def test_no_run_cannot_finish_empty_stages(self):
        answer = answer_expert_question('把这次结果导出。', {'results': {}, 'artifacts': {}})['answer']
        self.assertNotIn('所有记录阶段均已跑通', answer)

    def test_missing_model_never_uses_previous_or_zero(self):
        for status in ('needs_review', 'failed', 'completed'):
            snapshot = {'run_id': 'current', 'status': status, 'results': {'standardization': {'mapping': {}}}, 'artifacts': {}}
            answer = answer_expert_question('当前测试集R²和泛化效果如何？', snapshot)['answer']
            self.assertNotIn('R²=0.000', answer)
            self.assertIn('未保存', answer)

    def test_uncomputed_selection_not_zero(self):
        snapshot = {'results': {}, 'artifacts': {}}
        answer = answer_expert_question('为什么严格动态段为0还能建模？', snapshot)['answer']
        self.assertIn('尚未计算分段', answer)
        self.assertNotIn('当前严格达标动态段 0 个', answer)
        computed = deepcopy(snapshot)
        computed['results']['cleaning'] = {'selection_metrics': {'actual_selected_window_count': 0}, 'strict_selected_segment_count': 0, 'selected_segment_count': 0, 'modeling_row_count': 0}
        answer = answer_expert_question('为什么严格动态段为0还能建模？', computed)['answer']
        self.assertIn('当前严格达标动态段 0 个', answer)


class ActionBoundaryTests(SimpleTestCase):
    def test_original_and_paraphrased_actions(self):
        from core.skills.task_understanding import understand_task
        cases = {
            '请基于本次结果生成完整图文工程报告，包含清洗、动态段、时滞共线性、候选比较、实际模型、基线、限制与下一步。': 'GENERATE_REPORT',
            '把这次结果导出。': 'EXPORT_ARTIFACT',
            '这次最佳参数是多少，为什么选它？': 'QUERY_EXISTING',
            '帮我从当前数据中筛选动态片段、消除冗余输入，再循环评估并选出建模数据。': 'EXECUTE_NUMERIC',
            '不要寻优，只解释上次为什么没改善': 'GENERAL_EXPLANATION',
            '请解释为什么需要重新训练': 'GENERAL_EXPLANATION',
            '重新寻优，完成后生成报告并导出': 'EXECUTE_NUMERIC',
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                task = understand_task(message)
                self.assertEqual(task['action_type'], expected)
        task = understand_task('重新寻优，完成后生成报告并导出')
        self.assertEqual(task['constraints']['requested_actions'], ['EXECUTE_NUMERIC', 'GENERATE_REPORT', 'EXPORT_ARTIFACT'])

    def test_oversized_context_keeps_core_facts(self):
        from unittest.mock import patch
        from core.services.answer_context import build_answer_context
        from core.services.llm_gateway import _evidence_payload
        snapshot = {'run_id': 'frozen_A', 'status': 'completed', 'results': {
            'modeling': {'config': {'family': 'FIRX'}, 'fitted_inputs': ['observed_u'],
                         'metrics': {'validation': {'r2': .92}, 'test': {'r2': -.4}},
                         'collinearity': {str(i): list(range(100)) for i in range(1000)},
                         'diagnostics': {'test': {'rmse_improvement_over_persistence_pct': -2.6}}},
            'optimization': {'best_round': 7, 'best_parameters': {'top_k': 12, 'max_lag': 68}, 'iterations': [{'large': 'x'*10000}]*100},
            'cleaning': {'logs': ['x'*10000]*100}}}
        with patch('core.services.answer_context.search_knowledge', return_value={'documents': []}):
            context = build_answer_context('生成报告', snapshot, {}, budget=12000)
            payload = _evidence_payload('生成报告', snapshot, {'answer_context': context})
            for value in ['FIRX', 'observed_u', '0.92', '-0.4', '-2.6', '68']:
                self.assertIn(value, payload)
            import json
            self.assertLessEqual(len(json.dumps(context, ensure_ascii=False)), 12000)
            tiny = build_answer_context('生成报告', snapshot, {}, budget=100)
            self.assertTrue(tiny['context_observability']['fallback_required'])


from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from tempfile import TemporaryDirectory
from pathlib import Path


class PersistentAssetTests(TestCase):
    def test_same_name_archive_restart_and_owner_boundary(self):
        from django.contrib.auth import get_user_model
        from core.models import FileAsset
        with TemporaryDirectory() as directory, override_settings(PROCESSPILOT_RUNTIME_ROOT=directory):
            user = get_user_model().objects.create_user('asset_owner')
            stranger = get_user_model().objects.create_user('asset_other')
            self.client.force_login(user)
            def upload(raw):
                return self.client.post('/api/assets/', {'file': SimpleUploadedFile('same.csv', raw)}).json()['data']
            a, b = upload(b'u,y\n1,2\n'), upload(b'u,y\n3,4\n')
            self.assertNotEqual(a['asset_id'], b['asset_id'])
            self.assertNotEqual(a['content_hash'], b['content_hash'])
            record = FileAsset.objects.get(pk=a['asset_id'])
            record.related_runs = ['immutable_run']; record.save()
            stored = Path(directory) / 'file_assets' / record.storage_ref
            from django.test import Client
            fresh = Client(); fresh.force_login(user)
            self.assertEqual(len(fresh.get('/api/assets/').json()['data']), 2)
            for _ in range(2):
                response = fresh.delete(f"/api/assets/{a['asset_id']}/")
                self.assertEqual(response.status_code, 200)
            self.assertEqual(fresh.get(f"/api/assets/{a['asset_id']}/").json()['data']['status'], 'archived')
            self.assertTrue(stored.exists())
            self.assertEqual(len(fresh.get('/api/assets/').json()['data']), 1)
            fresh.force_login(stranger)
            self.assertEqual(fresh.delete(f"/api/assets/{b['asset_id']}/").status_code, 404)
            record = FileAsset.objects.get(pk=b['asset_id']); record.storage_ref = '../outside.csv'; record.save()
            fresh.force_login(user)
            self.assertEqual(fresh.get(f"/api/assets/{b['asset_id']}/?download=1").status_code, 404)


class ReportEvidenceTests(SimpleTestCase):
    def test_report_is_self_contained_and_never_runs_numeric_stages(self):
        import json
        from unittest.mock import patch
        from core.services.delivery_report import generate_report, artifact_manifest
        snapshot = {'run_id': 'isolated_report', 'status': 'partial', 'original_name': '<script>alert(1)</script>',
                    'results': {'optimization': {'best_round': 1, 'iterations': [{'round': 1, 'status': 'completed', 'score': 92}]},
                                'modeling': {'metrics': {'validation': {'r2': .9}, 'test': {'r2': -.4}}}}, 'artifacts': {}}
        with TemporaryDirectory() as directory, patch('core.services.pipeline.RUNS_DIR', Path(directory)), patch('core.services.pipeline.rerun_pipeline') as rerun, patch('core.services.pipeline._persist_snapshot'):
            result = generate_report(snapshot)
            report = Path(directory) / snapshot['run_id'] / result['artifacts']['analysis_report_html']
            text = report.read_text()
            self.assertIn('data:image/png;base64,', text)
            self.assertNotIn('<script>alert', text)
            self.assertIn('&lt;script&gt;', text)
            self.assertIn('尚未生成对应证据', text)
            self.assertEqual(artifact_manifest(result)['analysis_report_html']['state'], 'ready')
            manifest = result['results']['report']['manifest']
            self.assertEqual(manifest['source_run'], 'isolated_report')
            self.assertEqual(manifest['numeric_executions'], 0)
            report.unlink()
            self.assertEqual(artifact_manifest(result)['analysis_report_html']['state'], 'missing')
            rerun.assert_not_called()

    def test_winner_projection_preserves_baseline_and_real_zero(self):
        from core.services.evidence_values import final_result_view
        snapshot = {'run_id': 'one', 'results': {'cleaning': {'modeling_row_count': 30, 'selection_metrics': {'target_observation_count': 27}},
            'best_selection_receipt': {'selected_row_count': 45, 'actual_target_observation_count': 0,
              'selected_window_ids': ['a', 'b'], 'selected_windows': [{'window_id': 'a', 'level': '可用数据段'}, {'window_id': 'b', 'level': '优质动态段'}], 'requested_parameters': {'top_k': 2}, 'strict_window_count': 0, 'usable_window_count': 1}}}
        frozen = deepcopy(snapshot)
        result = final_result_view(snapshot)
        self.assertEqual(snapshot, frozen)
        self.assertTrue(all(row['selected'] for row in result['results']['cleaning']['segments_preview']))
        self.assertEqual(result['results']['cleaning']['modeling_row_count'], 45)
        self.assertEqual(result['results']['cleaning']['selection_metrics']['target_observation_count'], 0)
        self.assertEqual(result['results']['cleaning']['selection_metrics']['actual_selected_window_count'], 2)

    def test_robust_amplitude_rejects_isolated_spike_preserves_step(self):
        import numpy as np
        import pandas as pd
        from integrations.data_cleaning.src.data_cleaning_agent import DataCleaningSelectionAgent
        agent = DataCleaningSelectionAgent({'u': {'role': 'input'}, 'y': {'role': 'output'}})
        spike = pd.DataFrame({'u': np.full(120, 100.)}); spike.loc[60, 'u'] = 130
        step = pd.DataFrame({'u': np.r_[np.full(60,100.), np.full(60,130.)]})
        self.assertEqual(agent._relative_range_score(spike, 1500), 0)
        self.assertGreater(agent._relative_range_score(step, 1500), 90)

class RunAccessTests(SimpleTestCase):
    def test_explicit_run_checks_trace_and_source_binding(self):
        from django.test import RequestFactory, override_settings
        from django.http import JsonResponse
        from types import SimpleNamespace
        from unittest.mock import patch
        from core.security import ApiAuthenticationMiddleware
        factory = RequestFactory()
        middleware = ApiAuthenticationMiddleware(lambda req: JsonResponse({'ok': True}))
        for route, body in [('/api/agent/runs/foreign/trace/', None), ('/api/pipeline/workflows/execute/', {'source_run_id': 'foreign'})]:
            request = factory.get(route) if body is None else factory.post(route, body, content_type='application/json')
            request.user = SimpleNamespace(is_authenticated=True, pk=1, is_staff=False)
            with override_settings(PROCESSPILOT_REQUIRE_AUTH=True), patch('core.services.pipeline.get_run', return_value={'run_id': 'foreign', 'owner_id': 2, 'project':'A14'}):
                self.assertEqual(middleware(request).status_code, 403)
        request = factory.get('/api/pipeline/runs/mine/')
        request.user = SimpleNamespace(is_authenticated=True, pk=1, is_staff=False)
        with override_settings(PROCESSPILOT_REQUIRE_AUTH=True), patch('core.services.pipeline.get_run', return_value={'run_id': 'mine', 'owner_id': 1, 'project':'A14'}):
            self.assertEqual(middleware(request).status_code, 200)

class LLMProposalBoundaryTests(SimpleTestCase):
    def test_invalid_capability_run_binding_and_readonly_upgrade(self):
        import json
        from unittest.mock import patch, MagicMock
        from core.services.llm_gateway import propose_task_spec, ResolvedLLMConfig
        config = ResolvedLLMConfig('local', 'test', 'test', 'http://localhost', '')
        base = {'objective':'explain existing result', 'action_type':'EXECUTE_NUMERIC', 'requested_capabilities':[], 'parameters':{}, 'requested_outputs':['explanation'], 'needs_clarification':False}
        for extra, rejected in [({'run_id':'foreign'}, True), ({'requested_capabilities':['shell.execute']}, True), ({'parameters':{'max_lag':-9}}, True), ({}, False)]:
            remote = MagicMock();remote.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps({**base, **extra})}}]}).encode()
            with patch('core.services.llm_gateway.resolve_llm_config', return_value=config), patch('core.services.llm_gateway.urlopen', return_value=remote):
                task, audit = propose_task_spec('不要寻优，只解释上次为什么没改善', {'run_id':'mine','results':{}}, {'provider':'local'})
            self.assertEqual(task['action_type'], 'GENERAL_EXPLANATION')
            self.assertEqual(audit['fallback'], rejected)
            if not rejected:
                self.assertIn({'field':'action_type','reason':'request_authority_boundary'}, audit['rejected_fields'])

class RejectedRoundEvidenceTests(SimpleTestCase):
    def test_current_rejected_round_is_uncomputed_not_historical(self):
        from core.services.evidence_values import final_result_view
        source = {'results':{'optimization':{'iterations':[{'round_id':'A:8','status':'infeasible','rejection_reason':'outside explicit bounds'},{'round':1}]}}}
        result = final_result_view(source)['results']['optimization']['iterations']
        self.assertEqual(result[0]['audit_status'], 'not_computed')
        self.assertNotIn('historical_not_recorded', result[0])
        self.assertEqual(result[1]['audit_status'], 'historical_not_recorded')
        self.assertNotIn('audit_status', source['results']['optimization']['iterations'][0])
