"""Physical identity gate: model scores cannot establish measurement identity."""
from unittest.mock import Mock, patch
import pandas as pd
from django.test import SimpleTestCase
from integrations.standardization.standard_agent.engine import StandardizationAgent
from integrations.standardization.standard_agent.physical_semantics import evaluate


class FieldMatchingSafetyTests(SimpleTestCase):
    def setUp(self):
        self.agent=StandardizationAgent()
        self.contract=self.agent.repository.get('debutanizer_column').config['physical_semantics']

    def mapping(self,name):
        return self.agent.map_columns([name],'debutanizer_column')['mappings'][0]

    def gate(self,source,target,unit='consistent'):
        return evaluate(source,target,'trained_model_auto',0.99,unit,self.contract,0.82)

    def test_explicit_alias_still_passes(self):
        row=self.mapping('bottom_temp_a')
        self.assertEqual('AUTO_ACCEPT',row['decision'])
        self.assertEqual('alias',row['mapping_method'])
        self.assertEqual('bottom_temperature_a',row['standard'])

    def test_reboiler_outlet_not_bottom_temperature(self):
        row=self.mapping('Reboiler o/l Temp')
        self.assertEqual('bottom_temperature_b',row['candidate_field'])
        self.assertEqual('REVIEW_REQUIRED',row['decision'])
        self.assertFalse(row['physical_gates']['location_compatible'])

    def test_feed_flow_not_downstream_flow(self):
        row=self.mapping('Feed Flow to DB')
        self.assertEqual('next_process_flow',row['candidate_field'])
        self.assertEqual('REVIEW_REQUIRED',row['decision'])
        self.assertFalse(row['physical_gates']['direction_compatible'])

    def test_same_quantity_different_location_requires_review(self):
        for name,target in [('tray 6 temperature','top_temperature'),('feed temperature','bottom_temperature_a'),('reboiler outlet temperature','bottom_temperature_b')]:
            r=self.gate(name,target)
            self.assertTrue(r['physical_gates']['quantity_type_compatible'])
            self.assertFalse(r['physical_gate_pass'])
            self.assertFalse(r['physical_gates']['location_compatible'])

    def test_same_flow_different_direction_requires_review(self):
        for name in ['inlet flow','reflux flow','recycle flow']:
            self.assertFalse(self.gate(name,'next_process_flow')['physical_gates']['direction_compatible'])

    def test_high_confidence_cannot_override_physical_conflict(self):
        self.assertFalse(self.gate('reboiler outlet temperature','bottom_temperature_b')['physical_gate_pass'])
        frame=pd.DataFrame({'Reboiler o/l Temp [degC]':[100.,110.,120.]})
        row=self.agent.map_columns(list(frame),'debutanizer_column',frame)['mappings'][0]
        self.assertEqual(1.0,row['value_profile']['plausibility'])
        self.assertNotEqual('AUTO_ACCEPT',row['decision'])

    def test_unknown_location_is_not_auto_accepted(self):
        self.assertFalse(self.gate('temperature','top_temperature')['physical_gates']['location_compatible'])
        self.assertFalse(self.gate('bottom temperature','bottom_temperature_b')['physical_gate_pass'])
        self.assertFalse(self.gate('flow','next_process_flow')['physical_gates']['direction_compatible'])

    def test_mapping_audit_contains_physical_evidence(self):
        for name in ['Feed Flow to DB','bottom_temp_a','normalized_1']:
            r=self.mapping(name)
            for key in ['source_column','candidate_field','mapping_method','confidence','semantic_evidence','unit_evidence','quantity_type_evidence','role_evidence','location_evidence','direction_evidence','decision','decision_reason']:
                self.assertIn(key,r)

    def test_model_candidate_can_pass_when_semantics_fully_compatible(self):
        # Controlled candidate tests acceptance logic, not the model's accuracy.
        self.agent.semantic_model=Mock(metadata={'accept_threshold':0.54})
        self.agent.semantic_model.predict.return_value=[{'standard_name':'top_temperature','score':0.99},{'standard_name':'top_pressure','score':0.01}]
        with patch('integrations.standardization.standard_agent.engine.fuzz.WRatio',return_value=0), patch('integrations.standardization.standard_agent.engine._cosine',return_value=0):
            r=self.mapping('column top temperature reading [degC]')
        self.assertEqual('trained_model_auto',r['method'])
        self.assertEqual('AUTO_ACCEPT',r['decision'])
        self.assertTrue(all(r['physical_gates'].values()))
        self.assertFalse(self.gate('top temp','top_temperature','not_declared')['physical_gate_pass'])
        self.assertFalse(self.gate('top temp','top_temperature','conflict')['physical_gate_pass'])

    def test_debutanizer_contract_still_blocks_incomplete_data(self):
        m=self.agent.map_columns(['Reboiler o/l Temp','Feed Flow to DB'],'debutanizer_column')
        self.assertIn('bottom_temperature_b',m['missing_required'])
        self.assertIn('next_process_flow',m['missing_required'])
        self.assertEqual(0,m['required_coverage'])

    def test_explicit_alias_model_cannot_override(self):
        self.agent.semantic_model=Mock()
        self.assertEqual('AUTO_ACCEPT',self.mapping('bottom_temp_a')['decision'])
        self.agent.semantic_model.predict.assert_not_called()

    def test_role_equipment_and_ambiguous_quantity_conflicts(self):
        self.assertFalse(self.gate('column top temperature setpoint','top_temperature')['physical_gates']['physical_role_compatible'])
        self.assertFalse(self.gate('reactor top temperature','top_temperature')['physical_gate_pass'])
        self.assertFalse(self.gate('column top temperature flow','top_temperature')['physical_gates']['quantity_type_compatible'])
        self.assertFalse(self.gate('bottom temperature a b','bottom_temperature_b')['physical_gate_pass'])

    def test_alias_unit_conflict_and_measurement_digit_are_preserved(self):
        self.assertNotEqual('AUTO_ACCEPT',self.mapping('bottom_temp_a [Pa]')['decision'])
        self.assertEqual('AUTO_ACCEPT',self.mapping('tray_6_temperature')['decision'])
        self.assertNotEqual('AUTO_ACCEPT',self.mapping('tray_7_temperature [degC]')['decision'])

    def test_duplicate_resolution_cannot_reenable_unsafe_candidate(self):
        rows=[{'standard':'bottom_temperature_b','method':'trained_model_auto','confidence':0.99,'physical_gate_pass':False},
              {'standard':'bottom_temperature_b','method':'trained_model_auto','confidence':0.98,'physical_gate_pass':False}]
        self.agent._resolve_duplicates(rows)
        self.assertTrue(all(row['status']!='matched' for row in rows))
        safe={'standard':'bottom_temperature_b','method':'semantic','confidence':0.9,'physical_gate_pass':True}
        self.agent._resolve_duplicates(rows+[safe])
        self.assertEqual('matched',safe['status'])
        self.assertTrue(all(row['status']!='matched' for row in rows))
