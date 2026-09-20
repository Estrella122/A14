"""Validated view of existing scene algorithm profiles, shared by every entry."""
from copy import deepcopy
import hashlib
import json
import math
import re

DEFAULTS = {
    'selection': {'window_samples': 30, 'step_samples': 15, 'strict_score': 80., 'usable_score': 60.,
        'snr_db': 10., 'min_valid_samples': 15, 'allow_usable_fallback': False, 'sparse_output': False,
        'minimum_output_observations': 1, 'modeling_top_k': 5,
        'score_weights': {'input_change': .35, 'output_response': .25, 'completeness': .2, 'anomaly': .1, 'smoothness': .1},
        'score_scales': {'input_change': 1500., 'output_response': 1800.}},
    'decoupling': {'max_lag_samples': 60, 'correlation_threshold': .9, 'vif_threshold': 10.,
        'max_features': 0, 'model_families': ['ARX', 'AR'], 'orders': [1, 2, 3], 'ridge_alphas': [0., 1., 10.]},
    'optimization': {'objective_weights': {'r2': .68, 'error': .17, 'coverage': .15},
        'bounds': {}, 'constraints': {}, 'candidates': [], 'search_space': {}},
}
ALIASES = {'window_length': 'window_samples', 'step': 'step_samples', 'top_k': 'modeling_top_k',
           'max_lag': 'max_lag_samples', 'maximum_lag_samples': 'max_lag_samples', 'corr_threshold': 'correlation_threshold'}
KEY_SECTIONS = {key: section for section, values in DEFAULTS.items() for key in values}
DESCRIPTIVE = {'selection': {'acceptance_mode'}, 'decoupling': {'target_observation_mode'}, 'optimization': set()}


class PolicyError(ValueError):
    def __init__(self, message, rejected=None):
        super().__init__(message)
        self.rejected = rejected or [{'reason': message}]


