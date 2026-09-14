from unittest.mock import patch
from django.test import SimpleTestCase
from integrations.standardization.standard_agent.engine import StandardizationAgent
from integrations.standardization.standard_agent.physical_semantics import final_field_acceptance_gate

class FinalFieldAcceptanceTests(SimpleTestCase):
    def setUp(self):
        self.agent = StandardizationAgent()
        self.template = self.agent.repository.get('debutanizer_column')
    def row(self, name):
        return self.agent.map_columns([name], 'debutanizer_column')['mappings'][0]
    def nominated(self, source, target, method='alias', unit='consistent'):
        item = {'raw':source,'base_name':source,'standard':target,'method':method,'confidence':1.,'unit_status':unit,'expected_unit':self.template.by_name[target].unit}
        return final_field_acceptance_gate(item,self.template,.82)
    def test_explicit_alias_runs_final_physical_gate(self):
        r=self.row('bottom_temp_a');self.assertEqual('AUTO_ACCEPT',r['decision']);self.assertEqual('final_field_acceptance_gate',r['final_acceptance_audit']['gate'])
    def test_normalized_alias_runs_final_physical_gate(self):
        r=self.row('tray_6_temperature');self.assertEqual('AUTO_ACCEPT',r['decision']);self.assertTrue(r['final_acceptance_audit']['checks']['physical_semantics'])
    def test_bad_alias_can_be_rejected(self):
        aliases=self.agent._aliases(self.template).copy();aliases['reboiler_outlet_temperature']='bottom_temperature_b'
        with patch.object(self.agent,'_aliases',return_value=aliases):
            self.assertNotEqual('AUTO_ACCEPT',self.row('reboiler outlet temperature [degC]')['decision'])
    def test_normalization_mapping_requires_identity_metadata(self):
        for name in ['u1','U2','y','normalized_1','scaled_2']:
            self.assertNotEqual('AUTO_ACCEPT',self.row(name)['decision'])
        self.assertNotEqual('AUTO_ACCEPT',self.nominated('normalized_1','top_temperature','normalization_mapping')['decision'])
    def test_duplicate_resolution_cannot_restore_physical_conflict(self):
        rows=[]
        for method in ['manual','alias']:
            r={'standard':'bottom_temperature_b','method':method,'confidence':1.}
            r.update(self.nominated('reactor outlet temperature','bottom_temperature_b',method));rows.append(r)
        self.agent._resolve_duplicates(rows);self.assertTrue(all(r['status']!='matched' for r in rows))
    def test_high_confidence_alias_conflict_requires_review(self):
        self.assertEqual('REVIEW_REQUIRED',self.nominated('bottom temperature b','bottom_temperature_a')['decision'])
    def test_same_quantity_wrong_location_rejected(self):
        for name in ['tray 6 temperature','reboiler outlet temperature']:
            self.assertNotEqual('AUTO_ACCEPT',self.nominated(name,'top_temperature')['decision'])
    def test_same_flow_wrong_direction_rejected(self):
        self.assertNotEqual('AUTO_ACCEPT',self.nominated('feed flow','next_process_flow')['decision'])
    def test_unknown_unit_critical_field_not_autoaccepted(self):
        r=self.nominated('column top temperature reading','top_temperature','trained_model_auto','not_declared')
        self.assertEqual('REVIEW_REQUIRED',r['decision']);self.assertTrue(r['final_acceptance_audit']['required_field_criticality'])
    def test_all_acceptance_paths_emit_audit_evidence(self):
        for method in ['alias','normalized_alias','semantic','trained_model_auto','point_dictionary','normalization_mapping','vendor_core_alias','manual']:
            r=self.nominated('column top temperature','top_temperature',method)
            self.assertIn('final_acceptance_audit',r)
            self.assertEqual(method,r['final_acceptance_audit']['method'])
    def test_positive_units_and_source_metadata(self):
        self.assertEqual('AUTO_ACCEPT',self.row('top temp [degC]')['decision'])
        item={'raw':'u1','base_name':'u1','standard':'top_temperature','method':'alias','confidence':1.,'unit_status':'not_declared','expected_unit':'degC'}
        metadata={'standard_field':'top_temperature','scenario_id':'debutanizer_column','evidence_source':'test documented channel identity','unit':'degC','normalized':False}
        self.assertEqual('AUTO_ACCEPT',final_field_acceptance_gate(item,self.template,.82,metadata)['decision'])
        metadata['scenario_id']='industrial_dryer'
        self.assertNotEqual('AUTO_ACCEPT',final_field_acceptance_gate(item,self.template,.82,metadata)['decision'])

    def test_inverse_transform_conflicting_measurement_rejected(self):
        import tempfile, hashlib
        from pathlib import Path
        from core.services.dataset_evidence import restore_normalized_fields
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'wrong_location.csv';path.write_text('reboiler outlet temperature\n0\n1\n')
            metadata={'scenario_id':'debutanizer_column','source_file':path.name,'source_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'normalization_method':'minmax_0_1','evidence':'test-only incorrect binding','inverse_transform_parameters':{'bottom_temperature_b':{'source_column':'reboiler outlet temperature','min':50,'max':180,'unit':'degC'}}}
            with self.assertRaises(ValueError):restore_normalized_fields(path,metadata,{'bottom_temperature_b':'degC'})

    def test_source_metadata_cannot_contradict_physical_contract(self):
        item={'raw':'bottom_temp_a','base_name':'bottom_temp_a','standard':'bottom_temperature_a','method':'alias','confidence':1.,'unit_status':'not_declared','expected_unit':'degC'}
        for meta in [{'unit':'Pa'},{'measurement_location':'column_top'},{'measurement_channel':'b'}]:
            self.assertNotEqual('AUTO_ACCEPT',final_field_acceptance_gate(item,self.template,.82,meta)['decision'])
