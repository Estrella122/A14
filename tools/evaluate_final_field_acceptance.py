"""Post-safety evidence; preserve previous frozen ground truth/evaluation artifacts."""
import json
from pathlib import Path
import evaluate_real_field_ground_truth as ground
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'datasets/field_acceptance_safety'
gt=json.loads((ROOT/'real_field_ground_truth.json').read_text())
old={name:(ROOT/'datasets/field_ground_truth'/name).read_bytes() for name in ['evaluation.json','coverage.json']}
try:
    coverage,after=ground.evaluate(gt)
finally:
    for name,blob in old.items():(ROOT/'datasets/field_ground_truth'/name).write_bytes(blob)
for name,value in [('after.json',after),('coverage.json',coverage)]:
    (P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))
before=json.loads((P/'before.json').read_text());previous={(r['dataset_id'],r['source']):r for r in before}
def wrong(r):return r['prediction']=='MATCH' and (r['expected']!='MATCH' or r['predicted_field']!=r['target'])
result={}
for scene in ['blast_furnace','debutanizer_column','industrial_dryer']:
    rows=[r for r in after if r['scenario']==scene and r['real_evaluation_eligible']]
    prior=[previous[(r['dataset_id'],r['source'])] for r in rows]
    result[scene]={'source_column_count':len(rows),'previous_auto_accept_count':sum(r['prediction']=='MATCH' for r in prior),'previous_wrong_accept_count':sum(wrong(r) for r in prior),'new_auto_accept_count':sum(r['prediction']=='MATCH' for r in rows),'new_wrong_accept_count':sum(wrong(r) for r in rows),'review_count':sum(r['prediction']=='REVIEW_REQUIRED' for r in rows),'reject_count':sum(r['prediction']=='NO_MATCH' for r in rows),'new_false_rejects':[r['source'] for r in rows if previous[(r['dataset_id'],r['source'])]['prediction']=='MATCH' and r['expected']=='MATCH' and r['prediction']!='MATCH'],'critical_wrong_accepts':[r['source'] for r in rows if wrong(r) and gt['contracts'][scene]['fields'].get(r['predicted_field'],{}).get('required')=='true']}
(P/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
