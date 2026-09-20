"""Bounded candidate projection and deterministic, finite de-duplication."""
def bounded_candidate(candidate, bounds, seen):
    limits = {key: (int((bounds or {}).get(key, {}).get('min', low)), int((bounds or {}).get(key, {}).get('max', high)))
              for key, low, high in [('top_k', 2, 20), ('max_lag', 1, 600)]}
    requested = {key: int(candidate[key]) for key in limits}
    projected = {key: max(low, min(high, requested[key])) for key, (low, high) in limits.items()}
    k_low, k_high = limits['top_k']; lag_low, lag_high = limits['max_lag']
    width = lag_high - lag_low + 1
    capacity = (k_high - k_low + 1) * width
    start = (projected['top_k'] - k_low) * width + projected['max_lag'] - lag_low
    for offset in range(min(capacity, len(seen) + 1)):
        index = (start + offset) % capacity
        pair = (k_low + index // width, lag_low + index % width)
        if pair in seen:
            continue
        effective = dict(zip(('top_k', 'max_lag'), pair))
        return {**candidate, **effective, 'proposed_parameters': requested,
                'candidate_projection': {'requested': requested, 'effective': effective,
                    'reason': 'bounds_projection_or_duplicate_avoidance' if effective != requested else 'within_bounds'}}
    return None
