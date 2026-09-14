"""Final data evidence checks; synthetic unit fixtures never count as plant data."""
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pandas as pd
from django.test import SimpleTestCase, override_settings
from integrations.standardization.standard_agent.engine import StandardizationAgent
from core.services.dataset_evidence import restore_normalized_fields
from core.services.scene_skill_pipeline import run_scene_skill_pipeline
from core.skills.md_adapter import MarkdownExecutor
from core.skills.registry import get_registry

ROOT=Path(__file__).resolve().parents[1]


@override_settings(SKILL_MANIFEST_MODE='md')
class ThreeSceneFinalDataTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp=TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        logs=patch('core.skills.runtime.RUNS_DIR',Path(cls.temp.name)/'runs');logs.start();cls.addClassCleanup(logs.stop)
        cls.receipts={}
        for scene,path in [('debutanizer_column','integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv'),('industrial_dryer','演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv'),('blast_furnace','frontend/public/datasets/blast_furnace_real_720h.csv')]:
            cls.receipts[scene]=run_scene_skill_pipeline(ROOT/path,output_root=Path(cls.temp.name)/'inputs')

    def test_debutanizer_alias_resolution(self):
        columns=['timestamp','TOP_TEMPERATURE','top_pressure','reflux_flow','next_process_flow','tray_6_temperature','bottom_temp_a','bottom_temp_b','bottom_butane_content']
        r=StandardizationAgent().map_columns(columns,'debutanizer_column')
        self.assertEqual(1.0,r['required_coverage'])
        self.assertTrue(all(m['status']=='matched' for m in r['mappings']))
        # Header recognition is not proof that normalized values are physical.

    def test_debutanizer_gate_not_bypassed(self):
        r=self.receipts['debutanizer_column']
        self.assertEqual('debutanizer_column',r['scenario_id'])
        self.assertEqual('unavailable',r['status'])
        self.assertEqual({'bottom_temperature_a','bottom_temperature_b','top_temperature','tray6_temperature','top_pressure','next_process_flow','bottom_butane_content','reflux_flow'},set(r['standardization']['mapping']['missing_required']))
        for row in r['executions']:
            self.assertFalse(row['audit']['executor_invoked'])
            self.assertEqual({},row['metrics'])

    def test_debutanizer_inverse_transform_only_with_metadata(self):
        source=ROOT/'integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv'
        before=sha256(source.read_bytes()).hexdigest()
        for metadata in [None,{},json.loads((ROOT/'datasets/public/debutanizer/dataset_metadata.json').read_text())]:
            with self.assertRaises(ValueError):restore_normalized_fields(source,metadata,{'top_temperature':'degC'})
        self.assertEqual(before,sha256(source.read_bytes()).hexdigest())
        # A tiny explicit transform-unit fixture, never used for scene acceptance.
        path=Path(self.temp.name)/'normalized_unit_fixture.csv';path.write_text('U1\n0\n1\n')
        meta={'scenario_id':'debutanizer_column','source_file':path.name,'source_hash':sha256(path.read_bytes()).hexdigest(),'normalization_method':'minmax_0_1','evidence':'unit test only','inverse_transform_parameters':{'top_temperature':{'source_column':'U1','min':20,'max':120,'unit':'degC'}}}
        restored,audit=restore_normalized_fields(path,meta,{'top_temperature':'degC'})
        self.assertEqual([20,120],restored.top_temperature.tolist())
        self.assertEqual(['top_temperature'],audit['restored_fields'])
        meta['inverse_transform_parameters']['top_temperature']['unit']='Pa'
        with self.assertRaises(ValueError):restore_normalized_fields(path,meta,{'top_temperature':'degC'})

    def test_debutanizer_full_chain_if_valid_data(self):
        r=self.receipts['debutanizer_column']
        if r['status']=='unavailable':
            self.skipTest('缺合格物理量源文件：完整数值验收未通过，禁止生成替代数据')
        for row in r['executions']:
            self.assertIn(row['status'],{'success','read'})
        self.assertTrue(r['metrics']['arx_structure_order_selector']['candidate_count'])

    def test_dryer_real_or_best_available_dataset(self):
        r=self.receipts['industrial_dryer']
        self.assertIn('合成验收数据',r['dataset_ref'])
        frame=pd.read_csv(r['dataset_ref'])
        self.assertEqual(867,len(frame))
        self.assertEqual(sha256(Path(r['dataset_ref']).read_bytes()).hexdigest(),r['dataset_sha256'])
        self.assertEqual('partial',r['status'])

    def test_dryer_no_test_leakage(self):
        r=self.receipts['industrial_dryer']
        split=next(a for a in r['artifacts'] if a['artifact_type']=='FROZEN_SPLIT')
        parts=json.loads(Path(split['path']).read_text())['partitions']
        self.assertLess(parts['train']['end'],parts['validation']['start'])
        self.assertLess(parts['validation']['end'],parts['test']['start'])
        snapshot={'run_id':'test-leak-check','artifact_registry':r['artifacts'],'results':{}}
        # If ARX tries to read the held-out test, this invalid artifact will fail.
        broken=Path(self.temp.name)/'test_must_not_be_read.csv';broken.write_text('not CSV data')
        snapshot['artifact_registry']=[{**a,'path':str(broken)} if a['artifact_type']=='CLEANED_TEST' else a for a in r['artifacts']]
        manifest=get_registry('md').get('arx_structure_order_selector')
        result=MarkdownExecutor(manifest).execute(manifest.id,[],{}, {'scene_context':r['scene_context']},{'snapshot':snapshot},{'state':{},'execution_id':'no-leak','output_dir':Path(self.temp.name)/'no-leak'})
        self.assertEqual('success',result['status'])
        self.assertEqual(r['metrics']['arx_structure_order_selector'],result['metrics'])
        self.assertFalse(result['evidence'][0]['test_accessed'])

    def test_dryer_persistence_comparison(self):
        r=self.receipts['industrial_dryer'];artifact=next(a for a in r['artifacts'] if a['artifact_type']=='MODEL_ARTIFACT')
        model=json.loads(Path(artifact['path']).read_text());d=model['diagnostics']['test'];rmse=model['metrics']['test']['rmse'];baseline=d['persistence']['rmse']
        self.assertAlmostEqual((baseline-rmse)/baseline*100,d['rmse_improvement_over_persistence_pct'])
        self.assertLess(d['rmse_improvement_over_persistence_pct'],0)
        self.assertIn('multi_step',d)
        self.assertIn('metrics',d['multi_step'])
        self.assertEqual('partial',r['metrics']['model_diagnostics_evaluator']['status'])

    def test_three_scene_final_regression(self):
        r=self.receipts['blast_furnace']
        self.assertEqual('partial',r['status'])
        self.assertTrue(any(row['snr_db'] is None for row in r['metrics']['signal_noise_ratio_estimator']['per_variable_snr']))
        self.assertIn('test',r['metrics']['system_identification_trainer'])
        for r in self.receipts.values():
            self.assertEqual('md_registry',r['skill_plan']['analysis']['routing_source'])
