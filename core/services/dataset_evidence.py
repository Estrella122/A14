"""Offline, explicit dataset restoration. Never infer scale from field bounds."""
from hashlib import sha256
from pathlib import Path
import math


def restore_normalized_fields(source, metadata, expected_units):
    """Return a restored copy + receipt; callers must verify metadata provenance.

    No Runtime hook or automatic conversion: absent/incomplete metadata fails
    closed before loading or altering data. The source is never overwritten.
    """
    import pandas as pd
    source = Path(source)
    digest = sha256(source.read_bytes()).hexdigest()
    if not isinstance(metadata, dict) or metadata.get('source_hash') != digest:
        raise ValueError('缺少与源文件 SHA256 绑定的逆归一化元数据')
    if not metadata.get('evidence') or not metadata.get('source_file'):
        raise ValueError('缺少可核查的元数据来源')
    if Path(metadata['source_file']).name != source.name:
        raise ValueError('元数据源文件名不一致')
    method = metadata.get('normalization_method')
    parameters = metadata.get('inverse_transform_parameters', {})
    if method not in {'minmax_0_1', 'zscore'} or not expected_units:
        raise ValueError('未声明支持的归一化公式或物理单位')
    for field, unit in expected_units.items():
        param = parameters.get(field, {})
        keys = ('min', 'max') if method == 'minmax_0_1' else ('mean', 'std')
        if param.get('unit') != unit or not param.get('source_column'):
            raise ValueError(f'{field}: 缺少字段来源或单位不匹配')
        if any(isinstance(param.get(k), bool) or not isinstance(param.get(k), (float, int)) or not math.isfinite(param[k]) for k in keys):
            raise ValueError(f'{field}: 缺少有限逆变换参数')
        if method == 'minmax_0_1' and param['max'] <= param['min'] or method == 'zscore' and param['std'] <= 0:
            raise ValueError(f'{field}: 无效缩放范围')
    frame = pd.read_csv(source)
    from integrations.standardization.standard_agent.engine import StandardizationAgent
    from integrations.standardization.standard_agent.physical_semantics import final_field_acceptance_gate
    agent = StandardizationAgent()
    if not metadata.get('scenario_id'):
        raise ValueError('逆变换字段身份必须绑定 scenario_id')
    template = agent.repository.get(metadata['scenario_id'])
    acceptance_audits = {}
    restored = frame.copy()
    for field in expected_units:
        param = parameters[field]
        item = {'raw':param['source_column'], 'base_name':param['source_column'], 'standard':field, 'method':'normalization_mapping', 'confidence':1., 'unit_status':'consistent', 'expected_unit':expected_units[field]}
        bound = {'standard_field':field, 'scenario_id':metadata['scenario_id'], 'evidence_source':metadata['evidence'], 'unit':param['unit'], 'normalized':True, 'inverse_metadata':param, 'transform_applied':True, 'source_hash':digest}
        acceptance = final_field_acceptance_gate(item, template, agent.auto_threshold, bound)
        if acceptance['decision'] != 'AUTO_ACCEPT':
            raise ValueError(f'{field}: ' + acceptance['decision_reason'])
        acceptance_audits[field] = acceptance['final_acceptance_audit']
        values = pd.to_numeric(frame[param['source_column']], errors='raise')
        restored[field] = values * (param['max'] - param['min']) + param['min'] if method == 'minmax_0_1' else values * param['std'] + param['mean']
    receipt = {'source_file':str(source.resolve()), 'source_hash':digest,
        'normalization_method':method, 'inverse_transform_parameters':parameters,
        'restored_fields':list(expected_units), 'units':expected_units,
        'evidence':metadata['evidence'], 'source_overwritten':False,
        'provenance_verified_automatically':False, 'final_acceptance_audits':acceptance_audits}
    return restored, receipt
