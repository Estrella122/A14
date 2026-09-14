"""Debutanizer contract guards; blocked data is never a numerical PASS."""
import csv
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from core.services.dataset_evidence import restore_normalized_fields
from core.services.scene_skill_pipeline import run_scene_skill_pipeline
from integrations.standardization.standard_agent.engine import StandardizationAgent

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'integrations/standardization/standards/scenarios/debutanizer_column'


@override_settings(SKILL_MANIFEST_MODE='md')
class DebutanizerContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        logs = patch('core.skills.runtime.RUNS_DIR', Path(cls.tmp.name)/'runs')
        logs.start(); cls.addClassCleanup(logs.stop)
        cls.source = ROOT/'integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv'
        with patch('core.services.pipeline.run_pipeline', side_effect=AssertionError('legacy pipeline forbidden')) as legacy:
            cls.receipt = run_scene_skill_pipeline(cls.source, output_root=Path(cls.tmp.name)/'inputs')
            cls.legacy_calls = legacy.call_count

    def test_debutanizer_contract_resolution(self):
        config = json.loads((BASE/'template.json').read_text())
        with (BASE/'fields.csv').open() as stream:
            fields = {f['standard_name']: f for f in csv.DictReader(stream)}
        roles = config['field_roles']
        self.assertEqual(7, len(roles['inputs']))
        for name in [roles['timestamp'], roles['target'], *roles['inputs']]:
            self.assertEqual('true', fields[name]['required'])
        self.assertEqual('false', fields['sample_index']['required'])
        self.assertEqual('degC', fields['bottom_temperature_b']['unit'])
        self.assertEqual('50', fields['bottom_temperature_b']['lower_bound'])
        self.assertEqual('unavailable', self.receipt['status'])
        self.assertEqual({'bottom_temperature_a','bottom_temperature_b','top_temperature','tray6_temperature','top_pressure','next_process_flow','bottom_butane_content','reflux_flow'}, set(self.receipt['standardization']['mapping']['missing_required']))

    def test_debutanizer_alias_mapping(self):
        fields = ['timestamp','TOP_TEMPERATURE','top_pressure','reflux_flow','next_process_flow','tray_6_temperature','bottom_temp_a','bottom_temp_b','bottom_butane_content']
        mapping = StandardizationAgent().map_columns(fields, 'debutanizer_column')
        self.assertEqual(1.0, mapping['required_coverage'])
        self.assertTrue(all(m['status']=='matched' for m in mapping['mappings']))
        # Different measurement locations are not interchangeable aliases.
        bad = StandardizationAgent().map_columns(['normalized_1','Reboiler o/l Temp','Feed Flow to DB'], 'debutanizer_column')
        for m in bad['mappings']:
            self.assertFalse(m['status']=='matched' and m.get('standard') in {'bottom_temperature_b','next_process_flow'})

    def test_debutanizer_inverse_transform_guard(self):
        before = sha256(self.source.read_bytes()).hexdigest()
        metadata = json.loads((ROOT/'datasets/public/debutanizer/dataset_metadata.json').read_text())
        for invalid in [None, {}, metadata, {'source_hash':before, 'source_file':self.source.name, 'evidence':'missing scale', 'normalization_method':'minmax_0_1'}]:
            with self.assertRaises(ValueError):
                restore_normalized_fields(self.source, invalid, {'top_temperature':'degC'})
        self.assertEqual(before, sha256(self.source.read_bytes()).hexdigest())

    def test_debutanizer_scene_context(self):
        ctx = self.receipt['scene_context']
        self.assertEqual('debutanizer_column', ctx['scenario_id'])
        self.assertEqual('timestamp', ctx['timestamp_column'])
        self.assertEqual('bottom_butane_content', ctx['target_column'])
        self.assertEqual(7, len(ctx['input_columns']))
        self.assertEqual(60, ctx['sampling_interval'])  # template default, not proof of source cadence
        self.assertEqual('preserve_nan', ctx['constraints']['missing_target_policy'])
        self.assertEqual(75, ctx['default_parameters']['max_lag'])
        self.assertEqual('ScenarioRepository', ctx['metadata']['config_source'])

    def test_debutanizer_md_pipeline_12_skills(self):
        r = self.receipt
        self.assertEqual(12, len(set(r['skill_ids'])))
        if r['status']=='unavailable':
            self.assertTrue(all(not row['audit']['executor_invoked'] for row in r['executions']))
            self.skipTest('真实数值验收未完成：缺物理数据/可信逆缩放元数据；12规划节点不是12次执行')
        for row in r['executions']:
            self.assertIn(row['status'], {'success','read','partial'})
            self.assertTrue(row['audit']['executor_invoked'])
        self.assertGreater(r['metrics']['arx_structure_order_selector']['candidate_count'],0)

    def test_debutanizer_no_legacy_fallback(self):
        self.assertEqual(0, self.legacy_calls)
        self.assertEqual('md_registry', self.receipt['skill_plan']['analysis']['routing_source'])
        self.assertTrue(all(self.receipt['manifest_paths']))
        self.assertTrue(all(self.receipt['executor_modules']))
        # Even when the data gate fails, no legacy or mock numerical output appears.
        if self.receipt['status']=='unavailable':
            self.assertTrue(all(not m for m in self.receipt['metrics'].values()))

    def test_debutanizer_result_contract(self):
        r = self.receipt
        for key in ['run_id','dataset_ref','dataset_sha256','scene_context','skill_ids','manifest_paths','executor_modules','parameters','status','metrics','warnings','artifacts','elapsed_ms']:
            self.assertIn(key,r)
        self.assertEqual(sha256(self.source.read_bytes()).hexdigest(),r['dataset_sha256'])
        for row in r['executions']:
            for key,kind in {'status':str,'metrics':dict,'evidence':list,'warnings':list,'artifacts':list}.items():
                self.assertIsInstance(row[key],kind)
