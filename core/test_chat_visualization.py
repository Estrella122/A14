import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.test import SimpleTestCase, RequestFactory

from core.skills.registry import get_registry
from core.skills.md_planning import plan_from_manifests
from core.skills.task_understanding import understand_task
from core.skills.visualization import build_charts, render_svg
from core.skills.chart_artifacts import public_charts
from core.agent_api import agent_skill_chart


class ChartRequestTests(SimpleTestCase):
    def test_polite_requests_select_existing_visualization_skill(self):
        registry = get_registry()
        for text in ('能给我图形可视化吗', '帮我画个图', '能不能帮我画图', '展示当前数据曲线', '给我生成能耗趋势图'):
            with self.subTest(text=text):
                task = understand_task(text)
                self.assertEqual(task['requested_outputs'], ['charts'])
                plan = plan_from_manifests(text, task, {'run_id': 'test', 'results': {}}, 'test', registry)
                self.assertIn('engineering_visualization_builder', plan['direct_skill_ids'])
                self.assertEqual(plan['mode'], 'execute')
                self.assertFalse(plan['analysis']['needs_clarification'])
                self.assertEqual([node['id'] for node in plan['analysis']['execution_plan']['core']['steps']], ['engineering_visualization_builder'])

    def test_explanations_negations_and_hypotheticals_do_not_execute(self):
        registry = get_registry()
        for text in ('解释一下可视化是什么意思', '如何生成图表', '不要生成图表', '如果让你画图会怎样', '这个按钮写着“能给我图形可视化吗”'):
            with self.subTest(text=text):
                task = understand_task(text)
                self.assertNotIn('charts', task['requested_outputs'])
                plan = plan_from_manifests(text, task, None, None, registry)
                if plan:
                    self.assertNotEqual(plan['mode'], 'execute')


class ChartRenderingTests(SimpleTestCase):
    def test_real_csv_without_model_generates_bounded_charts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.csv'
            pd.DataFrame({'energy': np.arange(2000.), 'other': np.arange(2000.) / 2}).to_csv(path, index=False)
            charts, warnings = build_charts({}, {}, {'scene_context': {'target_column': 'energy', 'units': {'energy': 'kWh'}}}, tmp, lambda *_: path)
            self.assertEqual(len(charts), 2)
            self.assertEqual(charts[0]['source_rows'], 2000)
            self.assertEqual(charts[0]['point_count'], 500)
            self.assertEqual(charts[0]['unit'], 'kWh')
            self.assertFalse(warnings)
            self.assertTrue(Path(charts[0]['path']).is_file())

    def test_missing_values_are_not_connected_and_labels_are_escaped(self):
        svg, _ = render_svg('<script>alert(1)</script>', [('x', np.array([1., np.nan, 3.]))])
        self.assertNotIn('<script>', svg)
        self.assertNotIn('stroke-width="1.8"', svg)
        self.assertIsNone(render_svg('empty', [('x', [np.nan, np.inf])]))

    def test_no_data_has_no_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            charts, _ = build_charts({}, {}, {}, tmp, lambda *_: None)
            self.assertEqual(charts, [])

    def test_specific_prediction_request_does_not_fall_back_to_generic_chart(self):
        with tempfile.TemporaryDirectory() as tmp:
            charts, warnings = build_charts({}, {'constraints': {'chart_request': '给我预测对比图'}}, {}, tmp, lambda *_: None)
            self.assertEqual(charts, [])
            self.assertIn('缺少真实预测', warnings[0])


class ChartEndpointTests(SimpleTestCase):
    def test_only_registered_files_inside_run_directory_are_served(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'skillrun_test' / 'plot.svg'
            output.parent.mkdir()
            output.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            result = {'status': 'success', 'artifacts': [{'path': str(output)}], 'metrics': {'charts': [{'path': str(output), 'title': 'Actual data'}]}}
            payload = {'core_skill_execution_results': [result]}
            with patch('core.agent_api.get_skill_run', return_value=payload), patch('core.skills.runtime.RUNS_DIR', root):
                response = agent_skill_chart(RequestFactory().get('/'), 'skillrun_test', 0)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'image/svg+xml')
                response.close()
                self.assertEqual(agent_skill_chart(RequestFactory().get('/'), 'skillrun_other', 0).status_code, 404)
                self.assertEqual(agent_skill_chart(RequestFactory().get('/'), 'skillrun_test', 1).status_code, 404)
            public = public_charts('skillrun_test', payload)
            self.assertNotIn(str(root), json.dumps(public))
            result['artifacts'] = []
            self.assertEqual(public_charts('skillrun_test', payload), [])
