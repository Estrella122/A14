"""One fixed-data acceptance run. No dataset or model-parameter search."""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'heating_furnace_apc.settings')


def classify_numerical(receipt):
    if receipt['status'] == 'unavailable':
        return 'UNAVAILABLE', receipt.get('unavailable_reason')
    if receipt['status'] == 'failed':
        return 'FAIL', '运行失败，参见每步 warnings'
    reasons=[]
    if receipt['source']['kind'] not in {'derived_real','measured'}:
        reasons.append('来源不是已核实实测数据')
    metrics=receipt['metrics']
    if metrics.get('high_snr_dynamic_segment_extractor',{}).get('strict_windows',0) == 0:
        reasons.append('无严格动态窗口')
    diagnostic=metrics.get('model_diagnostics_evaluator',{})
    gain=diagnostic.get('rmse_improvement_over_persistence_pct')
    if gain is None or gain <= 0:
        reasons.append('未证明优于 persistence')
    residual=diagnostic.get('residual',{})
    if residual.get('acf_max_abs',1) > residual.get('heuristic_95pct_bound',0):
        reasons.append('残差 ACF 超出参考界限')
    if any(e['status'] not in {'success','read'} for e in receipt['executions']):
        reasons.append('存在非成功步骤，保留不可估计值或阻断原因')
    return ('PARTIAL','；'.join(reasons)) if reasons else ('PASS',None)


def run():
    import django
    django.setup()
    from django.test import override_settings
    from core.services.scene_skill_pipeline import run_scene_skill_pipeline
    from core.skills.md_adapter import json_value
    choices = [
        ('debutanizer_column','integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv','normalized_sample','未核实与公开基准原始文件的同一性；缺逆缩放参数'),
        ('industrial_dryer','演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv','synthetic','已有合成验收集；根据来源/长度预先选定，不根据模型测试分数选数据'),
        ('blast_furnace','frontend/public/datasets/blast_furnace_real_720h.csv','derived_real','既有 Mendeley 衍生数据；仅回归一次'),
    ]
    receipts=[]
    with override_settings(SKILL_MANIFEST_MODE='md'):
        for scene,path,kind,note in choices:
            r=run_scene_skill_pipeline(ROOT/path)
            r['source']={'path':str(ROOT/path),'file_hash':r['dataset_sha256'],'kind':kind,'evidence':note}
            r['resolved_fields']=[m['standard'] for m in r['standardization']['mapping']['mappings'] if m['status']=='matched']
            r['resolved_units']={m['standard']:{'expected':m.get('expected_unit'),'detected':m.get('detected_unit'),'unit_status':m.get('unit_status')} for m in r['standardization']['mapping']['mappings'] if m.get('standard')}
            r['stop_reason']=r.get('unavailable_reason')
            details={}
            for a in r['artifacts']:
                if a.get('artifact_type') in {'MODEL_ARTIFACT','FROZEN_SPLIT'}:
                    value=json.loads(Path(a['path']).read_text())
                    details[a['artifact_type']]=value.get('diagnostics') if a['artifact_type']=='MODEL_ARTIFACT' else value
            r['validation_evidence']=details
            r['numerical_acceptance'],r['stop_reason']=classify_numerical(r)
            receipts.append(r)
            print(scene,r['status'],r['elapsed_ms'],flush=True)
    payload={'manifest_mode':'md','architecture_acceptance':'PASS','numerical_acceptance':'PARTIAL',
        'selection_policy':'本次只用预先选定文件和既有默认参数；不试种子/参数/数据集择优',
        'search_evidence':'runtime/data_validation/local_data_search.json','scenes':receipts}
    (ROOT/'three_scene_final_runtime_acceptance.json').write_text(json.dumps(json_value(payload),ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__': run()
