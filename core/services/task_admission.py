"""Task-specific availability. Exploration never grants a scene contract PASS."""
import pandas as pd
from core.skills.artifacts import RuntimeArtifactResolver


def capability_availability(snapshot, requested_task='knowledge'):
    standard = (snapshot or {}).get('results', {}).get('standardization', {})
    mapping = standard.get('mapping', {})
    decision = standard.get('data_decision', {})
    missing = list(mapping.get('missing_required') or [])
    if not standard:
        missing.append('trusted_scene_contract')
    if mapping.get('review_count') or standard.get('detection', {}).get('is_ambiguous'):
        missing.append('field_mapping_review')
    if decision.get('status') == 'reject':
        missing.append('scene_contract_review')
    resolver = RuntimeArtifactResolver(snapshot or {})
    source = resolver.resolve('SOURCE_DATA')
    available = ['knowledge', 'method_explanation', 'gap_explanation']
    if (snapshot or {}).get('results'):
        available.append('read_existing_results')
    if source or isinstance((snapshot or {}).get('_dataframe'), pd.DataFrame):
        available.append('basic_data_exploration')
    blocked = {}
    if 'basic_data_exploration' not in available:
        blocked['basic_data_exploration'] = ['authorized_source_data']
    # Exact downstream artifact/quality readiness remains owned by the runtime.
    for task in ('physical_statistics', 'model_training', 'optimization'):
        blocked[task] = missing or ['task_input_contract_and_validation_gates_required']
    blocked['production_control'] = ['independent_validation', 'safety_interlocks', 'human_control_approval']
    return {'available_tasks': available, 'blocked_tasks': blocked, 'missing_requirements': missing,
            'requested_task_status': 'available' if requested_task in available else 'requires_task_gates',
            'next_actions': ['确认缺失字段的物理身份、单位和时间条件后再检查建模契约'] if missing else ['按目标检查已冻结分区和模型验证证据'],
            'pending_quality_review': standard.get('schema_validation', {}).get('failure_count', 0),
            'full_scene_contract_pass': bool(standard and not missing and decision.get('status') == 'accept')}


def basic_data_profile(snapshot):
    resolver = RuntimeArtifactResolver(snapshot)
    ref = resolver.resolve('SOURCE_DATA')
    if ref:
        # Raw columns remain raw: no unit/identity inference or cleaning.
        frame = pd.read_csv(ref.path)
        provenance = ref.public()
    elif isinstance(snapshot.get('_dataframe'), pd.DataFrame):
        frame = snapshot['_dataframe'].copy()
        provenance = {'run_id': snapshot.get('run_id'), 'source': 'provided_dataframe'}
    else:
        raise ValueError('当前运行没有可读取的原始数据')
    fields = []
    for name in frame:
        series = frame[name]
        time_ratio = None
        if not pd.api.types.is_numeric_dtype(series) and any(token in str(name).lower() for token in ('time', 'date', '时间', '日期')):
            parsed = pd.to_datetime(series, errors='coerce', format='mixed')
            time_ratio = float(parsed.notna().mean()) if len(series) else None
        fields.append({'raw_name': str(name), 'dtype': str(series.dtype), 'missing_count': int(series.isna().sum()),
                       'missing_rate': float(series.isna().mean()) if len(series) else None,
                       'constant': bool(series.nunique(dropna=True) <= 1), 'time_parseable_ratio': time_ratio})
    return {'row_count': len(frame), 'column_count': len(frame.columns), 'duplicate_rows': int(frame.duplicated().sum()),
            'fields': fields, 'source': provenance, 'contract_status': 'NOT_EVALUATED', 'algorithm': 'raw_dataframe_profile',
            'limitations': ['只描述原始列，不赋予未经确认的物理身份或单位；不清洗、不训练、不寻优']}
