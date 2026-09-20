"""Generic correctness and isolation checks required by synthetic presets."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from core.services.optimization_candidates import bounded_candidate
from core.test_validation import frame, vm

class CandidateBoundsTests(SimpleTestCase):
    def test_projection_is_finite_distinct_and_exhausts_actual_space(self):
        bounds = {'top_k': {'min': 2, 'max': 3}, 'max_lag': {'min': 4, 'max': 5}}
        seen = set()
        for _ in range(4):
            c = bounded_candidate({'top_k': 99, 'max_lag': 600}, bounds, seen)
            self.assertEqual(c['proposed_parameters'], {'top_k': 99, 'max_lag': 600})
            pair = c['top_k'], c['max_lag']
            self.assertNotIn(pair, seen)
            self.assertIn(pair, {(2,4), (2,5), (3,4), (3,5)})
            seen.add(pair)
        self.assertIsNone(bounded_candidate({'top_k': 99, 'max_lag': 600}, bounds, seen))

class FreeSimulationInitializationTests(SimpleTestCase):
    def test_missing_initial_target_waits_for_observed_history_without_later_feedback(self):
        data = frame(120)
        data.loc[13:15, 'y'] = np.nan
        state = {'output':'y','seconds':10,'inputs':['u'],'evaluation_inputs':['u'],'delays':{'u':3},'order':2,'coef':[0,.6,.1,.9,0],'family':'ARX'}
        _, d, _, _ = vm.evaluation(data, state, 15, 'validation')
        self.assertFalse(d['free_simulation']['diverged'])
        self.assertEqual(d['free_simulation']['initialization_positions'], [18])
        # A later missing target does not cause a restart or inject new truth.
        data.loc[60:65,'y'] = np.nan
        _, changed, _, _ = vm.evaluation(data, state, 15, 'validation')
        self.assertEqual(changed['free_simulation']['initialization_positions'], [18])
        self.assertFalse(changed['free_simulation']['diverged'])
    def test_unstable_simulation_is_not_reinitialized_to_hide_divergence(self):
        data = frame(180)
        state = {'output':'y','seconds':10,'inputs':[],'evaluation_inputs':['u'],'delays':{},'order':1,'coef':[0,2],'family':'AR'}
        _, d, _, _ = vm.evaluation(data, state, 15, 'validation')
        self.assertTrue(d['free_simulation']['diverged'])
        self.assertEqual(d['free_simulation']['initialization_positions'], [15])

class SyntheticAssetTests(TestCase):
    def test_reference_is_separate_owner_scoped_and_hash_bound(self):
        data = b'dt,Fb,Fo,Th,R,Si\n2026-01-01,3500,19000,1120,3.9,.5\n'
        manifest = {key: None for key in ['preset_id','preset_version','scenario_id','generator_version','explicit_seed','effective_generation_parameters','rows','sampling_interval','units','process_assumptions']}
        manifest.update(source_type='SYNTHETIC', file_hash=hashlib.sha256(data).hexdigest())
        with TemporaryDirectory() as tmp, override_settings(PROCESSPILOT_RUNTIME_ROOT=Path(tmp)):
            def upload(m):
                return self.client.post('/api/assets/', {'file':SimpleUploadedFile('SYNTHETIC_demo.csv',data), 'generation_manifest':json.dumps(m), 'evaluation_reference':json.dumps({'clean_target':[.5], 'private_reference_marker':'never_in_context'})})
            r = upload(manifest)
            self.assertEqual(r.status_code,201,r.content)
            asset = r.json()['data']; aid = asset['asset_id']
            self.assertEqual(asset['source_type'],'SYNTHETIC')
            self.assertNotIn('clean_target',r.content.decode())
            self.assertNotIn('private_reference_marker',self.client.get('/api/assets/').content.decode())
            ref = self.client.get(f'/api/assets/{aid}/?artifact=evaluation_reference')
            self.assertEqual(json.loads(b''.join(ref.streaming_content))['clean_target'],[.5])
            self.assertEqual(upload({**manifest,'file_hash':'incorrect'}).status_code,400)
            user = get_user_model().objects.create_user(username='different-owner')
            self.client.force_login(user)
            self.assertEqual(self.client.get(f'/api/assets/{aid}/?artifact=evaluation_reference').status_code,404)
