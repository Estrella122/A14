"""Regression tests for causal selection, independent evaluation and truthful skills."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.test import SimpleTestCase
from core.services import pipeline
from core.skills.runtime import execute_skill_plan, plan_skills

with pipeline._module_path(pipeline.INTEGRATIONS_DIR / 'identification'):
    import validated_modeling as vm
with pipeline._module_path(pipeline.INTEGRATIONS_DIR / 'data_cleaning/src'):
    from data_cleaning_agent import DataCleaningSelectionAgent


def frame(n=600):
    rng = np.random.default_rng(942)
    u = rng.normal(0, 1, n)
    y = np.zeros(n)
    for i in range(3, n): y[i] = .7 * y[i-1] + .9 * u[i-3] + rng.normal(0, .02)
    return pd.DataFrame({'timestamp': pd.date_range('2026-01-01', periods=n, freq='10s'), 'u': u, 'y': y})


class CausalModelingTests(SimpleTestCase):
    def test_lags_do_not_cross_discontinuous_windows(self):
        data = frame(100).iloc[list(range(20)) + list(range(80, 100))].reset_index(drop=True)
        shifted = vm.shifted(data, 'u', 3, 10)
        self.assertTrue(shifted.iloc[20:23].isna().all())
        self.assertEqual(shifted.iloc[23], data.u.iloc[20])
        with self.assertRaises(ValueError): vm.shifted(data, 'u', -1, 10)

    def test_future_perturbation_cannot_change_past_features(self):
        data = frame(100)
        original = vm.features(data, 'y', ['u'], {'u': 5}, 3, 10)
        data.loc[60:, ['u', 'y']] = 1e8
        changed = vm.features(data, 'y', ['u'], {'u': 5}, 3, 10)
        pd.testing.assert_frame_equal(original.iloc[:61], changed.iloc[:61])

    def test_train_only_delay_recovers_known_input_lag(self):
        data = frame()
        table = vm.estimate_training_delays(data, 'y', ['u'], 10, 12)
        self.assertEqual(int(table.iloc[0].delay_samples), 3)
        self.assertGreaterEqual(int(table.iloc[0].delay_samples), 0)

    def test_selection_top_k_matches_export_rows_even_with_many_good_windows(self):
        data = frame(300).set_index('timestamp')
        segments = pd.DataFrame([{'start_time': data.index[i], 'end_time': data.index[i+29],
                                  'level': '优质动态段'} for i in range(0, 240, 30)])
        selected = pipeline._select_modeling_rows(data, segments, top_k=2)
        self.assertEqual(len(selected), 60)
        self.assertEqual(selected.index.max(), data.index[59])

    def test_holdout_targets_are_common_and_test_does_not_refit(self):
        data = frame(600)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data.iloc[:360].to_csv(root/'train.csv', index=False)
            data.iloc[360:480].to_csv(root/'validation.csv', index=False)
            data.iloc[480:].to_csv(root/'test.csv', index=False)
            target_hashes = []
            for lag in (4, 10):
                out = root / f'model{lag}'
                summary = vm.run_validated_modeling(root/'train.csv', 'y', ['u'], out,
                                                    root/'validation.csv', 15, 10, lag)
                target_hashes.append(summary['diagnostics']['evaluation_target_hash'])
                state = out/'03_system_identification/fitted_state.json'
                before = state.read_bytes()
                before_metrics = json.loads((out/'03_system_identification/model_metrics.json').read_text())
                self.assertNotIn('test', before_metrics)
                self.assertEqual(len(summary['order_search']), 12)
                metrics, diagnostics = vm.finalize_test(out, root/'test.csv')
                self.assertEqual(state.read_bytes(), before)
                self.assertEqual(metrics['validation'], before_metrics['validation'])
                self.assertIn('persistence', diagnostics['test'])
                self.assertIn('multi_step', diagnostics['test'])
                self.assertIn('free_simulation', diagnostics['test'])
                self.assertEqual(metrics['test']['n_samples'], diagnostics['test']['persistence']['n_samples'])
            self.assertEqual(len(set(target_hashes)), 1)

    def test_recursive_prediction_does_not_feed_back_measured_future_outputs(self):
        data = frame(100)
        state = {'output':'y', 'seconds':10, 'inputs':[], 'delays':{}, 'order':1, 'coef':[0., .5]}
        _, d, _, _ = vm.evaluation(data, state, 15, 'test')
        idx = np.arange(25, 100)
        actual = data.y.to_numpy()[idx]
        expected = (0.5 ** 10) * data.y.to_numpy()[idx-10]
        expected_rmse = np.sqrt(np.mean((actual-expected)**2))
        self.assertAlmostEqual(d['multi_step']['metrics']['rmse'], expected_rmse, places=10)

    def test_firx_evaluates_sparse_targets_without_interpolating_truth(self):
        data = frame(360)[['timestamp', 'u']].copy()
        data['y'] = np.nan
        observed = np.arange(12, len(data), 12)
        data.loc[observed, 'y'] = data.loc[observed - 1, 'u'].to_numpy()
        state = {
            'output': 'y', 'seconds': 10, 'inputs': ['u'], 'delays': {'u': 1},
            'order': 1, 'coef': [0., 1.], 'family': 'FIRX',
            'evaluation_inputs': ['u'],
        }
        metrics, diagnostics, prediction, _ = vm.evaluation(data, state, 5, 'test')
        self.assertGreater(len(prediction), 20)
        self.assertAlmostEqual(metrics['rmse'], 0., places=10)
        self.assertFalse(diagnostics['multi_step']['applicable'])
        self.assertFalse(diagnostics['free_simulation']['applicable'])

    def test_unknown_snr_and_missing_skill_evidence_never_succeed(self):
        self.assertIsNone(DataCleaningSelectionAgent.estimate_snr(pd.Series(np.ones(30))))
        plan = plan_skills('提取加热炉高信噪比动态数据，处理共线性后闭环寻优', 'old_run')
        snapshot = {'run_id':'old_run', 'results':{'cleaning':{'selected_segment_count':69}, 'modeling':{'metrics':{'test':{'r2':.99}}}}}
        with TemporaryDirectory() as tmp, patch('core.skills.runtime.RUNS_DIR', Path(tmp)):
            result = execute_skill_plan(plan, snapshot)
        snr = next(r for r in result['executions'] if r['skill_id']=='signal_noise_ratio_estimator')
        order = next(r for r in result['executions'] if r['skill_id']=='arx_structure_order_selector')
        self.assertIn(snr['status'], {'blocked', 'unavailable'})
        self.assertEqual(order['status'], 'unavailable')
        self.assertEqual(result['summary']['executed'], 0)
        self.assertFalse(any(r['activity']=='executed' for r in result['executions']))

    def test_snr_proxy_distinguishes_noise_and_reports_power(self):
        rng = np.random.default_rng(123)
        signal = 10 * np.sin(np.linspace(0, 6, 600))
        clean = DataCleaningSelectionAgent.snr_details(pd.Series(signal+rng.normal(0,.1,600)))
        noisy = DataCleaningSelectionAgent.snr_details(pd.Series(signal+rng.normal(0,5,600)))
        self.assertGreater(clean['snr_db'], noisy['snr_db'] + 15)
        self.assertFalse(clean['calibrated'])
        self.assertGreater(clean['noise_power'], 0)

    def test_cleaner_never_uses_future_samples_or_fills_output_truth(self):
        spec = {'u': {'role':'input','min':-100,'max':100,'max_step':100},
                'y': {'role':'output','min':-100,'max':100,'max_step':100}}
        original = frame(100)
        changed = original.copy()
        original.loc[20, ['u','y']] = np.nan
        changed.loc[20, ['u','y']] = np.nan
        changed.loc[60:, ['u','y']] = 90
        def clean(data):
            a = DataCleaningSelectionAgent(spec)
            return a.detect_and_repair_anomalies(a.process_missing_values(a.align_timestamp(data)))
        a, b = clean(original), clean(changed)
        pd.testing.assert_frame_equal(a.iloc[:60], b.iloc[:60])
        self.assertTrue(pd.isna(a.y.iloc[20]))
        self.assertEqual(a.u.iloc[20], a.u.iloc[19])

    def test_positive_single_step_r2_does_not_override_failed_simulation(self):
        model = {'metrics':{'test':{'r2':.999}}, 'config':{'family':'ARX'},
                 'diagnostics':{'stable_ar_poles':True, 'test':{
                     'rmse_improvement_over_persistence_pct':20,
                     'multi_step':{'metrics':{'rmse':1}, 'persistence':{'rmse':2}},
                     'free_simulation':{'diverged':False, 'metrics':{'r2':-.2}}}}}
        with TemporaryDirectory() as tmp:
            result = pipeline._review({'data_decision':{'status':'ready'}}, {'overall_score':95}, model, Path(tmp))
        self.assertFalse(result['passed'])
        self.assertTrue(any('自由仿真' in item for item in result['blockers']))
        dynamic_gate = next(
            gate for gate in result['deployment_readiness']['offline_model']['gates']
            if gate['id'] == 'dynamic_validity'
        )
        self.assertFalse(dynamic_gate['passed'])
        self.assertIn('free_simulation_r2=-0.2', dynamic_gate['evidence'])

    def test_diverged_simulation_with_null_metrics_is_reviewed_not_crashed(self):
        model = {'metrics': {'test': {'r2': .88}}, 'config': {'family': 'ARX'},
                 'diagnostics': {'stable_ar_poles': True, 'test': {
                     'rmse_improvement_over_persistence_pct': 2,
                     'multi_step': {'metrics': {'rmse': 1}, 'persistence': {'rmse': 2}},
                     'free_simulation': {'diverged': True, 'metrics': None}}}}
        with TemporaryDirectory() as tmp:
            result = pipeline._review({'data_decision': {'status': 'ready'}}, {'overall_score': 87}, model, Path(tmp))

        self.assertFalse(result['passed'])
        self.assertTrue(any('自由仿真' in item for item in result['blockers']))
        dynamic_gate = next(gate for gate in result['deployment_readiness']['offline_model']['gates'] if gate['id'] == 'dynamic_validity')
        self.assertIn('free_simulation_r2=None, diverged=True', dynamic_gate['evidence'])

    def test_explicit_unsupported_parameter_does_not_silently_rerun(self):
        from core.services.agent_chat import chat
        snapshot = {'run_id':'example', 'results':{'standardization':{'scenario':{'scenario_name':'钢铁高炉铁水质量预测'}}}}
        with patch('core.services.agent_chat.get_run', return_value=snapshot), patch('core.services.agent_chat.rerun_pipeline') as rerun:
            with self.assertRaisesRegex(pipeline.PipelineError, 'top_k'):
                chat('提取加热炉动态数据 top_k=3')
            rerun.assert_not_called()