def _number(value, key, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high or integer and not isinstance(value, int):
        raise PolicyError(f'参数 {key} 必须为 {low}..{high} 范围内的' + ('整数' if integer else '有限数值'))
    return int(value) if integer else float(value)


def _normalize(values, *, scene=False):
    if not isinstance(values, dict):
        raise PolicyError('parameters 必须为对象')
    flat, ignored = {}, []
    def put(key, value, section=None):
        original = key
        if key == 'model_order':
            key, value = 'orders', [value]
        key = ALIASES.get(key, key)
        if section and key in DESCRIPTIVE[section]:
            if not scene:
                raise PolicyError(f'{section}.{key} 仅为说明，不能覆盖执行行为')
            ignored.append({'parameter': f'{section}.{key}', 'reason': 'descriptive metadata; not executable'})
            return
        if key == 'resample_rule':
            match = re.fullmatch(r'(\d+(?:\.\d+)?)(s|min|h)', str(value))
            if not match:
                raise PolicyError('resample_rule 只支持正数秒、分钟或小时')
            value = float(match[1]) * {'s': 1, 'min': 60, 'h': 3600}[match[2]]
            key = 'resample_seconds'
        if key != 'resample_seconds' and (key not in KEY_SECTIONS or section and KEY_SECTIONS[key] != section):
            raise PolicyError(f'未知或不可覆盖参数：{original}', [{'parameter': original, 'reason': 'unsupported or immutable'}])
        if key in flat and flat[key] != value:
            raise PolicyError(f'参数冲突：{original} 与 {key}')
        flat[key] = deepcopy(value)
    for key, value in values.items():
        if key in DEFAULTS:
            if not isinstance(value, dict):
                raise PolicyError(f'{key} 必须为对象')
            for name, item in value.items():
                put(name, item, key)
        else:
            put(key, value)
    return flat, ignored


def _validate(policy):
    s, d, o = (policy[k] for k in DEFAULTS)
    for key in ('window_samples', 'step_samples', 'min_valid_samples', 'minimum_output_observations', 'modeling_top_k'):
        s[key] = _number(s[key], key, 15 if key in {'window_samples', 'min_valid_samples'} else 1, 100000, True)
    if s['step_samples'] > s['window_samples'] or s['minimum_output_observations'] > s['window_samples']:
        raise PolicyError('step_samples / minimum_output_observations 不得超过 window_samples')
    for key in ('strict_score', 'usable_score'):
        s[key] = _number(s[key], key, 0, 100)
    if s['usable_score'] > s['strict_score']:
        raise PolicyError('usable_score 不得高于 strict_score')
    s['snr_db'] = _number(s['snr_db'], 'snr_db', -200, 200)
    for key in ('allow_usable_fallback', 'sparse_output'):
        if not isinstance(s[key], bool):
            raise PolicyError(f'{key} 必须为 boolean')
    for section, key in (('selection', 'score_weights'), ('selection', 'score_scales'), ('optimization', 'objective_weights')):
        values = policy[section][key]
        if not isinstance(values, dict) or set(values) != set(DEFAULTS[section][key]):
            raise PolicyError(f'{key} 包含未知项或缺少必要项')
        for name in values:
            values[name] = _number(values[name], f'{key}.{name}', .000001 if key == 'score_scales' else 0, 1e9 if key == 'score_scales' else 1)
        if key != 'score_scales' and not math.isclose(sum(values.values()), 1., abs_tol=1e-9):
            raise PolicyError(f'{key} 权重之和必须为 1')
    for key, low, high in (('max_lag_samples', 1, 600), ('max_features', 0, 10000)):
        d[key] = _number(d[key], key, low, high, True)
    for key, low, high in (('correlation_threshold', .000001, 1), ('vif_threshold', 1, 1e6)):
        d[key] = _number(d[key], key, low, high)
    for key, low, high in (('orders', 1, 3), ('ridge_alphas', 0, 1e9)):
        if not isinstance(d[key], list) or not d[key]:
            raise PolicyError(f'{key} 必须为非空列表')
        d[key] = sorted(set(_number(v, key, low, high, key == 'orders') for v in d[key]))
    if not isinstance(d['model_families'], list) or not d['model_families'] or any(not isinstance(v, str) or v.upper() not in {'ARX', 'AR', 'FIRX'} for v in d['model_families']):
        raise PolicyError('model_families 仅支持 ARX / AR / FIRX')
    d['model_families'] = sorted(set(v.upper() for v in d['model_families']))
    if 'FIRX' in d['model_families'] and len(d['model_families']) > 1:
        raise PolicyError('FIRX 和自回归族的验证目标条件不同，不能混合比较')
    for name in ('bounds', 'constraints', 'search_space'):
        if not isinstance(o[name], dict):
            raise PolicyError(f'optimization.{name} 必须为对象')
    if set(o['constraints']) - {'min_r2', 'min_coverage'}:
        raise PolicyError('未知 optimization.constraints')
    for key, value in o['constraints'].items():
        o['constraints'][key] = _number(value, key, -1e9 if key == 'min_r2' else 0, 1)
    for key, limits in o['bounds'].items():
        if key not in {'top_k', 'max_lag'} or not isinstance(limits, dict) or set(limits) != {'min', 'max'}:
            raise PolicyError('bounds 仅支持 top_k / max_lag 的 min / max')
        for bound in limits:
            limits[bound] = _number(limits[bound], key, 1, 600 if key == 'max_lag' else 100000, True)
        if limits['min'] > limits['max']:
            raise PolicyError('bounds min > max')
    if o['search_space']:
        raise PolicyError('search_space 尚未实现；请使用 candidates 和 bounds')
    if not isinstance(o['candidates'], list):
        raise PolicyError('candidates 必须为列表')
    for row in o['candidates']:
        if not isinstance(row, dict) or set(row) - {'round', 'top_k', 'max_lag', 'label'} or not {'round', 'top_k', 'max_lag'} <= set(row):
            raise PolicyError('候选必须指定 round / top_k / max_lag，无未知字段')
        for key in ('round', 'top_k', 'max_lag'):
            row[key] = _number(row[key], key, 1, 600 if key == 'max_lag' else 100000, True)
            limits = o['bounds'].get(key)
            if limits and not limits['min'] <= row[key] <= limits['max']:
                raise PolicyError(f'候选 {key} 超出 bounds')
    policy['resample_seconds'] = _number(policy['resample_seconds'], 'resample_seconds', .001, 86400 * 30)


def resolve_algorithm_policy(scene=None, requested=None):
    scene, requested = scene or {}, requested or {}
    profile = scene.get('algorithm_profile') or scene.get('metadata', {}).get('algorithm_profile') or {}
    policy = deepcopy(DEFAULTS)
    cadence = scene.get('sampling_seconds') or scene.get('sampling_interval')
    policy['resample_seconds'] = cadence or 10
    sources = {f'{section}.{key}': 'algorithm_default' for section, values in DEFAULTS.items() for key in values}
    sources['resample_seconds'] = 'scene' if cadence else 'algorithm_default'
    ignored = []
    legacy = {k: v for k, v in scene.get('default_parameters', {}).items() if k in KEY_SECTIONS or k in ALIASES or k == 'resample_seconds'}
    for source, values in [('scene_default', legacy), ('scene', {k: v for k, v in profile.items() if k in DEFAULTS}), ('request', requested)]:
        normalized, notes = _normalize(values, scene=source != 'request')
        ignored.extend(notes)
        for key, value in normalized.items():
            section = KEY_SECTIONS.get(key)
            if section:
                if isinstance(value, dict) and key in {'score_weights', 'score_scales', 'objective_weights'}:
                    policy[section][key].update(value)
                else:
                    policy[section][key] = value
                sources[f'{section}.{key}'] = source
            else:
                policy[key] = value
                sources[key] = source
    _validate(policy)
    behavior = deepcopy(policy)
    for row in behavior['optimization']['candidates']:
        row.pop('label', None)
    digest = hashlib.sha256(json.dumps(behavior, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'requested_parameters': deepcopy(requested), 'scene_parameters': deepcopy(profile),
            'effective_parameters': policy, 'parameter_sources': sources,
            'ignored_or_rejected_parameters': ignored, 'profile_version': profile.get('version'), 'effective_policy_hash': digest}


def snapshot_policy(snapshot, requested=None):
    from core.skills.context import build_scene_context
    return resolve_algorithm_policy(build_scene_context(snapshot).public(), requested)


def parameter_view(receipt):
    policy = receipt['effective_parameters']
    values = {key: value for section in DEFAULTS for key, value in policy[section].items()}
    values.update({alias: values[key] for alias, key in ALIASES.items()})
    values.update(resample_seconds=policy['resample_seconds'], resample_rule=f"{policy['resample_seconds']:g}s")
    return values
