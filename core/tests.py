import copy
import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .models import OptimizationRun, OptimizationStudy
from .services.optimization import (
    DEFAULT_INITIAL_CANDIDATE,
    benchmark_snapshot_id,
    evaluate_candidate,
    normalize_candidate,
)
from .services.agent_chat import chat
from .runtime_retention import prune_runtime
from .services.expert_qa import coverage_summary
from .skills import list_skills, plan_skills


PROJECT_CODE = 'FUR-APC-2026-02'
PROJECT_NAME = '2# 热轧加热炉 APC 建模'


class IntegrationBridgeTests(SimpleTestCase):
    def test_member_delivery_packages_are_available_through_one_api(self):
        for module in ('standardization', 'cleaning', 'modeling', 'agent'):
            with self.subTest(module=module):
                response = self.client.get(f'/api/integration/{module}/')
                self.assertEqual(response.status_code, 200, response.content)
                payload = response.json()
                self.assertTrue(payload['ok'])
                # Historical agent_control artifacts are deliberately absent from
                # this distribution; the bridge must not fabricate availability.
                if module == 'agent':
                    candidate = Path(settings.BASE_DIR) / 'integrations/agent_control/runtime/artifacts/run_a1f3a6251227/candidate_002_evaluation.json'
                    self.assertEqual(payload['data']['available'], candidate.exists())
                else:
                    self.assertTrue(payload['data']['available'])

    def test_integration_summary_contains_all_member_modules(self):
        response = self.client.get('/api/integration/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(set(response.json()['modules']), {'standardization', 'cleaning', 'modeling', 'agent'})


class AgentChatTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.skill_runs = TemporaryDirectory()
        self.skill_runs_patch = patch('core.skills.runtime.RUNS_DIR', Path(self.skill_runs.name))
        self.skill_runs_patch.start()

    def tearDown(self):
        self.skill_runs_patch.stop()
        self.skill_runs.cleanup()
        super().tearDown()

    def snapshot(self):
        return {
            'run_id': 'run_test',
            'results': {
                'standardization': {'scenario': {'scenario_name': '钢铁高炉铁水质量预测'}, 'mapping': {'mappings': [], 'required_coverage': 1, 'missing_required': []}, 'data_decision': {'status': 'ready'}},
                'cleaning': {'overall_score': 82.5, 'cleaned_row_count': 500, 'modeling_row_count': 180, 'selected_segment_count': 3, 'missing_rate': {'gas_flow': 0.02}, 'dimension_scores': {'dynamic': 85}},
                'modeling': {'output_col': 'slab_discharge_temp', 'input_cols': ['gas_flow'], 'selected_inputs': ['gas_flow_aligned'], 'lags': [{'input': 'gas_flow', 'output': 'slab_discharge_temp', 'delay_samples': 8, 'correlation': 0.72}], 'metrics': {'test': {'r2': 0.76, 'rmse': 2.1, 'mae': 1.4}}},
                'optimization': {'best_round': 2, 'best_label': '精炼动态段', 'best_score': 82.4, 'best_parameters': {'top_k': 3, 'max_lag': 30}, 'best_metrics': {'r2': 0.79, 'rmse': 1.9, 'mae': 1.2, 'coverage': 0.36}, 'iterations': [{'round': 1, 'status': 'completed'}, {'round': 2, 'status': 'completed'}, {'round': 3, 'status': 'completed'}]},
                'review': {'passed': True, 'conclusion': '通过', 'blockers': [], 'warnings': []},
                'report': {'title': '分析报告'},
            },
        }

    def test_different_questions_change_answer_intent_cards_and_plan(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            selection = chat('为什么动态段这么少')
            modeling = chat('这个模型的R2和RMSE怎么样')

        self.assertEqual(selection['intent']['key'], 'selection')
        self.assertEqual(modeling['intent']['key'], 'modeling')
        self.assertNotEqual(selection['answer'], modeling['answer'])
        self.assertNotEqual(selection['cards'], modeling['cards'])
        self.assertEqual(next(node for node in selection['plan'] if node['key'] == 'selection')['status'], 'completed')

    def test_optimization_question_reports_real_candidate_evidence(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('闭环寻优哪一轮是最佳策略')

        self.assertEqual(result['intent']['key'], 'optimization')
        self.assertIn('3 组候选策略', result['answer'])
        self.assertIn('第 2 轮', result['answer'])
        self.assertEqual(next(node for node in result['plan'] if node['key'] == 'optimization')['status'], 'completed')

    def test_multi_topic_summary_answers_all_requested_evidence(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('总结数据质量、模型效果、寻优结果和评审结论')

        self.assertEqual(result['intent']['key'], 'overview')
        self.assertIn('质量评分 82.5', result['answer'])
        self.assertIn('R²=0.760', result['answer'])
        self.assertIn('第 2 轮', result['answer'])
        self.assertIn('最终评审', result['answer'])
        self.assertGreaterEqual(len(result['intent']['matched']), 3)

    def test_follow_up_without_domain_keyword_keeps_previous_context(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('那为什么会这样呢', previous_intent='optimization')

        self.assertEqual(result['intent']['key'], 'optimization')
        self.assertIn('第 2 轮', result['answer'])

    def test_ambiguous_follow_up_after_multi_topic_answer_asks_for_clarification(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('那为什么会这样呢', previous_intent='overview', previous_intents=['cleaning', 'modeling', 'optimization', 'review'])

        self.assertEqual(result['intent']['key'], 'clarification')
        self.assertIn('具体是指哪一项', result['answer'])

    def test_greeting_gets_conversational_answer(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('你好，在吗')

        self.assertEqual(result['intent']['key'], 'conversation')
        self.assertIn('你好，我在', result['answer'])

    def test_problem_question_returns_prioritized_diagnosis(self):
        snapshot = self.snapshot()
        snapshot['results']['cleaning']['selected_segment_count'] = 0
        snapshot['results']['cleaning']['missing_rate'] = {'gas_flow': 0.42}
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat('这批数据最大的问题是什么')

        self.assertEqual(result['intent']['key'], 'diagnosis')
        self.assertIn('最值得先处理的问题', result['answer'])
        self.assertIn('gas_flow', result['answer'])

    def test_skill_catalog_has_five_groups_and_thirty_unique_skills(self):
        catalog = list_skills()
        self.assertEqual(catalog['total'], 30)
        self.assertEqual(len(catalog['categories']), 5)
        self.assertEqual(len({item['id'] for item in catalog['skills']}), 30)
        for category in catalog['categories']:
            self.assertEqual(sum(item['category'] == category['id'] for item in catalog['skills']), 6)

    def test_high_snr_tower_request_builds_dependency_complete_skill_plan(self):
        plan = plan_skills('提取 1 号塔高信噪比的动态数据', 'run_test')
        skill_ids = [item['skill_id'] for item in plan['steps']]
        self.assertEqual(plan['entities']['equipment_id'], '1号塔')
        self.assertIn('signal_noise_ratio_estimator', skill_ids)
        self.assertIn('high_snr_dynamic_segment_extractor', skill_ids)
        self.assertLess(skill_ids.index('missing_anomaly_cleaner'), skill_ids.index('high_snr_dynamic_segment_extractor'))

    def test_skills_api_and_plan_api_expose_runtime_contract(self):
        catalog_response = self.client.get('/api/agent/skills/')
        self.assertEqual(catalog_response.status_code, 200)
        self.assertEqual(catalog_response.json()['data']['total'], 30)
        self.assertEqual(len(catalog_response.json()['data']['expert_topics']), 21)
        plan_response = self.client.post('/api/agent/plans/', data=json.dumps({'message': '提取1号塔高信噪比动态数据', 'run_id': 'run_test'}), content_type='application/json')
        self.assertEqual(plan_response.status_code, 201)
        self.assertGreater(plan_response.json()['data']['selected_count'], 5)

    @patch('core.agent_api.get_run')
    def test_skill_run_api_executes_against_pipeline_evidence(self, mocked_get_run):
        mocked_get_run.return_value = self.snapshot()
        response = self.client.post('/api/agent/skill-runs/', data=json.dumps({'message': '分析模型R2', 'run_id': 'run_test'}), content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()['data']
        self.assertEqual(payload['status'], 'partial')
        modeling = next(item for item in payload['executions'] if item['skill_id'] == 'model_diagnostics_evaluator')
        self.assertEqual(modeling['metrics']['r2'], 0.76)

    def test_expert_residual_question_states_evidence_boundary(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('你们怎么证明残差是白噪声，做过自相关检验吗')
        self.assertEqual(result['expert_topic'], 'residual')
        self.assertEqual(result['intent']['key'], 'modeling')
        self.assertIn('不能声称残差已经是白噪声', result['answer'])
        skill_ids = [item['skill_id'] for item in result['skill_executions']]
        self.assertIn('model_diagnostics_evaluator', skill_ids)
        self.assertLess(len(skill_ids), 10)

    def test_expert_deployment_question_does_not_overclaim(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('这个模型现在可以直接上线投运吗，安全边界是什么')
        self.assertEqual(result['expert_topic'], 'deployment')
        self.assertIn('不等于可以直接投运', result['answer'])
        self.assertIn('联锁', result['answer'])

    def test_professional_questions_route_to_distinct_skill_sets(self):
        leakage = {item['skill_id'] for item in plan_skills('如何避免时间序列数据泄漏', snapshot=self.snapshot())['steps']}
        frequency = {item['skill_id'] for item in plan_skills('伯德图和奈奎斯特图说明了什么', snapshot=self.snapshot())['steps']}
        self.assertIn('modeling_dataset_assembler', leakage)
        self.assertNotIn('engineering_visualization_builder', leakage)
        self.assertIn('engineering_visualization_builder', frequency)

    def test_question_about_optimization_does_not_trigger_execution_mode(self):
        plan = plan_skills('为什么闭环寻优第3轮最好')
        self.assertEqual(plan['mode'], 'analyze')

    def test_equipment_mismatch_blocks_compound_execution(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()), patch('core.services.agent_chat.rerun_pipeline') as rerun:
            result = chat('提取1号塔高信噪比动态数据，处理共线性后进行闭环寻优')
        rerun.assert_not_called()
        self.assertTrue(result['blocked'])
        self.assertIn('设备场景不一致', result['answer'])
        self.assertGreater(result['skill_summary']['blocked'], 0)

    def test_matching_compound_command_returns_all_stage_results_and_artifacts(self):
        snapshot = self.snapshot()
        snapshot['run_id'] = 'run_rerun'
        snapshot['results']['modeling']['input_cols'] = ['gas_flow', 'air_flow']
        snapshot['results']['modeling']['selected_inputs'] = ['gas_flow_aligned']
        snapshot['artifacts'] = {'segments_csv': 'segments.csv', 'modeling_csv': 'modeling.csv', 'optimization_json': 'optimization.json'}
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()), patch('core.services.agent_chat.rerun_pipeline', return_value=snapshot):
            result = chat('提取高炉高信噪比动态数据，处理共线性后进行闭环寻优')
        self.assertTrue(result['executed'])
        self.assertFalse(result['blocked'])
        self.assertIn('共线性诊断从 2 个输入保留 1 个', result['answer'])
        self.assertIn('第 2 轮验证得分最高', result['answer'])
        self.assertEqual({item['key'] for item in result['deliverables']}, {'segments_csv', 'modeling_csv', 'optimization_json'})

    def test_compound_expert_question_uses_minimal_precise_skill_set(self):
        question = '当前模型测试集R²不错，如何证明没有时序数据泄漏和过拟合？请结合残差自相关、模型阶次和独立工况验证说明，不要直接给出可上线结论。'
        plan = plan_skills(question, 'run_test', snapshot=self.snapshot())
        skill_ids = {item['skill_id'] for item in plan['steps']}
        self.assertEqual(plan['mode'], 'analyze')
        self.assertEqual(plan['analysis']['question_type'], 'compound')
        self.assertTrue({'leakage', 'residual', 'generalization', 'order', 'deployment'}.issubset(set(plan['analysis']['topics'])))
        self.assertIn('modeling_dataset_assembler', skill_ids)
        self.assertIn('arx_structure_order_selector', skill_ids)
        self.assertIn('multi_model_benchmark', skill_ids)
        self.assertIn('model_diagnostics_evaluator', skill_ids)
        self.assertNotIn('industrial_simulation_generator', skill_ids)
        self.assertNotIn('steady_transient_state_detector', skill_ids)
        self.assertNotIn('constraint_parameter_extractor', skill_ids)
        self.assertNotIn('expert_report_writer', skill_ids)
        self.assertLessEqual(len(skill_ids), 10)

    def test_compound_expert_answer_covers_every_requested_dimension(self):
        question = '当前模型测试集R²不错，如何证明没有时序数据泄漏和过拟合？请结合残差自相关、模型阶次和独立工况验证说明，不要直接给出可上线结论。'
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat(question)
        self.assertGreaterEqual(len(result['expert_topics']), 5)
        for heading in ('时序数据泄漏', '残差诊断', '过拟合与泛化', '模型结构与阶次', '上线安全边界'):
            self.assertIn(heading, result['answer'])
        self.assertIn('当前证据不足', result['answer'])
        self.assertIn('0.760', result['answer'])

    def test_lag_collinearity_causality_answer_consumes_current_run_evidence(self):
        snapshot = self.snapshot()
        snapshot['results']['modeling'].update({
            'input_cols': ['gas_flow', 'air_flow'],
            'selected_inputs': ['air_flow_aligned'],
            'collinearity': {
                'vif': [
                    {'variable': 'gas_flow_aligned', 'vif': 18.42},
                    {'variable': 'air_flow_aligned', 'vif': 17.91},
                ],
                'recommendations': {
                    'keep': ['air_flow_aligned'],
                    'drop': ['gas_flow_aligned'],
                    'reasons': [{
                        'drop': 'gas_flow_aligned',
                        'reason': 'high_pairwise_correlation',
                        'pair': ['gas_flow_aligned', 'air_flow_aligned'],
                        'correlation': 0.971,
                    }],
                },
            },
        })
        question = '互相关时滞是否有物理意义？严重共线性时如何避免误判因果？请结合时滞、相关系数、VIF和保留变量说明。'
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat(question)

        self.assertEqual(result['expert_topics'], ['lag', 'collinearity', 'causality'])
        for evidence in ('时滞 8 个采样点', '相关系数 +0.720', '最大 VIF 为 18.42', '保留变量：air_flow', '剔除变量：gas_flow', '相关系数 +0.971'):
            self.assertIn(evidence, result['answer'])
        self.assertIn('不等同于因果证明', result['answer'])
        evidence_gap = next(card for card in result['cards'] if card['label'] == '证据缺口')
        self.assertEqual(evidence_gap['value'], 3)

    def test_optimization_expert_answer_compares_rounds_and_train_test_evidence(self):
        snapshot = self.snapshot()
        snapshot['results']['modeling']['config'] = {'output_order': 2, 'input_order': 2, 'input_delay': 1}
        snapshot['results']['modeling']['metrics']['train'] = {'r2': 0.85, 'rmse': 2.35}
        snapshot['results']['modeling']['metrics']['test'].update({'num_params': 9, 'aic': 129.616, 'bic': 141.278})
        snapshot['results']['optimization'].update({
            'objective': '0.68×R²得分 + 0.17×误差得分 + 0.15×数据覆盖率',
            'iterations': [
                {'round': 1, 'status': 'completed', 'score': 50.429, 'r2': 0.438, 'rmse': 0.267, 'coverage': 0.0556},
                {'round': 2, 'status': 'completed', 'score': 42.100, 'r2': 0.300, 'rmse': 0.500, 'coverage': 0.0800},
                {'round': 7, 'status': 'completed', 'score': 50.506, 'r2': 0.639, 'rmse': 7.901, 'coverage': 0.0694},
            ],
            'best_round': 7,
            'best_score': 50.506,
        })
        question = '当前最优模型测试集R²为0.639，但闭环寻优仍将它选为最佳候选。请结合训练集与测试集指标差异、RMSE、数据覆盖率、残差自相关、ARX阶次和各轮候选结果解释，并判断是否过拟合以及能否投运。'
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat(question)

        self.assertTrue({'residual', 'generalization', 'order', 'optimization', 'deployment'}.issubset(result['expert_topics']))
        skill_ids = {item['skill_id'] for item in result['skill_executions']}
        self.assertIn('closed_loop_preprocessing_optimizer', skill_ids)
        for evidence in ('实际完成 3 轮', '第 7 轮得分 50.506', '覆盖率 6.94%', '第1轮 得分50.429', 'R²下降 0.090', 'na=2', 'AIC=129.616'):
            self.assertIn(evidence, result['answer'])
        self.assertIn('当前权重下暂优', result['answer'])

    def test_every_expert_topic_example_has_a_matching_runtime_route(self):
        for topic in coverage_summary():
            with self.subTest(topic=topic['key']):
                plan = plan_skills(f"请分析{topic['examples'][0]}", snapshot=self.snapshot())
                self.assertIn(topic['key'], plan['analysis']['topics'])
                self.assertGreater(len(plan['steps']), 4)

    def test_hypothetical_reidentification_question_never_executes_pipeline(self):
        question = '如果迁移到另一座炉，哪些参数必须重新辨识，如何监测模型漂移？'
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()), patch('core.services.agent_chat.rerun_pipeline') as rerun:
            result = chat(question)

        rerun.assert_not_called()
        self.assertEqual(result['execution_mode'], 'analysis')
        self.assertEqual(result['expert_topics'], ['transfer', 'drift'])
        self.assertLessEqual(result['skill_summary']['total'], 10)

    def test_residual_input_cross_correlation_does_not_trigger_lag_topic(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('残差是否为白噪声，请结合残差自相关和残差与输入互相关说明')

        self.assertEqual(result['expert_topics'], ['residual'])
        self.assertNotIn('time_delay_estimator_compensator', {item['skill_id'] for item in result['skill_executions']})

    def test_missing_model_evidence_is_never_rendered_as_fake_zero_metrics(self):
        snapshot = self.snapshot()
        snapshot['results']['modeling'] = {}
        snapshot['results']['optimization'] = {}
        question = '请说明当前时滞、VIF、残差、训练测试差异、ARX阶次和闭环寻优最佳候选'
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat(question)

        self.assertNotIn('VIF 为 0.00', result['answer'])
        self.assertNotIn('R²=0.000', result['answer'])
        self.assertNotIn('AIC=0.000', result['answer'])
        self.assertIn('未保存可核验的输入—输出时滞结果', result['answer'])
        self.assertIn('未保存 VIF 表', result['answer'])
        self.assertIn('未保存测试集指标或残差统计量', result['answer'])
        self.assertIn('未保存闭环寻优候选轮次', result['answer'])

    def test_degraded_dynamic_segment_question_returns_explicit_acceptance_decision(self):
        snapshot = self.snapshot()
        snapshot['results']['cleaning'].update({
            'selected_segment_count': 0,
            'modeling_row_count': 120,
            'dimension_scores': {'dynamic': 66.91},
        })
        snapshot['results']['modeling']['metrics']['train'] = {'r2': 0.853, 'rmse': 2.355}
        snapshot['results']['modeling']['metrics']['test'] = {'r2': 0.639, 'rmse': 7.901}
        snapshot['results']['optimization'].update({
            'best_round': 7,
            'best_score': 50.506,
            'best_metrics': {'r2': 0.639, 'rmse': 7.901, 'coverage': 0.0694},
            'iterations': [{'round': 7, 'status': 'completed', 'score': 50.506, 'r2': 0.639, 'rmse': 7.901, 'coverage': 0.0694}],
        })
        question = '当前系统筛选出了0个严格优质动态段，却仍然使用120行候选数据完成了ARX辨识。请结合动态性评分、信噪比、持续激励、候选段降级策略、训练测试指标和数据覆盖率，判断降级建模是否合理，说明参数可信度风险和还需什么实验才能升级为可验收模型。'
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat(question)

        self.assertEqual(result['expert_topics'], ['degraded_modeling', 'optimization', 'deployment'])
        for evidence in ('动态性得分 66.91', '降级建模使用 120 行', '最佳候选覆盖率 6.94%', '训练/测试 R² 为 0.853/0.639'):
            self.assertIn(evidence, result['answer'])
        self.assertIn('比较算法方案是合理的，但用它确认模型参数或通过验收不合理', result['answer'])
        self.assertIn('参数置信区间', result['answer'])
        skill_ids = {item['skill_id'] for item in result['skill_executions']}
        self.assertTrue({'high_snr_dynamic_segment_extractor', 'modeling_dataset_assembler', 'model_diagnostics_evaluator', 'closed_loop_preprocessing_optimizer'}.issubset(skill_ids))

    def test_field_unit_question_keeps_standardization_evidence_in_compound_answer(self):
        snapshot = self.snapshot()
        snapshot['results']['standardization'].update({
            'detection': {'selected': {'review_fields': 0}},
            'data_decision': {'status': 'ready'},
        })
        question = 'gas_flow和air_flow单位不同或字段语义映射错误时，共线性和时滞结果是否可信？'
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat(question)

        self.assertIn('standardization', result['expert_topics'])
        self.assertIn('字段名匹配并不自动证明量纲正确', result['answer'])
        self.assertIn('semantic_field_unit_standardizer', {item['skill_id'] for item in result['skill_executions']})

    def test_interpolation_bias_question_consumes_cleaning_evidence(self):
        snapshot = self.snapshot()
        snapshot['results']['cleaning']['logs'] = ['gas_flow 检测到 40 个异常点，已标记并插值修复。', 'air_flow 检测到 34 个异常点，已标记并插值修复。']
        with patch('core.services.agent_chat.get_run', return_value=snapshot):
            result = chat('异常点经过线性插值会不会制造平滑动态并抬高R²？请结合残差说明。')

        self.assertEqual(result['expert_topics'], ['cleaning', 'residual'])
        self.assertIn('共标记 74 个变量级异常点', result['answer'])
        self.assertIn('missing_anomaly_cleaner', {item['skill_id'] for item in result['skill_executions']})

    def test_weight_sensitivity_question_routes_to_optimizer(self):
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()):
            result = chat('改变目标权重后最优轮次是否稳定，如何做权重敏感性分析？')

        self.assertEqual(result['expert_topics'], ['optimization'])
        self.assertIn('closed_loop_preprocessing_optimizer', {item['skill_id'] for item in result['skill_executions']})

    def test_execution_phrase_triggers_real_rerun_hook(self):
        rerun = {**self.snapshot(), 'run_id': 'run_rerun'}
        with patch('core.services.agent_chat.get_run', return_value=self.snapshot()), patch('core.services.agent_chat.rerun_pipeline', return_value=rerun) as mocked:
            result = chat('按5秒重新执行数据清洗')

        mocked.assert_called_once_with('run_test', resample_rule='5s', max_lag=60, stop_after='cleaning')
        self.assertTrue(result['executed'])
        self.assertEqual(result['run_id'], 'run_rerun')

    @patch('core.agent_api.get_run')
    def test_agent_trace_exposes_auditable_execution_nodes(self, mocked_get_run):
        snapshot = self.snapshot()
        snapshot.update({'status': 'completed', 'created_at': '2026-09-07T10:00:00+08:00', 'updated_at': '2026-09-07T10:00:03+08:00', 'instruction': '闭环寻优', 'stages': [{'key': 'modeling', 'started_at': '2026-09-07T10:00:01+08:00', 'finished_at': '2026-09-07T10:00:02+08:00'}], 'artifacts': {'report': 'report.md'}})
        mocked_get_run.return_value = snapshot
        response = self.client.get('/api/agent/runs/run_test/trace/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()['data']
        self.assertEqual(payload['source'], 'api')
        self.assertEqual(len(payload['nodes']), 8)
        self.assertEqual(payload['nodes'][5]['output']['r2'], 0.76)


class LivePipelineApiTests(SimpleTestCase):
    @patch('core.pipeline_api.list_runs', return_value=[{'score': float('nan')}])
    def test_pipeline_response_replaces_non_finite_numbers_with_null(self, mocked_list):
        response = self.client.get('/api/pipeline/runs/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['data'][0]['score'])
        self.assertNotIn(b'NaN', response.content)

    @patch('core.pipeline_api.list_runs', return_value=[{'run_id': 'run_new'}, {'run_id': 'run_old'}])
    def test_pipeline_collection_lists_history_for_experiment_tracking(self, mocked_list):
        response = self.client.get('/api/pipeline/runs/?limit=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['run_id'] for item in response.json()['data']], ['run_new', 'run_old'])
        mocked_list.assert_called_once_with(20)

    @patch('core.pipeline_api.list_runs', return_value=[{'run_id': 'run_deb'}])
    def test_pipeline_collection_filters_history_by_scenario(self, mocked_list):
        response = self.client.get('/api/pipeline/runs/?scenario_id=debutanizer_column')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'][0]['run_id'], 'run_deb')
        mocked_list.assert_called_once_with(100, scenario_id='debutanizer_column')

    def test_pipeline_rejects_non_csv_upload(self):
        upload = SimpleUploadedFile('notes.txt', b'not a csv', content_type='text/plain')
        response = self.client.post('/api/pipeline/runs/', {'file': upload})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    @patch('core.pipeline_api.rerun_pipeline')
    def test_visual_workflow_executes_real_canonical_pipeline(self, mocked_rerun):
        mocked_rerun.return_value = {
            'run_id': 'run_new',
            'stages': [
                {'key': 'standardization', 'status': 'completed'},
                {'key': 'cleaning', 'status': 'completed'},
                {'key': 'selection', 'status': 'completed'},
                {'key': 'modeling', 'status': 'completed'},
                {'key': 'optimization', 'status': 'skipped'},
                {'key': 'review', 'status': 'skipped'},
                {'key': 'report', 'status': 'skipped'},
            ],
        }
        body = {
            'run_id': 'run_old',
            'nodes': [
                {'id': 'source', 'type': 'source', 'config': {}},
                {'id': 'clean', 'type': 'cleaning', 'config': {'resample': '30s'}},
                {'id': 'lag', 'type': 'lag', 'config': {'maxLag': 45}},
                {'id': 'model', 'type': 'identification', 'config': {}},
            ],
            'edges': [
                {'from': 'source', 'to': 'clean'},
                {'from': 'clean', 'to': 'lag'},
                {'from': 'lag', 'to': 'model'},
            ],
        }
        response = self.client.post('/api/pipeline/workflows/execute/', data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()['data']
        self.assertEqual(payload['workflow']['mode'], 'canonical_backend_execution')
        self.assertEqual(payload['workflow']['executed_through'], 'modeling')
        mocked_rerun.assert_called_once_with('run_old', resample_rule='30s', max_lag=45, stop_after='modeling')

    @patch('core.pipeline_api.rerun_pipeline')
    def test_visual_workflow_rejects_cycle_without_execution(self, mocked_rerun):
        body = {
            'run_id': 'run_old',
            'nodes': [{'id': 'source', 'type': 'source'}, {'id': 'clean', 'type': 'cleaning'}],
            'edges': [{'from': 'source', 'to': 'clean'}, {'from': 'clean', 'to': 'source'}],
        }
        response = self.client.post('/api/pipeline/workflows/execute/', data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 422)
        mocked_rerun.assert_not_called()


class SecurityApiTests(TestCase):
    def test_unsafe_api_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        denied = client.post('/api/agent/plans/', data=json.dumps({'message': '分析数据'}), content_type='application/json')
        self.assertEqual(denied.status_code, 403)
        session = client.get('/api/security/session/')
        token = session.cookies['csrftoken'].value
        accepted = client.post(
            '/api/agent/plans/', data=json.dumps({'message': '分析数据'}),
            content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 201, accepted.content)

    @override_settings(PROCESSPILOT_REQUIRE_AUTH=True)
    def test_production_api_requires_authenticated_session(self):
        client = Client()
        denied = client.get('/api/agent/skills/')
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.json()['code'], 'authentication_required')
        user = get_user_model().objects.create_user(username='engineer', password='safe-test-password')
        client.force_login(user)
        accepted = client.get('/api/agent/skills/')
        self.assertEqual(accepted.status_code, 200)


class RuntimeRetentionTests(SimpleTestCase):
    def test_retention_is_dry_run_by_default_and_preserves_latest(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / 'runtime' / 'pipeline_runs'
            skills = root / 'runtime' / 'agent_skill_runs'
            runs.mkdir(parents=True)
            skills.mkdir(parents=True)
            for name in ('old', 'latest'):
                folder = runs / name
                folder.mkdir()
                (folder / 'snapshot.json').write_text('{}')
            (runs / 'latest.json').write_text(json.dumps({'run_id': 'latest'}))
            old_skill = skills / 'skillrun_old.json'
            old_skill.write_text('{}')
            old_timestamp = time.time() - 40 * 86400
            os.utime(runs / 'old', (old_timestamp, old_timestamp))
            os.utime(old_skill, (old_timestamp, old_timestamp))

            preview = prune_runtime(root, keep=1, days=30)
            self.assertEqual(preview['mode'], 'dry-run')
            self.assertTrue((runs / 'old').exists())
            applied = prune_runtime(root, keep=1, days=30, apply=True)
            self.assertEqual(applied['candidate_count'], 2)
            self.assertFalse((runs / 'old').exists())
            self.assertFalse(old_skill.exists())
            self.assertTrue((runs / 'latest').exists())

class OptimizationServiceTests(SimpleTestCase):
    def test_benchmark_evaluation_is_reproducible(self):
        first = evaluate_candidate(PROJECT_CODE, 20260731, DEFAULT_INITIAL_CANDIDATE)
        second = evaluate_candidate(PROJECT_CODE, 20260731, DEFAULT_INITIAL_CANDIDATE)

        self.assertEqual(first, second)
        self.assertGreater(first['metrics']['fit'], 0.5)
        self.assertLess(first['metrics']['fit'], 0.95)
        self.assertGreater(first['diagnostics']['selected_samples'], 100)
        self.assertGreater(first['diagnostics']['validation_samples'], 30)
        self.assertIn('18 步自由运行', first['diagnostics']['evaluator'])
        self.assertEqual(len(first['diagnostics']['effective_signature']), 12)

    def test_five_parameters_have_observable_effects(self):
        base = dict(DEFAULT_INITIAL_CANDIDATE)
        dynamic_low = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'dynamic_threshold': 0.20})
        dynamic_high = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'dynamic_threshold': 0.70})
        strict_outlier = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'outlier_sigma': 1.5})
        loose_outlier = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'outlier_sigma': 4.0})
        reduce_collinearity = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'collinearity_threshold': 0.60})
        retain_collinearity = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'collinearity_threshold': 0.94})
        short_lag_search = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'lag_max_seconds': 60})
        long_lag_search = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'lag_max_seconds': 240})
        short_segments = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'min_segment_minutes': 4})
        long_segments = evaluate_candidate(PROJECT_CODE, 20260731, {**base, 'min_segment_minutes': 12})

        self.assertGreater(dynamic_low['metrics']['coverage'] - dynamic_high['metrics']['coverage'], 0.25)
        self.assertGreater(abs(dynamic_low['metrics']['fit'] - dynamic_high['metrics']['fit']), 0.05)
        self.assertNotEqual(
            strict_outlier['diagnostics']['clipped_points'],
            loose_outlier['diagnostics']['clipped_points'],
        )
        self.assertGreater(
            abs(strict_outlier['metrics']['overall_score'] - loose_outlier['metrics']['overall_score']),
            0.5,
        )
        self.assertEqual(reduce_collinearity['diagnostics']['feature_count'], 5)
        self.assertEqual(retain_collinearity['diagnostics']['feature_count'], 6)
        self.assertGreater(long_lag_search['metrics']['cost'] - short_lag_search['metrics']['cost'], 0.20)
        self.assertGreater(long_segments['metrics']['coverage'] - short_segments['metrics']['coverage'], 0.20)

        signatures = {
            result['diagnostics']['effective_signature']
            for result in (
                dynamic_low,
                dynamic_high,
                strict_outlier,
                loose_outlier,
                reduce_collinearity,
                retain_collinearity,
                short_lag_search,
                long_lag_search,
                short_segments,
                long_segments,
            )
        }
        self.assertGreaterEqual(len(signatures), 7)

    def test_candidate_values_are_clamped_and_stepped(self):
        candidate = normalize_candidate({
            'dynamic_threshold': 0.999,
            'outlier_sigma': 1.56,
            'collinearity_threshold': 0.1,
            'lag_max_seconds': 83,
            'min_segment_minutes': 99,
        })
        self.assertEqual(candidate['dynamic_threshold'], 0.70)
        self.assertEqual(candidate['outlier_sigma'], 1.6)
        self.assertEqual(candidate['collinearity_threshold'], 0.60)
        self.assertEqual(candidate['lag_max_seconds'], 80)
        self.assertEqual(candidate['min_segment_minutes'], 20)

    def test_benchmark_snapshot_identifies_project_and_seed(self):
        first = benchmark_snapshot_id(PROJECT_CODE, 20260731)
        repeated = benchmark_snapshot_id(PROJECT_CODE, 20260731)
        other_project = benchmark_snapshot_id('OTHER-01', 20260731)
        other_seed = benchmark_snapshot_id(PROJECT_CODE, 20260732)

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, other_project)
        self.assertNotEqual(first, other_seed)
        self.assertIn('seed-20260731', first)


