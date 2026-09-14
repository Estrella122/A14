"""Evidence-authored labels and offline evaluation; never self-label using model output.

No model training or data conversion is performed here. Unavailable source files
stay unreviewed. Existing model predictions are evaluated only AFTER labels exist.
"""
import csv, hashlib, json, re, sys, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.environ.setdefault('DJANGO_SETTINGS_MODULE','heating_furnace_apc.settings')
import django;django.setup()
import pandas as pd
from integrations.standardization.standard_agent.engine import StandardizationAgent, normalize_name


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))

def build():
    sources=json.loads((ROOT/'three_scene_real_runtime.json').read_text())['candidates']
    contracts={}
    for scene in ['blast_furnace','debutanizer_column','industrial_dryer']:
        base=ROOT/'integrations/standardization/standards/scenarios'/scene
        contracts[scene]={'template':json.loads((base/'template.json').read_text()),'fields':{f['standard_name']:f for f in csv.DictReader((base/'fields.csv').open())}}
    bfpath=ROOT/'frontend/public/datasets/blast_furnace_real_720h.csv'
    sources=[{'scene':'blast_furnace','dataset_name':'Fixed Mendeley derived 720h','source_url':'datasets/real_candidates/blast_furnace_mendeley/derived_manifest.json','local_path':str(bfpath),'columns':list(pd.read_csv(bfpath,nrows=0)),'sha256':digest(bfpath),'source_type':'DERIVED','units':'source documentation + audited preparation script','target':'hot_metal_si'}]+sources
    datasets=[];rows=[]
    for number,s in enumerate(sources):
        scene=s['scene'];name=s['dataset_name'];ident=f'dataset_{number:02d}';c=contracts[scene];fields=c['fields'];columns=s.get('columns') or [];path=Path(s['local_path']) if s.get('local_path') else None
        if path and path.suffix=='.csv' and path.exists():
            columns=list(pd.read_csv(path,nrows=0,encoding='cp1252' if path.name=='lost_plant.csv' else 'utf-8-sig'))
        local=s.get('source_url','');lp=ROOT/local
        if not columns and lp.is_file() and lp.suffix=='.csv':columns=list(pd.read_csv(lp,nrows=0));path=lp
        rec={'dataset_id':ident,'scenario_id':scene,'dataset_name':name,'source_url':s['source_url'],'source_type':s['source_type'],'source_path':str(path) if path else None,'source_hash':digest(path) if path and path.exists() else s.get('sha256'),'source_columns':columns,'real_evaluation_eligible':not any(x in s['source_type'] for x in ['SYNTHETIC','未证实','待核实']),'review_status':'evidence_reviewed' if columns else 'SOURCE_UNAVAILABLE','normalization_status':s.get('normalization_status'),'source_metadata':s}
        datasets.append(rec)
        for col in columns:
            target=None;decision='REVIEW_REQUIRED';why='来源未提供可核验的对应测点/单位；不推断';unit=None;loc=None;direction=None;quantity=None;equipment=None;role=None;description=col;confidence='LOW';evidence=s['source_url']
            if scene=='blast_furnace' and col in fields:
                target=col;decision='MATCH';why='实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签';unit=fields[col]['unit'];description=fields[col]['description'];confidence='HIGH';evidence='datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json'
                loc=description;equipment='blast_furnace';role=fields[col]['role'];quantity=fields[col]['data_type']
            elif scene=='blast_furnace':
                decision='NO_EQUIVALENT';why='转换脚本产生的化验时效辅助元数据，不当作必需过程测量';confidence='HIGH'
            elif 'LostRunes' in name:
                # Human interpretation of file header, DCS tag row and unit row.
                table={'Unnamed: 0':('timestamp','MATCH','datetime','clock',None,'timestamp','源第二行明确Date /Time；是时间列，不以位置猜测'),
                       'Reflux flow':('reflux_flow','MATCH','t/h','reflux_line','reflux','flow','源单位TPH，明确回流而非产品流量'),
                       'Column top Temp':('top_temperature','REVIEW_REQUIRED',None,'column_top',None,'temperature','位置明确，但源温标字符编码异常，尚未核验degC'),
                       'Column Top pressure':('top_pressure','REVIEW_REQUIRED',None,'column_top',None,'pressure','表压kg/cm²g与当前Pa基准/编码需明确'),
                       'Column bottom temp':('bottom_temperature_a','REVIEW_REQUIRED',None,'column_bottom',None,'temperature','只有一个底温，未明确A/B身份，不能复制为两个测点'),
                       'Control tay temp':('tray6_temperature','REVIEW_REQUIRED',None,'control_tray_unknown_number',None,'temperature','控制板未证明是第六板'),
                       'Reboiler o/l Temp':('bottom_temperature_b','NO_EQUIVALENT',None,'reboiler_outlet','outlet','temperature','不同设备/位置；绝非第二底温'),
                       'Feed Flow to DB':('next_process_flow','NO_EQUIVALENT','t/h','feed_line','inlet','flow','流入塔的进料不是流向下游的产品'),
                       'Reboiling steam flow':(None,'NO_EQUIVALENT','t/h','reboiler_steam','inlet','flow','蒸汽加热公用工程不是回流或下游产品'),
                       'C4H6 in DB bottom':('bottom_butane_content','NO_EQUIVALENT','percent','column_bottom',None,'composition','C4H6不是丁烷C4H10'),
                       'C4H8 in DB bottom':('bottom_butane_content','NO_EQUIVALENT','percent','column_bottom',None,'composition','C4H8不是丁烷C4H10')}
                target,decision,unit,loc,direction,quantity,why=table[col];confidence='HIGH' if decision!='REVIEW_REQUIRED' else 'MEDIUM';equipment='reboiler' if col.startswith('Reboil') else 'debutanizer_column';role='process_measurement'
            elif 'DAISY' in name:
                table={'sample_index':('timestamp','REVIEW_REQUIRED', 'sample','sequence',None,'time','来源确认10秒有序采样；无日历起点，当前墙钟接入尚需显式转换'),
                'fuel_flow':(None,'NO_EQUIVALENT',None,'heater','inlet','flow','燃料流量不是热风温度'),
                'exhaust_fan_speed':('drying_air_flow','NO_EQUIVALENT',None,'exhaust_fan','outlet','speed','转速不是标准体积风量'),
                'raw_material_flow':('wet_feed_rate','REVIEW_REQUIRED',None,'feed','inlet','flow','原料流量意义接近，但单位和偏置缺失'),
                'dry_bulb_temperature':('hot_air_temperature','REVIEW_REQUIRED',None,'unknown',None,'temperature','干球测温位置不明，不能当入口或出口温度'),
                'wet_bulb_temperature':('exhaust_humidity','NO_EQUIVALENT',None,'unknown',None,'temperature','湿球温度不是相对湿度'),
                'raw_material_moisture':('product_moisture','NO_EQUIVALENT',None,'raw_material','inlet','moisture','原料水分不是出口产品水分；负值无逆变换说明')}
                target,decision,unit,loc,direction,quantity,why=table[col];equipment='industrial_dryer';role='process_measurement';confidence='HIGH' if decision=='NO_EQUIVALENT' else 'MEDIUM';evidence='runtime/data_validation/public_candidates/daisy_dryer_description.txt'
            elif scene=='debutanizer_column' and re.fullmatch(r'[uU][1-8]|y',col):
                # U labels retain documented identity only; never infer actual units.
                n=8 if col=='y' else int(col[1:]);mapping=['top_temperature','top_pressure','reflux_flow','next_process_flow','tray6_temperature','bottom_temperature_a','bottom_temperature_b','bottom_butane_content'];target=mapping[n-1];why='命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据';decision='REVIEW_REQUIRED';confidence='MEDIUM';unit='dimensionless';equipment='debutanizer_column';quantity='normalized';evidence='datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md'
            elif 'Coffee microwave' in name:
                target='timestamp' if col=='A' else None;unit='s' if col=='A' else None;why='来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分';confidence='MEDIUM';evidence='runtime/data_validation/public_candidates/coffee.xlsx'
            if 'SYNTHETIC' in s['source_type']:
                decision='REVIEW_REQUIRED';why='合成开发样本，禁止作为真实字段验收真值';confidence='LOW'
            row=dict(dataset_id=ident,scenario_id=scene,source_column=col,source_description=description,source_unit=unit,source_equipment=equipment,source_location=loc,source_direction=direction,source_quantity_type=quantity,source_role=role,candidate_standard_field=target,ground_truth_decision=decision,ground_truth_reason=why,evidence_source=evidence,confidence=confidence)
            rows.append(row)
        # No source equivalence cannot be disguised as a fabricated source column.
        accounted={r['candidate_standard_field'] for r in rows if r['dataset_id']==ident and r['ground_truth_decision'] in {'MATCH','REVIEW_REQUIRED'}}
        for field,definition in fields.items():
            if definition['required']=='true' and field not in accounted:
                rows.append(dict(dataset_id=ident,scenario_id=scene,source_column=None,source_description=None,source_unit=None,source_equipment=None,source_location=None,source_direction=None,source_quantity_type=None,source_role=None,candidate_standard_field=field,ground_truth_decision='MISSING_STANDARD_FIELD' if columns else 'REVIEW_REQUIRED',ground_truth_reason='完整已读字段表未发现可信对应测点' if columns else '未取得原文件，不能断言物理传感器不存在；获取源文件前待复核',evidence_source=s['source_url'],confidence='HIGH' if columns else 'LOW'))
    out={'version':'evidence-v1','label_authority':'explicit document interpretation; no prediction-derived labels','datasets':datasets,'fields':rows,'contracts':contracts}
    dump(ROOT/'real_field_ground_truth.json',out)
    text=['# 真实字段Ground Truth','证据标注不使用模型预测生成标签。MATCH同时要求测点与计量含义可确认；仅名称身份对应但缺单位/逆变换的字段为REVIEW_REQUIRED。无文件候选保持未标注，不伪造缺失传感器事实。','|dataset|source|canonical|decision|reason|evidence|','|---|---|---|---|---|---|']
    for row in rows:text.append('| '+' | '.join(str(row[k] or '—').replace('|','/') for k in ['dataset_id','source_column','candidate_standard_field','ground_truth_decision','ground_truth_reason','evidence_source'])+' |')
    (ROOT/'real_field_ground_truth.md').write_text('\n'.join(text))
    return out


