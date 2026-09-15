"""Fixed source-evidence acceptance. Rejected-data guards are not Pipeline PASS."""
import hashlib
import json
from pathlib import Path
from django.test import SimpleTestCase, override_settings
from core.skills.registry import get_registry

ROOT=Path(__file__).resolve().parents[1]


class RealDatasetAcceptanceTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record=json.loads((ROOT/'three_scene_real_runtime.json').read_text())
        cls.scenes={s['scene']:s for s in cls.record['scenes']}
        cls.bf=cls.scenes['blast_furnace']['receipt']

    def test_recorded_debutanizer_contract(self):
        # Recorded evidence only. Raw-source revalidation is an explicit local command.
        result=json.loads((ROOT/'datasets/real_validation/prechecks/dataset_23.json').read_text())
        self.assertEqual((2394,8),(result['rows'],len(result['columns'])))
        self.assertEqual(0,result['matched_required'])
        self.assertIn('timestamp',result['missing_fields'])
        self.assertNotEqual('ELIGIBLE',result['final_eligibility'])

    def test_real_debutanizer_pipeline(self):
        # No qualified source => intentionally do not call an algorithm.
        scene=self.scenes['debutanizer_column']
        self.assertEqual('UNAVAILABLE',scene['pipeline'])
        self.assertIsNone(scene['run_id'])
        self.assertFalse(scene['executor_invoked'])
        self.assertFalse(any(c['usable'] for c in self.record['candidates'] if c['scene']==scene['scene']))

    def test_recorded_dryer_contract(self):
        result=json.loads((ROOT/'datasets/real_validation/prechecks/dataset_10.json').read_text())
        self.assertEqual((867,7),(result['rows'],len(result['columns'])))
        self.assertIn('raw_material_moisture',result['columns'])
        self.assertNotIn('product_moisture',result['columns'])
        self.assertEqual(0,result['matched_required'])
        self.assertNotEqual('ELIGIBLE',result['final_eligibility'])
        c=next(c for c in self.record['candidates'] if 'DAISY' in c['dataset_name'])
        self.assertFalse(c['usable'])
        self.assertEqual('FAIL',c['preflight']['physical_safety'])

    def test_real_dryer_pipeline(self):
        s=self.scenes['industrial_dryer']
        self.assertIsNone(s['run_id'])
        self.assertFalse(s['executor_invoked'])
        self.assertNotEqual('PASS',s['pipeline'])
        self.assertEqual([],self.record['transformation_policy']['processed_files'])

    def test_real_dataset_source_manifest(self):
        required={'scene','dataset_name','source_url','source_type','publisher','paper_or_project','license','download_method','original_filename','sha256','rows','columns','time_coverage','sampling_interval','field_descriptions','units','target','inputs','normalization_status','inverse_metadata','usable','reject_reason'}
        for candidate in self.record['candidates']:
            self.assertTrue(required.issubset(candidate))
            self.assertEqual(12,len(candidate['preflight']))
            if candidate['usable']:
                self.assertTrue(all(x=='PASS' for x in candidate['preflight'].values()))
            else:self.assertTrue(candidate['reject_reason'])

    def test_real_dataset_no_fake_fields(self):
        policy=self.record['transformation_policy']
        self.assertEqual([],policy['derived_columns'])
        self.assertEqual({},policy['renames'])
        self.assertIsNone(policy['inverse_transform'])
        for scene,contract in self.record['contracts'].items():
            for name,digest in contract['hashes'].items():
                p=ROOT/'integrations/standardization/standards/scenarios'/scene/name
                self.assertEqual(digest,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_real_pipeline_no_legacy_fallback(self):
        self.assertEqual('md_registry',self.bf['skill_plan']['analysis']['routing_source'])
        self.assertTrue(all('core.skills.' in module for module in self.bf['executor_modules']))
        self.assertTrue(all(path.endswith('SKILL.md') for path in self.bf['manifest_paths']))

    @override_settings(SKILL_MANIFEST_MODE='md')
    def test_real_pipeline_md_mode(self):
        self.assertEqual('md',self.record['manifest_mode'])
        registry=get_registry('md')
        for sid,module in zip(self.bf['skill_ids'],self.bf['executor_modules']):
            self.assertEqual(registry.get(sid).executor['module'],module)

    def test_real_pipeline_executor_invoked(self):
        self.assertEqual(12,len(self.bf['executions']))
        self.assertTrue(all(row['audit']['executor_invoked'] for row in self.bf['executions']))
        self.assertFalse(any(row['status'] in {'blocked','unavailable','failed'} for row in self.bf['executions']))
        for row in self.bf['executions']:
            for key in ['metrics','warnings','evidence','artifacts']:self.assertIn(key,row)

    def test_recorded_source_hashes_and_distributed_fixture(self):
        # Cross-check independent checked-in manifests, not nonexistent private files.
        candidates=json.loads((ROOT/'datasets/real_validation/closeout/candidates.json').read_text())
        known={c['sha256'] for c in candidates if c.get('sha256')}
        for c in self.record['candidates']:
            if c.get('sha256'):
                self.assertRegex(c['sha256'],r'^[0-9a-f]{64}$')
                self.assertIn(c['sha256'],known)
        self.assertTrue(all(self.bf['comparison'].values()))
        path=ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv'
        self.assertEqual(self.bf['dataset_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
