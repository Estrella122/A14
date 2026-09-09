"""Frozen holdout evaluation. Does not modify the model, gates, or datasets."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from time import perf_counter
from statistics import mean
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from django.conf import settings
if not settings.configured:settings.configure(BASE_DIR=ROOT)
from core.skills.runtime import plan_skills
from core.skills.catalog import SKILLS
from core.skills.routing import SUPPORT
from core.skills.router_model import predict,normalize,MODEL_PATH
spec=importlib.util.spec_from_file_location('core.skills.baseline_runtime',Path(__file__).parent/'baseline_runtime.py')
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
DATA=Path(__file__).parent/'data'
REPORTS=Path(__file__).parent/'reports'

def read(name):return [json.loads(line) for line in (DATA/f'{name}.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
def metrics(rows,key):
    labels=[s.id for s in SKILLS if s.id not in SUPPORT]
    per_skill=[];tp=fp=fn=0;exact=0;top1=0
    for label in labels:
        a=sum(label in r['expected'] and label in r[key]['selected'] for r in rows)
        b=sum(label not in r['expected'] and label in r[key]['selected'] for r in rows)
        c=sum(label in r['expected'] and label not in r[key]['selected'] for r in rows)
        tp+=a;fp+=b;fn+=c
        per_skill.append({'skill_id':label,'support':sum(label in r['expected'] for r in rows),'precision':a/(a+b) if a+b else 0.,'recall':a/(a+c) if a+c else 0.,'f1':2*a/(2*a+b+c) if 2*a+b+c else 0.,'false_positives':b,'false_negatives':c})
    for r in rows:
        exact+=set(r['expected'])==set(r[key]['selected'])
        top1+=r[key]['top1'] in r['expected'] if r['expected'] else r[key]['top1'] is None
    inscope=[r for r in rows if r['expected']]
    accepted=[r for r in inscope if r[key]['selected']]
    unknown=[r for r in rows if not r['expected']]
    return {'case_count':len(rows),'exact_skill_set_accuracy':exact/len(rows),'top1_accuracy':top1/len(rows),
            'micro_precision':tp/(tp+fp) if tp+fp else 0,'micro_recall':tp/(tp+fn) if tp+fn else 0,
            'micro_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,'macro_f1':mean(s['f1'] for s in per_skill),
            'in_scope_coverage':len(accepted)/len(inscope),
            'accepted_exact_accuracy':sum(set(r['expected'])==set(r[key]['selected']) for r in accepted)/len(accepted) if accepted else 0,
            'out_of_scope_rejection':sum(not r[key]['selected'] for r in unknown)/len(unknown),
            'mean_direct_skill_count':mean(len(r[key]['selected']) for r in rows),
            'mean_latency_ms':mean(r[key]['latency_ms'] for r in rows),
            'per_skill':per_skill}

def main():
    train,val,test=read('train'),read('validation'),read('test')
    for left,right in [(train,val),(train,test),(val,test)]:
        assert not {r['group'] for r in left}&{r['group'] for r in right}
        assert not {normalize(r['text']) for r in left}&{normalize(r['text']) for r in right}
    model_before=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    predict('暖机');rows=[]
    order={s.id:i for i,s in enumerate(SKILLS)}
    for case in test:
        t=perf_counter();analysis=baseline._request_analysis(case['text'])
        direct,scores,_=baseline._direct_matches(case['text'],analysis)
        direct=direct-SUPPORT
        ranked=sorted(direct,key=lambda sid:(-scores.get(sid,0),order[sid]))
        before={'selected':sorted(direct),'top1':ranked[0] if ranked else None,'mode':analysis['mode'],'latency_ms':(perf_counter()-t)*1000}
        t=perf_counter();p=plan_skills(case['text']);selected=p['direct_skill_ids']
        scores={s['skill_id']:s['relevance_score'] for s in p['steps'] if s['selection_kind']=='direct'}
        ranked=sorted(selected,key=lambda sid:(-scores.get(sid,0),order[sid]))
        after={'selected':selected,'top1':ranked[0] if ranked else None,'mode':p['mode'],'needs_clarification':p['analysis']['needs_clarification'],'source':p['analysis']['routing_source'],'latency_ms':(perf_counter()-t)*1000}
        raw=predict(case['text'])
        rows.append({'id':case['id'],'text':case['text'],'expected':case['labels'],'baseline':before,'trained_router':after,'raw_model_top1':raw['top_label']})
    report={'test_source':'assistant_authored_synthetic_holdout','production_accuracy_claim':False,
            'split_integrity':'passed: disjoint normalized text and seed groups; wrappers only within train',
            'model_sha256':model_before,'test_sha256':hashlib.sha256((DATA/'test.jsonl').read_bytes()).hexdigest(),
            'baseline':metrics(rows,'baseline'),'trained_router':metrics(rows,'trained_router'),
            'raw_model_top1_accuracy':sum(r['raw_model_top1'] in r['expected'] if r['expected'] else r['raw_model_top1']=='__none__' for r in rows)/len(rows),
            'baseline_top1_definition':'Highest old keyword score; ties follow original catalog order because the original router exposes no unique top-1.',
            'routing_metric_definition':'Direct business skill IDs only; dependency and orchestration steps excluded from both sides.',
            'limitations':['Small authored test set; no independent human labeling or real traffic.','Hybrid router includes explicit-action guards and existing expert evidence contracts.','Do not tune on this test set; add a fresh held-out set after future changes.'],
            'errors':[r for r in rows if set(r['expected'])!=set(r['trained_router']['selected'])]}
    assert model_before==hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (REPORTS/'test_predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    compact={k:v for k,v in report.items() if k not in ['baseline','trained_router','errors']}
    compact.update({k:{a:b for a,b in report[k].items() if a!='per_skill'} for k in ['baseline','trained_router']})
    compact['errors']=[{'text':r['text'],'expected':r['expected'],'actual':r['trained_router']['selected']} for r in report['errors']]
    print(json.dumps(compact,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