def evaluate(gt):
    agent=StandardizationAgent();coverage=[];evaluations=[]
    for dataset in gt['datasets']:
        fields=[r for r in gt['fields'] if r['dataset_id']==dataset['dataset_id']];scene=dataset['scenario_id'];req={k for k,v in gt['contracts'][scene]['fields'].items() if v['required']=='true'}
        matched={r['candidate_standard_field'] for r in fields if r['ground_truth_decision']=='MATCH'}&req
        review={r['candidate_standard_field'] for r in fields if r['ground_truth_decision']=='REVIEW_REQUIRED'}&req
        missing={r['candidate_standard_field'] for r in fields if r['ground_truth_decision']=='MISSING_STANDARD_FIELD'}&req
        known_agent_fail=[]
        actual={}
        if dataset['source_columns']:
            frame=None
            if dataset['source_path'] and dataset['source_path'].endswith('.csv'):
                try:frame=pd.read_csv(dataset['source_path'],encoding='cp1252' if 'lost_plant' in dataset['source_path'] else 'utf-8-sig')
                except (ValueError,UnicodeError):pass
            actual={m['raw']:m for m in agent.map_columns(dataset['source_columns'],scene,frame)['mappings']}
        for row in fields:
            if row['source_column'] is None:continue
            m=actual.get(row['source_column'],{});target=row['candidate_standard_field'];pred=[]
            if agent.semantic_model:
                pred=agent.semantic_model.predict(row['source_column'],scene,limit=5)
            recall=list(dict.fromkeys([m['standard']] if m.get('standard') else []))+[x['standard_name'] for x in pred]
            recall=list(dict.fromkeys(recall))[:5]
            final='MATCH' if m.get('status')=='matched' else 'REVIEW_REQUIRED' if m.get('status')=='review' else 'NO_MATCH'
            evaluations.append({'real_evaluation_eligible':dataset['real_evaluation_eligible'],'dataset_id':dataset['dataset_id'],'scenario':scene,'source':row['source_column'],'expected':row['ground_truth_decision'],'target':target,'prediction':final,'predicted_field':m.get('standard'),'top_candidates':recall,'top3_hit':target in recall[:3] if target and row['ground_truth_decision']=='MATCH' else None,'mapping':m})
            if row['ground_truth_decision']=='MATCH' and not (final=='MATCH' and m.get('standard')==target):known_agent_fail.append(row['source_column'])
        # Blank-header timestamp has explicit metadata preprocessing, not a learnable
        # lexical alias. Keep this integration limitation separate from model accuracy.
        learnable=[x for x in known_agent_fail if x!='Unnamed: 0']
        category='CAN_RUN_NOW' if matched==req and not known_agent_fail else 'AGENT_LIMITED' if matched==req else 'MIXED_LIMITATION' if known_agent_fail else 'DATA_LIMITED'
        optional={k for k,v in gt['contracts'][scene]['fields'].items() if v['required']!='true'}
        coverage.append({'dataset_id':dataset['dataset_id'],'scenario':scene,'name':dataset['dataset_name'],'required_field_count':len(req),'matched_required_count':len(matched),'review_required_count':len(review-matched),'missing_required_count':len(missing-matched-review),'no_equivalent_count':sum(r['ground_truth_decision']=='NO_EQUIVALENT' for r in fields),'optional_field_coverage':len({r['candidate_standard_field'] for r in fields if r['ground_truth_decision']=='MATCH'}&optional)/len(optional) if optional else None,'coverage':len(matched)/len(req),'classification':category,'agent_unrecognized_verified_fields':known_agent_fail,'learnable_verified_fields':learnable})
    dump(ROOT/'datasets/field_ground_truth/coverage.json',coverage);dump(ROOT/'datasets/field_ground_truth/evaluation.json',evaluations)
    return coverage,evaluations


if __name__=='__main__':
    gt=build();c,e=evaluate(gt);print('sources',len(gt['datasets']),'ground truth rows',len(gt['fields']),'learnable gaps',[(x['name'],x['learnable_verified_fields']) for x in c if x['learnable_verified_fields']])
