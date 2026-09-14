"""Evidence corpus regression: no learned predictions may author Ground Truth."""
import hashlib,json
from pathlib import Path
import pandas as pd
from django.test import SimpleTestCase
from integrations.standardization.standard_agent.engine import normalize_name
from integrations.standardization.standard_agent.physical_semantics import evaluate
from core.services import pipeline
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'datasets/field_ground_truth'


class GroundTruthEvaluationTests(SimpleTestCase):
    def setUp(self):
        self.gt=json.loads((ROOT/'real_field_ground_truth.json').read_text())
        self.coverage=json.loads((P/'coverage.json').read_text())

    def test_ground_truth_has_source_evidence_and_never_copies_sensors(self):
        for d in self.gt['datasets']:
            rows=[r for r in self.gt['fields'] if r['dataset_id']==d['dataset_id'] and r['source_column'] is not None]
            self.assertEqual(d['source_columns'],[r['source_column'] for r in rows])
            for r in rows:self.assertTrue(r['evidence_source'])
        rows=[r for r in self.gt['fields'] if r['source_column'] in {'Reboiler o/l Temp','Feed Flow to DB'}]
        self.assertEqual(2,len(rows));self.assertTrue(all(r['ground_truth_decision']=='NO_EQUIVALENT' for r in rows))

    def test_contract_coverage_separates_match_review_missing(self):
        for c in self.coverage:
            self.assertEqual(c['required_field_count'],c['matched_required_count']+c['review_required_count']+c['missing_required_count'])
            self.assertAlmostEqual(c['coverage'],c['matched_required_count']/c['required_field_count'])
        lost=next(c for c in self.coverage if 'LostRunes' in c['name'])
        self.assertEqual(2,lost['matched_required_count']);self.assertEqual('MIXED_LIMITATION',lost['classification'])

    def test_retrieval_metrics_include_denominators_and_no_training_claim(self):
        m=json.loads((P/'field_metrics.json').read_text())
        self.assertFalse(m['training_performed']);self.assertEqual(m['before'],m['after'])
        for scene,v in m['before'].items():
            self.assertIn('match_support',v);self.assertIn('review_support',v)
            if v['match_support']==0:self.assertIsNone(v['top3_recall'])

    def test_semantic_classifier_retains_physical_gate(self):
        contract=self.gt['contracts']['debutanizer_column']['template']['physical_semantics']
        self.assertFalse(evaluate('top temperature','top_temperature','trained_model_auto',.99,'not_declared',contract,.82)['physical_gate_pass'])
        self.assertTrue(evaluate('top temperature','top_temperature','trained_model_auto',.99,'consistent',contract,.82)['physical_gate_pass'])

    def test_hard_negatives_never_auto_accept(self):
        probes=json.loads((P/'field_metrics.json').read_text())['hard_negative_probes']
        self.assertEqual(4,len(probes));self.assertFalse(any(x['auto_accept'] for x in probes))

    def test_ood_not_confirmed_known(self):
        rows=json.loads((P/'scene_evaluation.json').read_text())
        unknown=[r for r in rows if r['expected'].startswith('unknown')]
        self.assertEqual(3,len(unknown))
        self.assertTrue(all(r['result']['status']!='confirmed' for r in unknown))
        # An uncertain medical schema is a reported rejection-coverage limitation,
        # not counted as a successful UNKNOWN rejection.
        self.assertEqual(2,sum(r['result']['status']=='unknown' for r in unknown))

    def test_cleaning_strategy_causal_and_target_safe(self):
        with pipeline._module_path(pipeline.INTEGRATIONS_DIR/'data_cleaning/src'):
            from data_cleaning_agent import DataCleaningSelectionAgent
        def clean(frame):
            return DataCleaningSelectionAgent({'u':{'role':'input'},'y':{'role':'output'}},primary_output='y').process_missing_values(frame)
        x=pd.DataFrame({'u':[1.]+[float('nan')]*9+[8.],'y':[2.]+[float('nan')]*9+[9.]})
        y=clean(x);z=x.copy();z.iloc[-1]=[99.,99.]
        pd.testing.assert_frame_equal(y.iloc[:-1],clean(z).iloc[:-1])
        self.assertTrue(y.y.isna().equals(x.y.isna()));self.assertTrue(y.u.iloc[7:10].isna().all())

    def test_alias_split_and_source_dataset_no_leakage(self):
        rows=[json.loads(x) for x in (P/'field_examples.jsonl').read_text().splitlines()]
        for key in ['scenario_split_group','source_field']:
            groups={}
            for row in rows:
                value=normalize_name(row[key]).replace('_','') if key=='source_field' else row[key]
                groups.setdefault(value,set()).add(row['split'])
            self.assertTrue(all(len(s)==1 for s in groups.values()))
        manifest=json.loads((P/'dataset_manifest.json').read_text())
        self.assertEqual(manifest['dataset_sha256'],hashlib.sha256((P/'field_examples.jsonl').read_bytes()).hexdigest())

    def test_three_scene_real_contract_training_cannot_fill_missing(self):
        self.assertFalse(any(c['learnable_verified_fields'] for c in self.coverage))
        self.assertEqual('CAN_RUN_NOW',self.coverage[0]['classification'])
        self.assertEqual([],json.loads((ROOT/'three_scene_real_runtime.json').read_text())['transformation_policy']['derived_columns'])

    def test_three_scene_pipeline_receipts_are_truthful(self):
        result=json.loads((ROOT/'three_scene_post_training_runtime.json').read_text())
        bf=result['scenes'][0]['receipt'];self.assertEqual(12,len(bf['executions']))
        self.assertTrue(all(r['audit']['executor_invoked'] for r in bf['executions']))
        self.assertTrue(all(bf['comparison'].values()))
        for scene in result['scenes'][1:]:self.assertIsNone(scene['run_id']);self.assertEqual('UNAVAILABLE',scene['pipeline'])