class OptimizationApiTests(TestCase):
    def create_study(self, **overrides):
        payload = {
            'project_code': PROJECT_CODE,
            'project_name': PROJECT_NAME,
            'dataset_mode': 'synthetic_benchmark',
            'total_rounds': 12,
            'run_mode': 'auto_converge',
            'random_seed': 20260731,
            'initial_candidate': DEFAULT_INITIAL_CANDIDATE,
            **overrides,
        }
        return self.client.post(
            '/api/optimization/studies/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def run_to_completion(self, study_id, max_calls=16):
        snapshot = None
        for _ in range(max_calls):
            response = self.client.post(f'/api/optimization/studies/{study_id}/step/')
            self.assertEqual(response.status_code, 200, response.content)
            snapshot = response.json()['data']
            if snapshot['status'] in ('completed', 'accepted'):
                return snapshot
        self.fail(f'寻优任务 {study_id} 在 {max_calls} 次调用后仍未结束')

    @patch('core.optimization_api.get_run')
    def test_uploaded_csv_pipeline_result_can_be_registered(self, mocked_get_run):
        mocked_get_run.return_value = {
            'run_id': 'real_run', 'original_name': 'plant.csv',
            'results': {
                'cleaning': {'selected_segment_count': 6, 'config': {'dynamic_threshold': .3}, 'split': {'seconds': 10}},
                'modeling': {'config': {'family': 'ARX'}},
                'optimization': {
                    'best_round': 2,
                    'stopping': {'stop_reason': '真实搜索完成'},
                    'iterations': [
                        {'round': 1, 'status': 'completed', 'r2': .70, 'rmse': .2, 'coverage': .72, 'score': 78, 'top_k': 5, 'max_lag': 30},
                        {'round': 2, 'status': 'completed', 'r2': .76, 'rmse': .18, 'coverage': .75, 'score': 84, 'top_k': 8, 'max_lag': 40},
                    ],
                },
            },
        }
        response = self.create_study(dataset_mode='uploaded_csv', pipeline_run_id='real_run')
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()['data']
        self.assertEqual(data['pipeline_run_id'], 'real_run')
        self.assertEqual(data['dataset_mode'], 'uploaded_csv')
        self.assertEqual(data['evaluation_profile']['trust_level'], 'offline_real_data')
        self.assertEqual(data['best_iteration']['round'], 2)
        self.assertEqual(len(data['iterations']), 2)

    @staticmethod
    def reproducible_projection(snapshot):
        return [
            {
                'round': row['round'],
                'params': row['params'],
                'metrics': row['metrics'],
                'signature': row['diagnostics']['effective_signature'],
                'failures': row['constraint_failures'],
                'decision_code': row['decision_code'],
                'equivalent_to_round': row['equivalent_to_round'],
            }
            for row in snapshot['iterations']
        ]

    def test_auto_mode_stops_between_eight_and_twelve_rounds_with_valid_best(self):
        created = self.create_study()
        self.assertEqual(created.status_code, 201, created.content)
        created_data = created.json()['data']
        self.assertEqual(created_data['contract_version'], 'clso.study.v2')
        self.assertEqual(created_data['stopping']['min_rounds'], 8)
        self.assertEqual(created_data['stopping']['max_rounds'], 12)
        self.assertEqual(created_data['evaluation_profile']['trust_level'], 'simulation_validated')
        self.assertFalse(created_data['evaluation_profile']['production_ready'])
        self.assertEqual(created_data['input_artifact']['snapshot_id'], created_data['evaluation_profile']['dataset_snapshot'])
        self.assertEqual(created_data['input_artifact']['sampling_period_seconds'], 10)

        final = self.run_to_completion(created_data['id'])

        self.assertEqual(final['status'], 'completed')
        self.assertTrue(final['early_stopped'])
        self.assertGreaterEqual(final['current_round'], 8)
        self.assertLess(final['current_round'], 12)
        self.assertEqual(final['progress'], 100)
        self.assertLess(final['round_progress'], 100)
        self.assertIn('连续', final['stop_reason'])
        self.assertEqual(len(final['iterations']), final['current_round'])

        best = final['best_iteration']
        self.assertIsNotNone(best)
        self.assertFalse(best['constraint_failures'])
        self.assertTrue(all(check['passed'] for check in best['constraint_checks'].values()))
        valid_iterations = [row for row in final['iterations'] if not row['constraint_failures']]
        expected_best = max(valid_iterations, key=lambda row: row['metrics']['overall_score'])
        self.assertEqual(best['id'], expected_best['id'])

        fits = {round(row['metrics']['fit'], 3) for row in final['iterations']}
        coverages = {round(row['metrics']['coverage'], 3) for row in final['iterations']}
        scores = {round(row['metrics']['overall_score'], 1) for row in final['iterations']}
        self.assertGreaterEqual(len(fits), 5)
        self.assertGreaterEqual(len(coverages), 5)
        self.assertGreaterEqual(len(scores), 5)

        signatures = [row['diagnostics']['effective_signature'] for row in final['iterations']]
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertTrue(all(row['equivalent_to_round'] is None for row in final['iterations']))

        accepted = self.client.post(f"/api/optimization/studies/{final['id']}/accept/")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        accepted_data = accepted.json()['data']
        self.assertEqual(accepted_data['status'], 'accepted')
        self.assertEqual(accepted_data['accepted_iteration_id'], best['id'])
        self.assertEqual(accepted_data['accepted_strategy']['contract_version'], 'clso.accepted-strategy.v1')
        self.assertEqual(accepted_data['accepted_strategy']['iteration']['id'], best['id'])

    def test_fixed_mode_runs_exactly_requested_rounds(self):
        created = self.create_study(
            total_rounds=8,
            run_mode='fixed',
            stopping={'min_rounds': 4, 'patience': 2, 'min_score_improvement': 5.0},
        )
        self.assertEqual(created.status_code, 201, created.content)
        study_id = created.json()['data']['id']

        final = self.run_to_completion(study_id)

        self.assertEqual(final['status'], 'completed')
        self.assertEqual(final['run_mode'], 'fixed')
        self.assertEqual(final['current_round'], 8)
        self.assertEqual(len(final['iterations']), 8)
        self.assertFalse(final['early_stopped'])
        self.assertEqual(final['stop_reason'], '达到最大轮次 8 轮')

        repeated = self.client.post(f'/api/optimization/studies/{study_id}/step/')
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(len(repeated.json()['data']['iterations']), 8)

    def test_equivalent_signature_is_not_promoted_or_recommended_twice(self):
        created = self.create_study(total_rounds=2, run_mode='fixed')
        self.assertEqual(created.status_code, 201, created.content)
        study_id = created.json()['data']['id']

        first_response = self.client.post(f'/api/optimization/studies/{study_id}/step/')
        self.assertEqual(first_response.status_code, 200, first_response.content)
        first_run = OptimizationRun.objects.get(study_id=study_id, round_number=1)
        duplicate_result = copy.deepcopy(first_run.candidate_parameters)
        duplicate_result['params']['dynamic_threshold'] = 0.23
        duplicate_result['metrics']['overall_score'] += 5.0

        with (
            patch('core.optimization_api.suggest_candidate', return_value=duplicate_result['params']),
            patch('core.optimization_api.evaluate_candidate', return_value=duplicate_result),
        ):
            second_response = self.client.post(f'/api/optimization/studies/{study_id}/step/')

        self.assertEqual(second_response.status_code, 200, second_response.content)
        final = second_response.json()['data']
        second = final['iterations'][1]
        self.assertEqual(second['decision_code'], 'equivalent')
        self.assertEqual(second['equivalent_to_round'], 1)
        self.assertFalse(second['is_best'])
        self.assertEqual(final['best_iteration']['id'], first_run.id)

    def test_infeasible_study_cannot_be_accepted(self):
        impossible_constraints = {
            'target_fit': 1.0,
            'min_coverage': 1.0,
            'max_rmse': 0.01,
            'min_valid_segments': 100,
        }
        created = self.create_study(
            total_rounds=3,
            run_mode='fixed',
            stopping={'min_rounds': 3, 'patience': 2, 'min_score_improvement': 0.2},
            constraints=impossible_constraints,
        )
        self.assertEqual(created.status_code, 201, created.content)
        final = self.run_to_completion(created.json()['data']['id'])

        self.assertEqual(final['current_round'], 3)
        self.assertTrue(final['best_iteration']['constraint_failures'])
        self.assertFalse(all(check['passed'] for check in final['best_iteration']['constraint_checks'].values()))

        rejected = self.client.post(f"/api/optimization/studies/{final['id']}/accept/")
        self.assertEqual(rejected.status_code, 409)
        self.assertIn('未找到满足全部硬约束的策略', rejected.json()['message'])
        study = OptimizationStudy.objects.get(pk=final['id'])
        self.assertEqual(study.status, 'completed')
        self.assertIsNone(study.accepted_run_id)

    def test_two_fixed_runs_with_same_seed_are_reproducible(self):
        first_created = self.create_study(total_rounds=8, run_mode='fixed')
        second_created = self.create_study(total_rounds=8, run_mode='fixed')
        self.assertEqual(first_created.status_code, 201, first_created.content)
        self.assertEqual(second_created.status_code, 201, second_created.content)

        first = self.run_to_completion(first_created.json()['data']['id'])
        second = self.run_to_completion(second_created.json()['data']['id'])

        self.assertEqual(self.reproducible_projection(first), self.reproducible_projection(second))
        self.assertEqual(first['best_iteration']['round'], second['best_iteration']['round'])
        self.assertEqual(first['stop_reason'], second['stop_reason'])

    def test_history_can_be_filtered_and_records_can_be_exported(self):
        created = self.create_study(total_rounds=2, run_mode='fixed')
        self.create_study(project_code='OTHER-01', project_name='其他项目')
        study_id = created.json()['data']['id']
        self.run_to_completion(study_id)

        response = self.client.get(f'/api/optimization/studies/?project_code={PROJECT_CODE}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['project_code'], PROJECT_CODE)

        csv_response = self.client.get(f'/api/optimization/studies/{study_id}/export/?format=csv')
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('text/csv', csv_response['Content-Type'])
        self.assertIn('综合分'.encode(), csv_response.content)

    def test_rejects_invalid_stopping_options_and_premature_accept(self):
        invalid_rounds = self.create_study(total_rounds=1)
        self.assertEqual(invalid_rounds.status_code, 400)

        invalid_mode = self.create_study(run_mode='unknown')
        self.assertEqual(invalid_mode.status_code, 400)

        invalid_stopping = self.create_study(
            total_rounds=8,
            stopping={'min_rounds': 9, 'patience': 3, 'min_score_improvement': 0.2},
        )
        self.assertEqual(invalid_stopping.status_code, 400)

        created = self.create_study(total_rounds=2, run_mode='fixed')
        study_id = created.json()['data']['id']
        premature = self.client.post(f'/api/optimization/studies/{study_id}/accept/')
        self.assertEqual(premature.status_code, 409)
        self.assertEqual(OptimizationStudy.objects.get(pk=study_id).status, 'ready')

    def test_custom_search_space_is_used_during_real_evaluation(self):
        search_space = {
            'dynamic_threshold': {'min': 0.80, 'max': 0.90, 'step': 0.01},
            'outlier_sigma': {'min': 4.20, 'max': 5.00, 'step': 0.10},
            'collinearity_threshold': {'min': 0.96, 'max': 0.99, 'step': 0.01},
            'lag_max_seconds': {'min': 250, 'max': 300, 'step': 10},
            'min_segment_minutes': {'min': 21, 'max': 25, 'step': 1},
        }
        initial = {
            'dynamic_threshold': 0.85,
            'outlier_sigma': 4.5,
            'collinearity_threshold': 0.98,
            'lag_max_seconds': 280,
            'min_segment_minutes': 23,
        }
        created = self.create_study(
            total_rounds=2,
            run_mode='fixed',
            search_space=search_space,
            initial_candidate=initial,
        )
        self.assertEqual(created.status_code, 201, created.content)

        stepped = self.client.post(f"/api/optimization/studies/{created.json()['data']['id']}/step/")
        self.assertEqual(stepped.status_code, 200, stepped.content)
        self.assertEqual(stepped.json()['iteration']['params'], initial)

    def test_reaching_max_round_is_not_reported_as_early_stop(self):
        valid_initial = {
            'dynamic_threshold': 0.42,
            'outlier_sigma': 2.6,
            'collinearity_threshold': 0.84,
            'lag_max_seconds': 140,
            'min_segment_minutes': 8,
        }
        created = self.create_study(
            total_rounds=2,
            run_mode='auto_converge',
            stopping={'min_rounds': 2, 'patience': 2, 'min_score_improvement': 0.2},
            initial_candidate=valid_initial,
        )
        study_id = created.json()['data']['id']
        first = self.client.post(f'/api/optimization/studies/{study_id}/step/')
        self.assertEqual(first.status_code, 200, first.content)
        self.assertFalse(first.json()['data']['best_iteration']['constraint_failures'])
        OptimizationStudy.objects.filter(pk=study_id).update(no_improvement_rounds=2)

        final = self.client.post(f'/api/optimization/studies/{study_id}/step/')
        self.assertEqual(final.status_code, 200, final.content)
        data = final.json()['data']
        self.assertEqual(data['current_round'], 2)
        self.assertFalse(data['early_stopped'])
        self.assertEqual(data['stop_reason'], '达到最大轮次 2 轮')

    def test_malformed_payloads_return_400_and_do_not_create_studies(self):
        malformed_payloads = [
            [],
            {'project_code': PROJECT_CODE, 'project_name': PROJECT_NAME, 'search_space': {'dynamic_threshold': []}},
            {'project_code': PROJECT_CODE, 'project_name': PROJECT_NAME, 'random_seed': float('inf')},
            {'project_code': PROJECT_CODE, 'project_name': PROJECT_NAME, 'constraints': {'target_fit': float('nan')}},
            {'project_code': 'BAD\nHEADER', 'project_name': PROJECT_NAME},
        ]
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    '/api/optimization/studies/',
                    data=json.dumps(payload),
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(OptimizationStudy.objects.count(), 0)

    def test_transient_database_conflict_does_not_fail_study(self):
        from django.db import OperationalError

        created = self.create_study(total_rounds=2, run_mode='fixed')
        study_id = created.json()['data']['id']
        with patch('core.optimization_api.suggest_candidate', side_effect=OperationalError('database is locked')):
            response = self.client.post(f'/api/optimization/studies/{study_id}/step/')

        self.assertEqual(response.status_code, 409, response.content)
        study = OptimizationStudy.objects.get(pk=study_id)
        self.assertEqual(study.status, 'ready')
        self.assertEqual(study.current_round, 0)

    def test_export_uses_header_safe_filename(self):
        created = self.create_study(project_code='FUR/Line 2', total_rounds=2, run_mode='fixed')
        self.assertEqual(created.status_code, 201, created.content)
        study_id = created.json()['data']['id']
        response = self.client.get(f'/api/optimization/studies/{study_id}/export/?format=json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="FUR_Line_2_optimization_{study_id}.json"')
