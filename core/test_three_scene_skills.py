"""Real repository datasets; unavailable normalized data must not be called PASS."""
import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from core.skills.context import build_scene_context
from core.skills.registry import get_registry
from core.skills.runtime import plan_skills
from core.skills.md_adapter import MarkdownExecutor
from core.services.scene_skill_pipeline import run_scene_skill_pipeline

ROOT = Path(__file__).resolve().parent.parent
DATASETS = {
    'industrial_dryer': ROOT/'演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv',
    'debutanizer_column': ROOT/'integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv',
    'blast_furnace': ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv',
}
CORE = {'missing_anomaly_cleaner','signal_noise_ratio_estimator','time_delay_estimator_compensator','collinearity_detector_reducer','arx_structure_order_selector'}


@override_settings(SKILL_MANIFEST_MODE='md')
class ThreeSceneSkillTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.logs = patch('core.skills.runtime.RUNS_DIR', Path(cls.temp.name)/'runs')
        cls.logs.start(); cls.addClassCleanup(cls.logs.stop)
        # Execution order intentionally follows dryer -> debutanizer -> furnace.
        cls.receipts = {key: run_scene_skill_pipeline(path, output_root=Path(cls.temp.name)/'inputs') for key,path in DATASETS.items()}

    def test_three_scene_context_resolution(self):
        targets = {'industrial_dryer':'product_moisture','debutanizer_column':'bottom_butane_content','blast_furnace':'hot_metal_si'}
        for scene, receipt in self.receipts.items():
            ctx = receipt['scene_context']
            self.assertEqual(scene,ctx['scenario_id'])
            self.assertEqual('timestamp',ctx['timestamp_column'])
            self.assertEqual(targets[scene],ctx['target_column'])
            self.assertTrue(ctx['input_columns'])
            self.assertTrue(all(name in ctx['units'] for name in ctx['input_columns']))
            separated = build_scene_context({'project_scene':'unrelated-project','runtime_trace':{'final_scene':scene}}).public()
            self.assertEqual(scene,separated['scenario_id'])
            self.assertEqual('unrelated-project',separated['metadata']['project_context_scene'])

    def test_common_skill_same_executor_across_scenes(self):
        first = next(iter(self.receipts.values()))
        self.assertEqual(12,len(first['skill_ids']))
        for receipt in self.receipts.values():
            for key in ('skill_ids','manifest_paths','executor_modules'):
                self.assertEqual(first[key],receipt[key])
            self.assertTrue(all(receipt['manifest_paths']))

    def test_no_scene_specific_algorithm_duplication(self):
        paths = [ROOT/'core/skills/stage_adapters.py']
        paths.extend(ROOT.joinpath(*skill.executor['module'].split('.')).with_suffix('.py') for skill in get_registry('md').list())
        for path in paths:
            tree = ast.parse(path.read_text())
            names = {node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str)}
            self.assertTrue(set(DATASETS).isdisjoint(names),str(path))

    def assert_pipeline(self,scene):
        receipt = self.receipts[scene]
        self.assertTrue(CORE.issubset(receipt['skill_ids']))
        rows = {row['skill_id']:row for row in receipt['executions']}
        self.assertNotIn('failed',{row['status'] for row in rows.values()})
        if scene == 'debutanizer_column':
            self.assertEqual('unavailable',receipt['status'])
            self.assertTrue(receipt['standardization']['mapping']['missing_required'])
            self.assertTrue(all(not row['audit']['executor_invoked'] for row in rows.values()))
            self.assertTrue(all(not row['metrics'] for row in rows.values()))
        else:
            for key in CORE:
                self.assertIn(rows[key]['status'],{'success','partial'})
                self.assertTrue(rows[key]['audit']['executor_invoked'])
            self.assertTrue(rows['arx_structure_order_selector']['metrics']['candidate_count'])
            self.assertFalse(rows['arx_structure_order_selector']['evidence'][0]['test_accessed'])
            self.assertIn('test',rows['system_identification_trainer']['metrics'])

    def test_blast_furnace_skill_pipeline(self): self.assert_pipeline('blast_furnace')
    def test_debutanizer_skill_pipeline(self): self.assert_pipeline('debutanizer_column')
    def test_industrial_dryer_skill_pipeline(self): self.assert_pipeline('industrial_dryer')

    def test_three_scene_result_contract(self):
        for receipt in self.receipts.values():
            for row in receipt['executions']:
                for key,kind in {'status':str,'metrics':dict,'artifacts':list,'evidence':list,'warnings':list,'suggested_next_skills':list}.items():
                    self.assertIsInstance(row[key],kind)
            snr = receipt['metrics']['signal_noise_ratio_estimator']
            if snr:
                self.assertIn('per_variable_snr',snr)
                self.assertIn('summary_snr',snr)
                self.assertTrue(all('signal_power' in item and 'noise_power' in item for item in snr['per_variable_snr']))

    def test_scene_config_driven_parameters(self):
        manifest = get_registry('md').get('signal_noise_ratio_estimator')
        from core.test_skill_md_runtime import snapshot_fixture
        snapshot = snapshot_fixture(self.temp.name)
        results = []
        for columns in (['air_flow'],['fuel','temperature']):
            context = {'default_parameters':{'columns':columns},'metadata':{}}
            result = MarkdownExecutor(manifest).execute(manifest.id,[],{}, {'scene_context':context}, {'snapshot':snapshot}, {'state':{},'execution_id':'config-test','output_dir':Path(self.temp.name)/'config'})
            self.assertEqual(columns,[r['field'] for r in result['metrics']['fields']])
            self.assertEqual(columns,result['audit']['parameter_snapshot']['columns'])
            results.append(result)
        self.assertEqual(results[0]['audit']['manifest_hash'],results[1]['audit']['manifest_hash'])
        self.assertEqual(results[0]['audit']['executor_module'],results[1]['audit']['executor_module'])
        self.assertNotEqual(results[0]['metrics'],results[1]['metrics'])

    def test_md_mode_three_scenes(self):
        for receipt in self.receipts.values():
            self.assertEqual('md_registry',receipt['skill_plan']['analysis']['routing_source'])
            self.assertTrue(all(row['manifest_source']=='SKILL.md' for row in receipt['skill_plan']['steps']))
            self.assertEqual(receipt['scene_context']['default_parameters']['max_lag'], receipt['parameters']['time_delay_estimator_compensator']['max_lag'])

    def test_api_compatibility_and_boundaries(self):
        response = self.client.get('/api/agent/skills/')
        self.assertEqual(200,response.status_code)
        self.assertEqual(13,response.json()['data']['total'])
        for message in ['介绍一下系统辨识','不要计算信噪比，只解释原理']:
            plan = plan_skills(message)
            self.assertFalse(plan.get('analysis',{}).get('execution_plan',{}).get('core',{}).get('steps'))
        response = self.client.post('/api/agent/plans/',data=json.dumps({'message':'分析当前场景的数据质量并判断是否适合 ARX 建模。'}),content_type='application/json')
        self.assertEqual(201,response.status_code)
