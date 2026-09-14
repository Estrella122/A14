"""Frozen offline corpus/evaluation; no fitting without a verified learnable gap."""
import json,hashlib,sys,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('DJANGO_SETTINGS_MODULE','heating_furnace_apc.settings')
import django;django.setup()
from integrations.standardization.standard_agent.engine import StandardizationAgent, normalize_name
from integrations.standardization.standard_agent.physical_semantics import evaluate
import pandas as pd
from core.services import pipeline
P=ROOT/'datasets/field_ground_truth'
def dump(name,x):(P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
def norm(x):return normalize_name(x).replace('_','')

def corpus():
    gt=json.loads((ROOT/'real_field_ground_truth.json').read_text());examples=[]
    def example(scene,source,target,label,kind,reason,split,group,props=None):
        field=gt['contracts'][scene]['fields'].get(target,{})
        meta=gt['contracts'][scene]['template'].get('physical_semantics',{}).get(target,{})
        props=props or {}
        e=dict(scenario=scene,source_field=source,candidate_field=target,source_unit=props.get('source_unit'),candidate_unit=field.get('unit'),label=label,sample_type=kind,reason_codes=[reason],source_type='real' if kind=='real' else 'alias' if kind=='alias' else 'synthetic_format_augmentation',scenario_split_group=group,split=split)
        for k in ['quantity_type','role','location','direction','equipment']:
            e['source_'+k]=props.get('source_'+k)
            e['candidate_'+k]=meta.get({'role':'physical_role','location':'measurement_location','direction':'flow_direction','equipment':'equipment_role'}.get(k,k))
        examples.append(e)
    real_sources={norm(r['source_column']) for r in gt['fields'] if r['source_column']}
    for scene,c in gt['contracts'].items():
        for field,d in c['fields'].items():
            group='canonical:'+field
            n=int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%10
            split='train' if n<6 else 'validation' if n<8 else 'test'
            for alias in [field]+d['aliases'].split('|'):
                if not alias or norm(alias) in real_sources:continue
                example(scene,alias,field,'MATCH','alias','curated_contract_alias; no real-data unit inference',split,group,{'source_unit':d['unit']})
    eligible={d['dataset_id'] for d in gt['datasets'] if d['real_evaluation_eligible']}
    for row in gt['fields']:
        if row['source_column'] is None or row['dataset_id'] not in eligible:continue
        example(row['scenario_id'],row['source_column'],row['candidate_standard_field'],{'MATCH':'MATCH','REVIEW_REQUIRED':'REVIEW_REQUIRED','NO_EQUIVALENT':'NO_MATCH'}[row['ground_truth_decision']],'real',row['ground_truth_reason'],'real_unseen_test',row['dataset_id'],row)
    # Fixed held-out safety probes: never used for model fitting or threshold tuning.
    negatives=[('reactor outlet temperature [degC]','bottom_temperature_b'),('upstream inlet flow [t/h]','next_process_flow'),('tray 7 temperature [degC]','top_temperature'),('recycle flow [t/h]','next_process_flow')]
    for source,target in negatives:example('debutanizer_column',source,target,'NO_MATCH','HARD_NEGATIVE','different physical identity','hard_negative_test','negative:'+norm(source))
    example('debutanizer_column','hot blast oxygen flow [Nm3/h]','reflux_flow','NO_MATCH','HARD_NEGATIVE','cross-scene equipment and quantity basis','cross_scene_test','cross:blast_to_column')
    example('industrial_dryer','top butane concentration [%]','product_moisture','NO_MATCH','HARD_NEGATIVE','different substance/quantity','cross_scene_test','cross:column_to_dryer')
    # Union formatting-identical aliases across canonical groups to prevent leakage.
    groups={}
    for e in examples:groups.setdefault(norm(e['source_field']),[]).append(e)
    priority={'train':0,'validation':1,'test':2,'hard_negative_test':3,'cross_scene_test':4,'real_unseen_test':5}
    # Propagate strongest holdout across both source-normalization and semantic group.
    changed=True
    while changed:
        changed=False
        by_group={}
        for e in examples:by_group.setdefault(e['scenario_split_group'],[]).append(e)
        for group in list(groups.values())+list(by_group.values()):
            split=max((e['split'] for e in group),key=priority.get)
            for e in group:
                if e['split']!=split:e['split']=split;changed=True
    blob='\n'.join(json.dumps(e,ensure_ascii=False) for e in examples)+'\n';(P/'field_examples.jsonl').write_text(blob)
    manifest={'version':'evidence-v1','random_seed':None,'partitioning':'deterministic semantic-group hash; normalized-source/source-dataset holdout propagation','source_gt_sha256':hashlib.sha256((ROOT/'real_field_ground_truth.json').read_bytes()).hexdigest(),'dataset_sha256':hashlib.sha256(blob.encode()).hexdigest(),'splits':{s:sum(e['split']==s for e in examples) for s in priority},'training_performed':False,'real_unseen_caveat':'held out from THIS corpus; original pretrained model exposure unknown','feature_schema':list(examples[0])}
    dump('dataset_manifest.json',manifest)
    return examples


def metrics(examples):
    agent=StandardizationAgent();observations=json.loads((P/'evaluation.json').read_text());result={}
    for scene in ['blast_furnace','debutanizer_column','industrial_dryer']:
        # Only source columns with an explicit expected decision enter this denominator.
        rows=[r for r in observations if r['scenario']==scene and r['real_evaluation_eligible']];positive=[r for r in rows if r['expected']=='MATCH'];accepted=[r for r in rows if r['prediction']=='MATCH'];tp=sum(r['expected']=='MATCH' and r['predicted_field']==r['target'] for r in accepted);reviews=[r for r in rows if r['expected']=='REVIEW_REQUIRED'];bad=[r for r in rows if r['expected']=='NO_EQUIVALENT']
        ratio=lambda a,b:a/b if b else None
        result[scene]={'n':len(rows),'match_support':len(positive),'review_support':len(reviews),'top1_accuracy':ratio(sum(r['top_candidates'][:1]==[r['target']] for r in positive),len(positive)),'top3_recall':ratio(sum(r['target'] in r['top_candidates'][:3] for r in positive),len(positive)),'top5_recall':ratio(sum(r['target'] in r['top_candidates'][:5] for r in positive),len(positive)),'match_precision':ratio(tp,len(accepted)),'match_recall':ratio(tp,len(positive)),'false_auto_accept_count':len(accepted)-tp,'false_auto_accept_rate':ratio(len(accepted)-tp,len(rows)),'review_recall':ratio(sum(r['prediction']=='REVIEW_REQUIRED' for r in reviews),len(reviews)),'hard_negative_rejection':ratio(sum(r['prediction']!='MATCH' for r in bad),len(bad)),'limitations':'raw field-level decisions; source metadata/normalization guards can still block entire dataset; duplicate datasets not independent trials'}
    probes=[];contract=agent.repository.get('debutanizer_column').config['physical_semantics']
    for e in examples:
        if e['split']=='hard_negative_test':
            r=evaluate(e['source_field'],e['candidate_field'],'trained_model_auto',.999,'consistent',contract,.82);probes.append({'source':e['source_field'],'candidate':e['candidate_field'],'auto_accept':r['physical_gate_pass'],'trace':r})
    dump('field_metrics.json',{'before':result,'after':result,'training_performed':False,'hard_negative_probes':probes,'new_false_auto_accept':0,'new_false_auto_accept_reason':'No retraining or field decision code change; same frozen evaluation, not proof baseline false accepts are zero'})
    # OOD tests use genuinely unrelated schemas, not variants of known aliases.
    schemas={'unknown_sales':['invoice_id','customer_name','gross_total','currency'],'unknown_medical':['patient_id','diagnosis','appointment_date'],'unknown_opaque':['ZZ_901.AV','QQ_782.AV']}
    gt=json.loads((ROOT/'real_field_ground_truth.json').read_text())
    for name,match in [('blast_furnace','Fixed Mendeley'),('debutanizer_column','LostRunes'),('industrial_dryer','DAISY')]:schemas[name]=next(d['source_columns'] for d in gt['datasets'] if match in d['dataset_name'])
    scenes=[]
    for expected,cols in schemas.items():
        value=agent.detect_scenario(cols);scenes.append({'expected':expected,'columns':cols,'result':value})
    dump('scene_evaluation.json',scenes)


def cleaning():
    with pipeline._module_path(pipeline.INTEGRATIONS_DIR/'data_cleaning/src'):
        from data_cleaning_agent import DataCleaningSelectionAgent
    spec={'u':{'role':'input','min':0,'max':100,'max_step':50},'y':{'role':'output','min':0,'max':100,'max_step':50}}
    def agent():return DataCleaningSelectionAgent(spec,primary_output='y')
    source=pd.DataFrame({'u':[1.]+[float('nan')]*9+[9.],'y':[2.]+[float('nan')]*9+[8.]})
    a=agent();clean=a.process_missing_values(source)
    future=source.copy();future.iloc[-1]=[99.,99.];other=agent().process_missing_values(future)
    checks={'target_missing_preserved':bool(clean.y.isna().equals(source.y.isna())),'limited_forward_fill':bool(clean.u.iloc[1:7].eq(1).all()),'long_gap_kept_missing':bool(clean.u.iloc[7:10].isna().all()),'no_future_leakage':bool(clean.iloc[:-1].equals(other.iloc[:-1])),'no_cross_gap_interpolation':bool(clean.u.iloc[7:10].isna().all())}
    train=source.iloc[:6];test=source.iloc[6:];isolated=agent().process_missing_values(test)
    checks['test_partition_not_backfilled_from_train']=bool(isolated.u.iloc[:4].isna().all())
    dump('cleaning_evaluation.json',{'checks':checks,'input':source.where(source.notna(),None).to_json(),'strategy_log':a.logs,'strategy':'existing limited causal ffill(max6); output keep_missing','selector_training':False,'status':'NOT_NEEDED' if all(checks.values()) else 'PARTIAL'})


if __name__=='__main__':
    examples=corpus();metrics(examples);cleaning();print('corpus',len(examples),'baseline, scene/OOD and causal cleaning checks written; no fitting')
