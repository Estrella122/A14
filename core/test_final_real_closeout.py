"""Final acceptance assertions; blocked real scenes remain explicit, never skipped."""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools.validate_local_real_sources import portable_path
from core.services.scene_skill_pipeline import run_scene_skill_pipeline
ROOT=Path(settings.BASE_DIR)
def read(p):return json.loads((ROOT/p).read_text())
@override_settings(SKILL_MANIFEST_MODE="md")
class FinalRealCloseoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.result=read('three_scene_final_real_runtime.json');cls.bf=cls.result['scenes'][0]['receipt']
        cls.temp=TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        logs=patch('core.skills.runtime.RUNS_DIR',Path(cls.temp.name)/'runs')
        logs.start();cls.addClassCleanup(logs.stop)
        cls.fresh=run_scene_skill_pipeline(ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv',output_root=Path(cls.temp.name)/'inputs')
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
    def test_recorded_source_manifest_integrity(self):
        m=read('datasets/real_validation/tobacco_acquisition_manifest.json')
        self.assertTrue(m['source_archive_md5_verified']);self.assertEqual({},m['renames']);self.assertIsNone(m['inverse_transform'])
        self.assertEqual(m['output_hash'],read('datasets/real_validation/prechecks/tobacco_zenodo.json')['source_hash'])
        self.assertRegex(m['output_hash'],r'^[0-9a-f]{64}$')
    def test_distributed_real_data_hash(self):
        path=ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest,self.bf['dataset_sha256'])
        self.assertEqual(digest,self.fresh['dataset_sha256'])
        self.assertTrue(self.bf['comparison']['dataset_sha256'])
    def test_no_cross_dataset_splice(self):
        self.assertEqual(str(ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv'),str(portable_path(self.bf['dataset_ref'],self.bf['dataset_ref'])))
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
            manifest=portable_path(e['audit']['manifest_path'],self.bf['dataset_ref'])
            self.assertEqual('SKILL.md',manifest.name)
            declaration=yaml.safe_load(manifest.read_text().split('---',2)[1])
            self.assertIn(e['audit']['execution_mode'],['execute','read'])
            self.assertEqual(declaration['execution_mode'],e['audit']['execution_mode'])
    def test_no_legacy_fallback(self):
        for e in self.bf['executions']:
            self.assertTrue(e['audit']['executor_module'].startswith('core.skills.'));self.assertTrue(e['audit']['executor_module'].endswith('.executor'))
        self.assertTrue(self.bf['comparison']['executor_modules'])
    def test_12_executor_receipts(self):
        self.assertEqual(12,len(self.fresh['executions']));self.assertEqual(12,len(set(self.fresh['skill_ids'])))
        self.assertEqual(self.bf['skill_ids'],self.fresh['skill_ids'])
        for e in self.fresh['executions']:
            self.assertTrue(e['audit']['executor_invoked']);self.assertNotIn(e['status'],['failed','blocked','unavailable'])
            for key in ['metrics','evidence','warnings','artifacts']:self.assertIn(key,e)
    def test_test_leakage_guard(self):
        self.assertTrue(self.bf['comparison']['metrics'])
        parts=self.fresh['metrics']['time_axis_alignment_resampler']['partitions'];self.assertEqual([432,144,144],[parts[k]['rows'] for k in ['train','validation','test']])
        model=read(Path(next(a['path'] for a in self.fresh['artifacts'] if a['artifact_type']=='MODEL_ARTIFACT')))
        self.assertGreater(model['diagnostics']['test']['guard_samples'],0);self.assertTrue(model['diagnostics']['test']['evaluation_target_hash'])
        self.assertTrue(self.fresh['metrics']['model_diagnostics_evaluator']['gates']['single_final_test'])

    def test_historical_paths_rebase_to_current_checkout(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            old='/different/checkout/frontend/public/datasets/blast_furnace_real_720h.csv'
            self.assertEqual(root.resolve()/'core/skills/runtime.py',portable_path('/different/checkout/core/skills/runtime.py',old,root))

    def test_historical_paths_cannot_escape_checkout(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                portable_path('../outside','/different/checkout/frontend/public/datasets/blast_furnace_real_720h.csv',Path(directory))
