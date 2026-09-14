import json,sys,hashlib
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root));from tools.precheck_real_dataset import precheck
out=root/'datasets/real_validation/prechecks';out.mkdir(parents=True,exist_ok=True)
gt=json.load(open('real_field_ground_truth.json'))
for i in [0,1,3,4,10,11,23]:
 d=gt['datasets'][i];p=Path(d['source_path']);meta=d['source_metadata'].copy()
 meta.update(source_hash=hashlib.sha256(p.read_bytes()).hexdigest(),source_type='DERIVED_REAL' if i==0 else 'BENCHMARK_REAL' if i in [1,3,23] else 'PUBLIC_REAL_PROCESS' if i==10 else 'PUBLIC_EXPERIMENT' if i==11 else 'UNKNOWN',evidence_source=d['source_url'],sampling_evidence=meta.get('field_descriptions'),no_equivalent=sum(r['ground_truth_decision']=='NO_EQUIVALENT' for r in gt['fields'] if r['dataset_id']==d['dataset_id']),analysis_allowed=i in [0,11])
 if i==0:meta.update(license='CC BY 4.0',normalization_status='physical',units={k:v['unit'] for k,v in gt['contracts']['blast_furnace']['fields'].items()},sampling_interval=3600,sampling_evidence='datasets/real_candidates/blast_furnace_mendeley/derived_manifest.json')
 elif i in [1,3,23]:meta['normalization_status']='normalized'
 elif i==4:meta.update(encoding='cp1252',skiprows=[1,2],normalization_status='physical')
 if i in [1,10]:meta.update(documented_columns=d['source_columns'],layout_evidence='raw header' if i==1 else 'runtime/data_validation/public_candidates/daisy_dryer_description.txt',separator=r'\s+',skiprows=5 if i==1 else 0)
 result=precheck(p,d['scenario_id'],meta);(out/(d['dataset_id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));print(d['dataset_id'],result['rows'],result.get('matched_required'),result['final_eligibility'])
p=Path('runtime/data_validation/final_search/tobacco.xlsx');meta={'source_type':'DERIVED_REAL','source_hash':hashlib.sha256(p.read_bytes()).hexdigest(),'evidence_source':'https://www.nature.com/articles/s41598-026-49347-9','license':'Apache-2.0 declared for Zenodo archive; proprietary full source not included','analysis_allowed':True,'sampling_interval':1,'sampling_evidence':'article instrumentation section; actual _time 1s','normalization_status':'unknown','no_equivalent':4}
r=precheck(p,'industrial_dryer',meta);(out/'tobacco_zenodo.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False));print('tobacco',r['rows'],r['columns'],r['final_eligibility'])
