"""Read-only, fail-closed real-data precheck. Does not execute or train a pipeline.

Usage: python tools/precheck_real_dataset.py SOURCE --scene SCENE --metadata META.json --output dataset_precheck.json
Source metadata must be independently verified; this utility does not authenticate it.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integrations.standardization.standard_agent.engine import StandardizationAgent

def precheck(source, scene, metadata=None):
    metadata=metadata or {};source=Path(source);agent=StandardizationAgent();template=agent.repository.get(scene)
    required={f.standard_name for f in template.fields if f.required};target=template.config.get('field_roles',{}).get('target')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    result={'source':str(source.resolve()),'source_hash':digest,'scene':scene,'required_count':len(required),'target':target,'source_metadata':metadata,'provenance_authenticated_by_tool':False}
    try:
        if source.suffix.lower()=='.xlsx':frame=pd.read_excel(source,sheet_name=metadata.get('sheet',0))
        else:
            options={'encoding':metadata.get('encoding','utf-8-sig'),'skiprows':metadata.get('skiprows',0)}
            if metadata.get('documented_columns'):
                if not metadata.get('layout_evidence'):raise ValueError('Headerless data needs documented layout evidence; no column-position guessing')
                options.update(header=None,names=metadata['documented_columns'],sep=metadata.get('separator',r'\s+'))
            frame=pd.read_csv(source,**options)
    except Exception as exc:
        return {**result,'rows':None,'columns':None,'final_eligibility':'UNUSABLE','reasons':[type(exc).__name__+': '+str(exc)]}
    mapping=agent.map_columns(list(map(str,frame.columns)),scene,frame)
    accepted={r['standard']:r['raw'] for r in mapping['mappings'] if r['status']=='matched'}
    review={r['standard'] for r in mapping['mappings'] if r['status']=='review'} & required
    matched=set(accepted)&required;missing=required-matched-review
    timestamp=template.config.get('field_roles',{}).get('timestamp','timestamp');time_status='missing_or_not_accepted';sampling_status='unverified';seconds=None;time_coverage=None;duplicate_timestamps=None
    if timestamp in accepted:
        values=frame[accepted[timestamp]]
        if not pd.api.types.is_numeric_dtype(values):
            times=pd.to_datetime(values,errors='coerce')
            duplicate_timestamps=int(times.dropna().duplicated().sum())
            if times.notna().all() and times.is_monotonic_increasing and times.is_unique:
                time_status='valid';deltas=times.diff().dt.total_seconds().dropna();seconds=float(deltas.median()) if len(deltas) else None;time_coverage=[str(times.iloc[0]),str(times.iloc[-1])]
                if metadata.get('sampling_interval') and seconds==float(metadata['sampling_interval']) and metadata.get('sampling_evidence'):sampling_status='documented_and_consistent'
    units=metadata.get('units',{});units_ok=isinstance(units,dict) and all(units.get(k)==template.by_name[k].unit for k in required if k!=timestamp)
    source_ok=metadata.get('source_type') in {'REAL_PLANT','PUBLIC_REAL_PROCESS','PUBLIC_EXPERIMENT','BENCHMARK_REAL','DERIVED_REAL'} and metadata.get('source_hash')==digest and bool(metadata.get('evidence_source'))
    license_ok=metadata.get('analysis_allowed') is True and bool(metadata.get('license'))
    target_count=int(pd.to_numeric(frame[accepted[target]],errors='coerce').notna().sum()) if target in accepted else 0
    normalized=metadata.get('normalization_status');normal_ok=normalized=='physical' or (normalized=='restored' and bool(metadata.get('transformation_manifest')))
    reasons=[]
    if not source_ok:reasons.append('MISSING_METADATA: source class/hash/evidence not verified')
    if not license_ok:reasons.append('LICENSE_BLOCKED: permitted analysis not established')
    if matched!=required:reasons.append('MISSING_REQUIRED_SENSORS_OR_MAPPING: '+', '.join(sorted(required-matched)))
    if not units_ok:reasons.append('MISSING_METADATA: canonical physical units not independently documented')
    if time_status!='valid' or sampling_status!='documented_and_consistent':reasons.append('MISSING_METADATA: timestamp or sampling not verified')
    if not normal_ok:reasons.append('NORMALIZATION_BLOCKED: physical scale/restoration not verified')
    if len(frame)<150 or target_count==0:reasons.append('INSUFFICIENT_DATA: less than existing 150-row minimum or no target observations')
    if not reasons:eligibility='ELIGIBLE'
    elif metadata.get('source_type') in {'SYNTHETIC','UNKNOWN'} or not license_ok:eligibility='UNUSABLE'
    elif not normal_ok:eligibility='NORMALIZATION_BLOCKED'
    elif missing:eligibility='DATA_LIMITED'
    elif review:eligibility='REVIEW_BLOCKED'
    else:eligibility='METADATA_LIMITED'
    return {**result,'rows':len(frame),'columns':list(map(str,frame.columns)),'time_coverage':time_coverage,'timestamp_status':time_status,'duplicate_timestamp_count':duplicate_timestamps,'sampling_status':sampling_status,'observed_sampling_seconds':seconds,'unit_status':'documented' if units_ok else 'unverified','target_status':{'accepted':target in accepted,'valid_observations':target_count},'matched_required':len(matched),'review_required':len(review),'missing_required':len(missing),'missing_fields':sorted(missing),'review_fields':sorted(review),'no_equivalent':metadata.get('no_equivalent'),'required_field_coverage':len(matched)/len(required),'physical_gate_results':mapping['mappings'],'normalization_status':normalized or 'unknown','inverse_metadata_status':metadata.get('inverse_metadata_status','unknown'),'missing_rate':float(frame.isna().mean().mean()),'constant_ratio':float((frame.nunique(dropna=True)<=1).mean()),'final_eligibility':eligibility,'reasons':reasons}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--scene',required=True);parser.add_argument('--metadata',type=Path);parser.add_argument('--output',type=Path,default=Path('dataset_precheck.json'));args=parser.parse_args()
    result=precheck(args.source,args.scene,json.loads(args.metadata.read_text()) if args.metadata else {})
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));print(result['final_eligibility'])
