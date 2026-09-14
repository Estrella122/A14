"""Final acceptance assertions; blocked real scenes remain explicit, never skipped."""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase
ROOT=Path(settings.BASE_DIR)
def read(p):return json.loads((ROOT/p).read_text())
class FinalRealCloseoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.result=read('three_scene_final_real_runtime.json');cls.bf=cls.result['scenes'][0]['receipt']
    def test_final_debutanizer_real_contract(self):
        r=read('datasets/real_validation/prechecks/dataset_04.json')
        self.assertEqual(9,r['required_count']);self.assertLess(r['matched_required'],9);self.assertNotEqual('ELIGIBLE',r['final_eligibility'])
        self.assertTrue(r['reasons'])
    def test_final_debutanizer_real_pipeline(self):
        r=self.result['scenes'][1];self.assertEqual('UNAVAILABLE',r['pipeline']);self.assertIsNone(r['run_id']);self.assertEqual([],r['executions'])
    def test_final_dryer_real_contract(self):
        for file in ['dataset_10','tobacco_zenodo']:
            r=read('datasets/real_validation/prechecks/'+file+'.json');self.assertEqual(7,r['required_count']);self.assertLess(r['matched_required'],7);self.assertNotEqual('ELIGIBLE',r['final_eligibility'])
    def test_final_dryer_real_pipeline(self):
        r=self.result['scenes'][2];self.assertEqual('UNAVAILABLE',r['pipeline']);self.assertIsNone(r['run_id']);self.assertEqual([],r['executions'])
    def test_source_manifest_integrity(self):
        m=read('datasets/real_validation/tobacco_acquisition_manifest.json')
        self.assertTrue(m['source_archive_md5_verified']);self.assertEqual({},m['renames']);self.assertIsNone(m['inverse_transform'])
        self.assertEqual(m['output_hash'],hashlib.sha256((ROOT/'runtime/data_validation/final_search/tobacco.xlsx').read_bytes()).hexdigest())
    def test_real_data_hash(self):
        for r in read('datasets/real_validation/closeout/candidates.json'):
            if r.get('hash_revalidated'):
                self.assertEqual(r['sha256'],hashlib.sha256(Path(r['local_path']).read_bytes()).hexdigest())
        self.assertTrue(self.bf['comparison']['dataset_sha256'])
    def test_no_cross_dataset_splice(self):
        self.assertEqual(str(ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv'),self.bf['dataset_ref'])
        for artifact in self.bf['artifacts']:
            self.assertEqual(self.bf['run_id'],artifact['run_id'])
            self.assertIn(artifact.get('source_execution_id'),[self.bf['run_id'],self.bf['skill_run_id']])
    def test_no_fake_required_fields(self):
        for scene,c in read('datasets/real_validation/closeout/contracts.json').items():
            for name,digest in c['hashes'].items():
                self.assertEqual(digest,hashlib.sha256((ROOT/'integrations/standardization/standards/scenarios'/scene/name).read_bytes()).hexdigest())
    def test_md_mode_only(self):
        self.assertEqual('md',self.result['manifest_mode'])
        import yaml
        for e in self.bf['executions']:
            manifest=Path(e['audit']['manifest_path'])
            self.assertEqual('SKILL.md',manifest.name)
            declaration=yaml.safe_load(manifest.read_text().split('---',2)[1])
            self.assertIn(e['audit']['execution_mode'],['execute','read'])
            self.assertEqual(declaration['execution_mode'],e['audit']['execution_mode'])
    def test_no_legacy_fallback(self):
        for e in self.bf['executions']:
            self.assertTrue(e['audit']['executor_module'].startswith('core.skills.'));self.assertTrue(e['audit']['executor_module'].endswith('.executor'))
        self.assertTrue(self.bf['comparison']['executor_modules'])
    def test_12_executor_receipts(self):
        self.assertEqual(12,len(self.bf['executions']));self.assertEqual(12,len(set(self.bf['skill_ids'])))
        for e in self.bf['executions']:
            self.assertTrue(e['audit']['executor_invoked']);self.assertNotIn(e['status'],['failed','blocked','unavailable'])
            for key in ['metrics','evidence','warnings','artifacts']:self.assertIn(key,e)
    def test_test_leakage_guard(self):
        self.assertTrue(self.bf['comparison']['metrics'])
        parts=self.bf['metrics']['time_axis_alignment_resampler']['partitions'];self.assertEqual([432,144,144],[parts[k]['rows'] for k in ['train','validation','test']])
        model=read(Path(next(a['path'] for a in self.bf['artifacts'] if a['artifact_type']=='MODEL_ARTIFACT')))
        self.assertGreater(model['diagnostics']['test']['guard_samples'],0);self.assertTrue(model['diagnostics']['test']['evaluation_target_hash'])
        self.assertTrue(self.bf['metrics']['model_diagnostics_evaluator']['gates']['single_final_test'])
