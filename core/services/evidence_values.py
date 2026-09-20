"""Finite observations and explicit absence, shared by answers and reports."""
from math import isfinite
from copy import deepcopy


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (ValueError, TypeError):
        return None


def display(value, digits=3):
    result = number(value)
    return f'{result:.{digits}f}' if result is not None else '未计算/指标不可定义'


def relative_improvement(actual, baseline):
    actual, baseline = number(actual), number(baseline)
    return 100 * (1 - actual / baseline) if actual is not None and baseline is not None and baseline > 0 else None


def clean_facts(value):
    if isinstance(value, float):
        return number(value)
    if isinstance(value, dict):
        return {k: clean_facts(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_facts(v) for v in value]
    return value


def final_result_view(snapshot):
    """Project the recorded winner without modifying baseline evidence."""
    snapshot = clean_facts(deepcopy(snapshot))
    result = snapshot.get('results', {})
    for row in result.get('optimization', {}).get('iterations', []):
        missing = [key for key in ('round_id', 'candidate_source', 'effective_policy_hash', 'target_observations', 'duration_seconds', 'fitted_inputs') if key not in row]
        if missing:
            if row.get('round_id') and row.get('status') in {'infeasible', 'failed'}:
                row['audit_status'] = 'not_computed'
                row['unavailable_fields'] = {key: row.get('rejection_reason') or row['status'] for key in missing}
            else:
                row['audit_status'] = 'historical_not_recorded'
                row['historical_not_recorded'] = missing
    winner = result.get('best_selection_receipt')
    if winner:
        cleaning = result.setdefault('cleaning', {})
        chosen = set(winner['selected_window_ids'])
        previews = cleaning.get('segments_preview', [])
        windows = {str(row.get('window_id', index)): row for index, row in enumerate(previews)}
        for row in winner.get('selected_windows', []):
            windows[row['window_id']] = row
        cleaning['segments_preview'] = [dict(row, window_id=key, selected=key in chosen) for key, row in windows.items()]
        cleaning['selection_view'] = 'frozen_winner'
        cleaning['selection_metrics'] = {
            **cleaning.get('selection_metrics', {}),
            'selected_row_count': winner['selected_row_count'],
            'target_observation_count': winner['actual_target_observation_count'],
            'actual_selected_window_count': len(winner['selected_window_ids']),
            'effective_top_k': winner['requested_parameters'].get('top_k'),
            'source': 'best_selection_receipt',
        }
        cleaning['modeling_row_count'] = winner['selected_row_count']
        cleaning['strict_selected_segment_count'] = winner.get('strict_window_count')
        cleaning['usable_segment_count'] = winner.get('usable_window_count')
        cleaning['selected_segment_count'] = len(winner['selected_window_ids'])
        cleaning['selection_metrics']['strict_selected_count'] = winner.get('strict_window_count')
        cleaning['selection_metrics']['usable_count'] = winner.get('usable_window_count')
        result.setdefault('selection', {})['modeling_row_count'] = winner['selected_row_count']
    return snapshot
