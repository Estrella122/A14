from django.test import SimpleTestCase
from tools.precheck_real_dataset import precheck
from pathlib import Path
import tempfile
class RealDatasetPrecheckTests(SimpleTestCase):
    def test_no_metadata_cannot_authorize_real_data(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.csv';p.write_text('timestamp,top_temperature\n2024-01-01,80\n')
            r=precheck(p,'debutanizer_column');self.assertNotEqual('ELIGIBLE',r['final_eligibility']);self.assertEqual(9,r['required_count']);self.assertIn('physical_gate_results',r)
    def test_headerless_layout_cannot_be_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.txt';p.write_text('1 2\n3 4\n')
            r=precheck(p,'industrial_dryer',{'documented_columns':['timestamp','product_moisture']});self.assertEqual('UNUSABLE',r['final_eligibility'])
    def test_anonymous_scaled_data_stays_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.csv';p.write_text('u1,u2,y\n0.1,0.2,0.3\n')
            r=precheck(p,'debutanizer_column',{'source_type':'BENCHMARK_REAL','license':'test fixture only','analysis_allowed':True,'normalization_status':'normalized'})
            self.assertEqual('NORMALIZATION_BLOCKED',r['final_eligibility']);self.assertEqual(0,r['matched_required'])
