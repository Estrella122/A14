"""Deterministic closed-loop preprocessing search with a lightweight ARX evaluator.

The service intentionally uses only Python's standard library so the local demo can
run without a scientific Python stack.  Every iteration performs real preprocessing,
time-lag search, least-squares fitting and validation on a reproducible industrial
step-response benchmark.  A later CSV adapter can feed the same evaluator.
"""

from __future__ import annotations

import math
import random
import statistics
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass


DEFAULT_SEARCH_SPACE = {
    'dynamic_threshold': {'min': 0.20, 'max': 0.70, 'step': 0.01},
    'outlier_sigma': {'min': 1.50, 'max': 4.00, 'step': 0.10},
    'collinearity_threshold': {'min': 0.60, 'max': 0.95, 'step': 0.01},
    'lag_max_seconds': {'min': 60, 'max': 240, 'step': 10},
    'min_segment_minutes': {'min': 4, 'max': 20, 'step': 1},
}

DEFAULT_OBJECTIVE_WEIGHTS = {'fit': 0.70, 'coverage': 0.20, 'cost': 0.10}
DEFAULT_CONSTRAINTS = {
    'target_fit': 0.75,
    'min_coverage': 0.70,
    'max_rmse': 6.0,
    'min_valid_segments': 5,
}
DEFAULT_INITIAL_CANDIDATE = {
    'dynamic_threshold': 0.24,
    'outlier_sigma': 3.8,
    'collinearity_threshold': 0.94,
    'lag_max_seconds': 60,
    'min_segment_minutes': 4,
}


@dataclass(frozen=True)
class BenchmarkData:
    sampling_seconds: int
    gas_flow: list[float]
    air_flow: list[float]
    slab_speed: list[float]
    inlet_temperature: list[float]
    furnace_pressure: list[float]
    outlet_temperature: list[float]
    reference_outlet_temperature: list[float]
    injected_outliers: int


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _rounded_to_step(value, rule):
    minimum = float(rule['min'])
    maximum = float(rule['max'])
    step = float(rule['step'])
    value = clamp(float(value), minimum, maximum)
    stepped = minimum + round((value - minimum) / step) * step
    if step >= 1:
        return int(round(stepped))
    decimals = max(0, len(str(step).split('.')[-1].rstrip('0')))
    return round(stepped, decimals)


def normalize_search_space(search_space=None):
    result = {}
    supplied = search_space or {}
    if not isinstance(supplied, Mapping):
        raise ValueError('search_space 必须是 JSON 对象')
    for key, defaults in DEFAULT_SEARCH_SPACE.items():
        candidate = supplied.get(key, {})
        if not isinstance(candidate, Mapping):
            raise ValueError(f'{key} 的搜索范围必须是 JSON 对象')
        minimum = float(candidate.get('min', defaults['min']))
        maximum = float(candidate.get('max', defaults['max']))
        step = float(candidate.get('step', defaults['step']))
        if not math.isfinite(minimum) or not math.isfinite(maximum) or not math.isfinite(step):
            raise ValueError(f'{key} 的搜索范围必须是有限数字')
        if minimum >= maximum or step <= 0:
            raise ValueError(f'{key} 的搜索范围无效')
        result[key] = {'min': minimum, 'max': maximum, 'step': step}
    return result


def normalize_candidate(candidate=None, search_space=None):
    search_space = normalize_search_space(search_space)
    if candidate is not None and not isinstance(candidate, Mapping):
        raise ValueError('initial_candidate 必须是 JSON 对象')
    supplied = {**DEFAULT_INITIAL_CANDIDATE, **(candidate or {})}
    result = {}
    for key, rule in search_space.items():
        try:
            result[key] = _rounded_to_step(supplied[key], rule)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'{key} 不是合法候选参数') from exc
    return result


def normalize_weights(weights=None):
    if weights is not None and not isinstance(weights, Mapping):
        raise ValueError('objective_weights 必须是 JSON 对象')
    supplied = {**DEFAULT_OBJECTIVE_WEIGHTS, **(weights or {})}
    result = {}
    for key in DEFAULT_OBJECTIVE_WEIGHTS:
        value = float(supplied[key])
        if not math.isfinite(value) or value < 0:
            raise ValueError('目标权重必须是非负有限数字')
        result[key] = value
    if sum(result.values()) <= 0:
        raise ValueError('目标权重之和必须大于 0')
    return result


def normalize_constraints(constraints=None):
    if constraints is not None and not isinstance(constraints, Mapping):
        raise ValueError('constraints 必须是 JSON 对象')
    result = {**DEFAULT_CONSTRAINTS, **(constraints or {})}
    target_fit = float(result['target_fit'])
    min_coverage = float(result['min_coverage'])
    max_rmse = float(result['max_rmse'])
    min_valid_segments = int(result['min_valid_segments'])
    if not all(math.isfinite(value) for value in (target_fit, min_coverage, max_rmse)):
        raise ValueError('硬约束必须是有限数字')
    if not 0.0 <= target_fit <= 1.0:
        raise ValueError('target_fit 必须在 0 到 1 之间')
    if not 0.0 <= min_coverage <= 1.0:
        raise ValueError('min_coverage 必须在 0 到 1 之间')
    if max_rmse <= 0:
        raise ValueError('max_rmse 必须大于 0')
    if min_valid_segments < 1:
        raise ValueError('min_valid_segments 必须大于等于 1')
    result['target_fit'] = target_fit
    result['min_coverage'] = min_coverage
    result['max_rmse'] = max_rmse
    result['min_valid_segments'] = min_valid_segments
    return result


def benchmark_snapshot_id(project_code, seed):
    """Return a traceable ID for the exact deterministic benchmark input."""
    fingerprint = hashlib.sha256(f'{project_code}:{seed}:benchmark-v3'.encode('utf-8')).hexdigest()[:12]
    return f'FURNACE-BENCH-v3@{fingerprint}-seed-{seed}'


def generate_benchmark(project_code, seed, sample_count=840):
    """Create a reproducible furnace benchmark with lag, drift and sensor faults."""
    rng = random.Random(f'{project_code}:{seed}:benchmark-v3')
    gas_flow = []
    air_flow = []
    slab_speed = []
    inlet_temperature = []
    furnace_pressure = []
    outlet_temperature = []

    gas_level = 51.5
    speed_level = 1.08
    gas_steps = {52: 4.8, 138: -3.5, 226: 5.6, 318: -4.2, 408: 3.9, 500: -5.0, 592: 4.4, 686: -3.2, 776: 3.6}
    speed_steps = {96: 0.08, 184: -0.11, 274: 0.07, 364: -0.06, 454: 0.09, 546: -0.08, 638: 0.06, 730: -0.05}
    last_step_index = -10_000

    for index in range(sample_count):
        gas_level += gas_steps.get(index, 0.0)
        speed_level += speed_steps.get(index, 0.0)
        if index in gas_steps or index in speed_steps:
            last_step_index = index
        gas = gas_level + 0.45 * math.sin(index / 17.0) + rng.gauss(0, 0.10)
        # Air follows gas closely but retains an independent oscillatory component,
        # making collinearity handling useful rather than mathematically neutral.
        air = 0.82 * gas + 2.6 + 1.45 * math.sin(index / 31.0 + 0.7) + rng.gauss(0, 0.18)
        speed = speed_level + 0.018 * math.sin(index / 23.0) + rng.gauss(0, 0.004)
        inlet = 862.0 + 5.5 * math.sin(index / 88.0) + rng.gauss(0, 0.35)
        pressure = 0.16 * (air - 44.0) - 0.10 * (gas - 52.0) + rng.gauss(0, 0.08)
        gas_flow.append(gas)
        air_flow.append(air)
        slab_speed.append(speed)
        inlet_temperature.append(inlet)
        furnace_pressure.append(pressure)

        gas_lagged = gas_flow[max(0, index - 11)]
        air_lagged = air_flow[max(0, index - 7)]
        speed_lagged = slab_speed[max(0, index - 3)]
        regime_gain = 1.0 if index < sample_count * 0.58 else 0.91
        unmeasured_heat_loss = 1.8 * math.sin(index / 57.0) + 0.7 * math.sin(index / 19.0)
        equilibrium = (
            1085.0
            + regime_gain * 1.48 * (gas_lagged - 52.0)
            + 0.78 * (air_lagged - 45.0)
            - 19.5 * (speed_lagged - 1.08)
            + 0.12 * (inlet - 862.0)
            - 1.8 * pressure
            + 0.035 * (gas_lagged - 52.0) ** 2
            + unmeasured_heat_loss
        )
        previous = outlet_temperature[-1] if outlet_temperature else 1082.0
        samples_since_step = index - last_step_index
        noise_sigma = 0.36 if 0 <= samples_since_step <= 68 else 0.78
        outlet_temperature.append(0.895 * previous + 0.105 * equilibrium + rng.gauss(0, noise_sigma))

    reference_outlet_temperature = list(outlet_temperature)
    outlier_indexes = [116, 247, 333, 419, 587, 681, 742, 809]
    for position, index in enumerate(outlier_indexes):
        outlet_temperature[index] += 25.0 if position % 2 == 0 else -22.0
        if position % 3 == 0:
            gas_flow[index] += 8.5

    # Moderate faults sit close to a loose Hampel threshold.  A balanced sigma
    # removes them, while an overly loose or overly strict setting hurts fit.
    soft_fault_indexes = [171, 286, 371, 476, 535, 654, 715, 788]
    for position, index in enumerate(soft_fault_indexes):
        outlet_temperature[index] += 3.2 if position % 2 == 0 else -3.0
        if position % 3 == 1:
            air_flow[index] += 2.4

    return BenchmarkData(
        sampling_seconds=10,
        gas_flow=gas_flow,
        air_flow=air_flow,
        slab_speed=slab_speed,
        inlet_temperature=inlet_temperature,
        furnace_pressure=furnace_pressure,
        outlet_temperature=outlet_temperature,
        reference_outlet_temperature=reference_outlet_temperature,
        injected_outliers=len(outlier_indexes) + len(soft_fault_indexes),
    )


def _robust_clip(values, sigma):
    filtered = list(values)
    replaced_indexes = []
    radius = 6
    for index, value in enumerate(values):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        window = values[start:end]
        median = statistics.median(window)
        deviations = [abs(item - median) for item in window]
        mad = statistics.median(deviations)
        robust_scale = 1.4826 * mad
        if robust_scale <= 1e-9:
            continue
        if abs(value - median) > sigma * robust_scale:
            filtered[index] = median
            replaced_indexes.append(index)
    return filtered, replaced_indexes


def _standardized_changes(values):
    spread = statistics.pstdev(values) or 1.0
    return [0.0] + [abs(values[index] - values[index - 1]) / spread for index in range(1, len(values))]


def _dynamic_mask(data, threshold, min_segment_minutes):
    gas_change = _standardized_changes(data.gas_flow)
    air_change = _standardized_changes(data.air_flow)
    speed_change = _standardized_changes(data.slab_speed)
    energy = [0.55 * gas + 0.25 * air + 0.20 * speed for gas, air, speed in zip(gas_change, air_change, speed_change)]
    events = []
    cooldown = 12
    for index, value in enumerate(energy):
        if value < threshold:
            continue
        if events and index - events[-1] < cooldown:
            if value > energy[events[-1]]:
                events[-1] = index
            continue
        events.append(index)

    if not events:
        events = sorted(range(len(energy)), key=energy.__getitem__, reverse=True)[:6]
        events.sort()

    minimum_steps = max(4, round(min_segment_minutes * 60 / data.sampling_seconds))
    before_steps = max(4, minimum_steps // 5)
    after_steps = max(12, round(minimum_steps * 1.15))
    mask = [False] * len(energy)
    for event in events:
        start = max(0, event - before_steps)
        end = min(len(mask), event + after_steps)
        for index in range(start, end):
            mask[index] = True

    segment_count = 0
    inside = False
    for selected in mask:
        if selected and not inside:
            segment_count += 1
        inside = selected
    return mask, energy, segment_count, events


def _correlation(left, right):
    if len(left) < 2:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_sum = sum((x - left_mean) ** 2 for x in left)
    right_sum = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_sum * right_sum)
    return numerator / denominator if denominator else 0.0


def _solve_linear_system(matrix, vector):
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            augmented[pivot][column] = 1e-10
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def _fit_regression(train_rows, train_targets):
    feature_count = len(train_rows[0])
    means = [statistics.fmean(row[index] for row in train_rows) for index in range(feature_count)]
    scales = []
    for index, mean in enumerate(means):
        variance = statistics.fmean((row[index] - mean) ** 2 for row in train_rows)
        scales.append(math.sqrt(variance) or 1.0)
    target_mean = statistics.fmean(train_targets)
    target_scale = math.sqrt(statistics.fmean((target - target_mean) ** 2 for target in train_targets)) or 1.0
    normalized_rows = [
        [(value - means[index]) / scales[index] for index, value in enumerate(row)]
        for row in train_rows
    ]
    normalized_targets = [(target - target_mean) / target_scale for target in train_targets]
    matrix = [[0.0] * feature_count for _ in range(feature_count)]
    vector = [0.0] * feature_count
    for row, target in zip(normalized_rows, normalized_targets):
        for left in range(feature_count):
            vector[left] += row[left] * target
            for right in range(feature_count):
                matrix[left][right] += row[left] * row[right]
    for index in range(feature_count):
        matrix[index][index] += 0.004
    coefficients = _solve_linear_system(matrix, vector)

    def predict(row):
        normalized = [(value - means[index]) / scales[index] for index, value in enumerate(row)]
        return target_mean + target_scale * sum(value * coefficient for value, coefficient in zip(normalized, coefficients))

    return predict


def _metrics(actual, predicted):
    mean = statistics.fmean(actual)
    squared_error = sum((value - estimate) ** 2 for value, estimate in zip(actual, predicted))
    total_variance = sum((value - mean) ** 2 for value in actual) or 1.0
    rmse = math.sqrt(squared_error / len(actual))
    r2 = 1.0 - squared_error / total_variance
    fit = 1.0 - math.sqrt(squared_error) / math.sqrt(total_variance)
    return clamp(r2, -1.0, 1.0), clamp(fit, 0.0, 1.0), rmse


def _build_rows(data, mask, lag, collinearity_threshold):
    indexes = [index for index in range(max(lag, 2), len(mask)) if mask[index]]
    gas_values = [data.gas_flow[index - lag] for index in indexes]
    air_values = [data.air_flow[max(0, index - max(1, lag - 4))] for index in indexes]
    input_correlation = abs(_correlation(gas_values, air_values))
    decorrelate = input_correlation >= collinearity_threshold
    rows = []
    targets = []
    for index, gas_value, air_value in zip(indexes, gas_values, air_values):
        if decorrelate:
            # Merge strongly collinear fuel/air signals into a lower-dimensional
            # combustion-load feature.  This improves stability but can lose some
            # independent air information, creating a real threshold trade-off.
            features = [
                data.outlet_temperature[index - 1],
                0.58 * gas_value + 0.42 * air_value,
                data.slab_speed[max(0, index - 3)],
                data.inlet_temperature[index],
                data.furnace_pressure[index],
            ]
        else:
            features = [
                data.outlet_temperature[index - 1],
                gas_value,
                air_value,
                data.slab_speed[max(0, index - 3)],
                data.inlet_temperature[index],
                data.furnace_pressure[index],
            ]
        rows.append(features)
        targets.append(data.outlet_temperature[index])
    return indexes, rows, targets, input_correlation, decorrelate


def _free_run_predictions(indexes, rows, predict, horizon=18):
    predictions = []
    previous_index = None
    previous_prediction = None
    steps_in_horizon = 0
    for index, row in zip(indexes, rows):
        simulation_row = list(row)
        is_continuous = previous_index is not None and index == previous_index + 1
        if is_continuous and steps_in_horizon < horizon:
            simulation_row[0] = previous_prediction
            steps_in_horizon += 1
        else:
            steps_in_horizon = 0
        prediction = predict(simulation_row)
        predictions.append(prediction)
        previous_index = index
        previous_prediction = prediction
    return predictions


def _segment_aware_split(indexes, fraction=0.72):
    if len(indexes) < 45:
        return max(30, len(indexes) - 15)
    boundaries = [position for position in range(1, len(indexes)) if indexes[position] != indexes[position - 1] + 1]
    target = round(len(indexes) * fraction)
    valid_boundaries = [position for position in boundaries if 30 <= position <= len(indexes) - 15]
    if not valid_boundaries:
        return max(30, min(len(indexes) - 15, target))
    return min(valid_boundaries, key=lambda position: abs(position - target))


def evaluate_candidate(project_code, seed, candidate, weights=None, constraints=None, search_space=None):
    weights = normalize_weights(weights)
    constraints = normalize_constraints(constraints)
    candidate = normalize_candidate(candidate, search_space)
    raw_data = generate_benchmark(project_code, seed)
    clipped_output, output_clip_indexes = _robust_clip(raw_data.outlet_temperature, candidate['outlier_sigma'])
    clipped_gas, gas_clip_indexes = _robust_clip(raw_data.gas_flow, candidate['outlier_sigma'])
    data = BenchmarkData(
        sampling_seconds=raw_data.sampling_seconds,
        gas_flow=clipped_gas,
        air_flow=raw_data.air_flow,
        slab_speed=raw_data.slab_speed,
        inlet_temperature=raw_data.inlet_temperature,
        furnace_pressure=raw_data.furnace_pressure,
        outlet_temperature=clipped_output,
        reference_outlet_temperature=raw_data.reference_outlet_temperature,
        injected_outliers=raw_data.injected_outliers,
    )
    mask, _, valid_segments, event_indexes = _dynamic_mask(
        data,
        candidate['dynamic_threshold'],
        candidate['min_segment_minutes'],
    )
    eligible_count = max(1, len(mask) - 2)
    coverage = sum(mask[2:]) / eligible_count
    max_lag_steps = max(1, round(candidate['lag_max_seconds'] / data.sampling_seconds))
    best_evaluation = None

    for lag in range(1, max_lag_steps + 1):
        indexes, rows, targets, correlation, decorrelate = _build_rows(
            data,
            mask,
            lag,
            candidate['collinearity_threshold'],
        )
        if len(rows) < 50:
            continue
        split = _segment_aware_split(indexes)
        predict = _fit_regression(rows[:split], targets[:split])
        validation_actual = [data.reference_outlet_temperature[index] for index in indexes[split:]]
        validation_predicted = _free_run_predictions(indexes[split:], rows[split:], predict)
        r2, fit, rmse = _metrics(validation_actual, validation_predicted)
        train_one_step = [predict(row) for row in rows[:split]]
        _, train_one_step_fit, _ = _metrics(targets[:split], train_one_step)
        train_free_run = _free_run_predictions(indexes[:split], rows[:split], predict)
        _, train_fit, _ = _metrics(targets[:split], train_free_run)
        selection_score = 0.35 * train_one_step_fit + 0.65 * train_fit
        evaluation = {
            'lag_steps': lag,
            'lag_seconds': lag * data.sampling_seconds,
            'r2': r2,
            'fit': fit,
            'rmse': rmse,
            'train_fit': train_fit,
            'train_one_step_fit': train_one_step_fit,
            'selection_score': selection_score,
            'sample_count': len(rows),
            'validation_count': len(validation_actual),
            'feature_count': len(rows[0]),
            'input_correlation': correlation,
            'decorrelated': decorrelate,
        }
        if best_evaluation is None or evaluation['selection_score'] > best_evaluation['selection_score']:
            best_evaluation = evaluation

    if best_evaluation is None:
        raise ValueError('动态数据覆盖不足，无法完成 ARX 训练验证')

    clipped_total = len(output_clip_indexes) + len(gas_clip_indexes)
    cost = clamp(
        0.40 * candidate['lag_max_seconds'] / 240
        + 0.25 * coverage
        + 0.20 * min(1.0, clipped_total / max(1, raw_data.injected_outliers * 2))
        + 0.15 * best_evaluation['feature_count'] / 6,
        0.0,
        1.0,
    )
    weighted_total = weights['fit'] + weights['coverage'] + weights['cost']
    objective = (
        weights['fit'] * best_evaluation['fit']
        + weights['coverage'] * coverage
        - weights['cost'] * cost
    ) / weighted_total
    overall_score = 100 * clamp(objective, 0.0, 1.0)

    failures = []
    if best_evaluation['fit'] < constraints['target_fit']:
        failures.append('拟合度未达目标')
    if coverage < constraints['min_coverage']:
        failures.append('动态覆盖不足')
    if best_evaluation['rmse'] > constraints['max_rmse']:
        failures.append('RMSE 超限')
    if valid_segments < constraints['min_valid_segments']:
        failures.append('有效片段不足')

    selected_mask = ''.join('1' if selected else '0' for selected in mask)
    signature_payload = '|'.join([
        selected_mask,
        ','.join(map(str, output_clip_indexes)),
        ','.join(map(str, gas_clip_indexes)),
        str(best_evaluation['lag_seconds']),
        str(best_evaluation['feature_count']),
    ])
    effective_signature = hashlib.sha1(signature_payload.encode('utf-8')).hexdigest()[:12]
    constraint_checks = {
        'fit': {
            'passed': best_evaluation['fit'] >= constraints['target_fit'],
            'actual': round(best_evaluation['fit'], 4),
            'target': constraints['target_fit'],
        },
        'coverage': {
            'passed': coverage >= constraints['min_coverage'],
            'actual': round(coverage, 4),
            'target': constraints['min_coverage'],
        },
        'rmse': {
            'passed': best_evaluation['rmse'] <= constraints['max_rmse'],
            'actual': round(best_evaluation['rmse'], 4),
            'target': constraints['max_rmse'],
        },
        'segments': {
            'passed': valid_segments >= constraints['min_valid_segments'],
            'actual': valid_segments,
            'target': constraints['min_valid_segments'],
        },
    }

    return {
        'params': candidate,
        'metrics': {
            'fit': round(best_evaluation['fit'], 4),
            'r2': round(best_evaluation['r2'], 4),
            'rmse': round(best_evaluation['rmse'], 4),
            'coverage': round(coverage, 4),
            'cost': round(cost, 4),
            'overall_score': round(overall_score, 4),
        },
        'score_components': {
            'fit_contribution': round(weights['fit'] * best_evaluation['fit'] / weighted_total * 100, 4),
            'coverage_contribution': round(weights['coverage'] * coverage / weighted_total * 100, 4),
            'cost_penalty': round(weights['cost'] * cost / weighted_total * 100, 4),
        },
        'diagnostics': {
            'evaluator': 'ARX(1,1) · 分段时序留出 · 18 步自由运行',
            'sampling_seconds': data.sampling_seconds,
            'optimal_lag_seconds': best_evaluation['lag_seconds'],
            'lag_boundary_hit': best_evaluation['lag_seconds'] >= candidate['lag_max_seconds'] - data.sampling_seconds,
            'valid_segments': valid_segments,
            'detected_events': len(event_indexes),
            'selected_samples': best_evaluation['sample_count'],
            'validation_samples': best_evaluation['validation_count'],
            'input_correlation': round(best_evaluation['input_correlation'], 4),
            'decorrelated': best_evaluation['decorrelated'],
            'feature_count': best_evaluation['feature_count'],
            'clipped_points': clipped_total,
            'injected_outliers': raw_data.injected_outliers,
            'train_free_run_fit': round(best_evaluation['train_fit'], 4),
            'train_one_step_fit': round(best_evaluation['train_one_step_fit'], 4),
            'generalization_gap': round(best_evaluation['train_fit'] - best_evaluation['fit'], 4),
            'effective_signature': effective_signature,
        },
        'constraint_checks': constraint_checks,
        'constraint_failures': failures,
    }


def suggest_candidate(study, round_number, attempt=0):
    search_space = study.search_space or DEFAULT_SEARCH_SPACE
    if round_number == 1 or not study.best_run_id:
        return normalize_candidate(study.initial_candidate, search_space)

    # Six rounds form a deterministic space-filling warm-up.  Every dimension
    # reaches low/mid/high regions before feedback-based local search is allowed
    # to converge, preventing premature stopping around the initial candidate.
    warmup_design = {
        2: {'dynamic_threshold': 0.34, 'outlier_sigma': 3.2, 'collinearity_threshold': 0.90, 'lag_max_seconds': 100, 'min_segment_minutes': 6},
        3: {'dynamic_threshold': 0.42, 'outlier_sigma': 2.6, 'collinearity_threshold': 0.84, 'lag_max_seconds': 140, 'min_segment_minutes': 8},
        4: {'dynamic_threshold': 0.50, 'outlier_sigma': 2.4, 'collinearity_threshold': 0.90, 'lag_max_seconds': 150, 'min_segment_minutes': 7},
        5: {'dynamic_threshold': 0.30, 'outlier_sigma': 2.0, 'collinearity_threshold': 0.72, 'lag_max_seconds': 200, 'min_segment_minutes': 10},
        6: {'dynamic_threshold': 0.60, 'outlier_sigma': 3.1, 'collinearity_threshold': 0.65, 'lag_max_seconds': 120, 'min_segment_minutes': 6},
    }
    if round_number in warmup_design and attempt == 0:
        return normalize_candidate(warmup_design[round_number], search_space)

    best_payload = study.best_run.candidate_parameters or {}
    candidate = normalize_candidate(best_payload.get('params'), search_space)
    best_metrics = best_payload.get('metrics', {})
    diagnostics = best_payload.get('diagnostics', {})
    constraints = normalize_constraints(study.constraints)
    rng = random.Random(study.random_seed + round_number * 7919 + attempt * 104729)
    radius = max(0.12, 0.46 - 0.045 * round_number)

    if float(best_metrics.get('coverage', 0)) < constraints['min_coverage']:
        candidate['dynamic_threshold'] -= 0.05
        candidate['min_segment_minutes'] += 2
    else:
        candidate['dynamic_threshold'] += rng.uniform(-0.08, 0.08) * radius
        candidate['min_segment_minutes'] += rng.choice([-2, -1, 1, 2])

    if float(best_metrics.get('rmse', 999)) > constraints['max_rmse']:
        candidate['outlier_sigma'] -= 0.3
    else:
        candidate['outlier_sigma'] += rng.uniform(-0.35, 0.35) * radius

    if float(best_metrics.get('fit', 0)) < constraints['target_fit'] or int(diagnostics.get('optimal_lag_seconds', 0)) >= candidate['lag_max_seconds'] - 10:
        candidate['lag_max_seconds'] += 30
    else:
        candidate['lag_max_seconds'] += rng.choice([-20, -10, 10, 20])

    correlation = float(diagnostics.get('input_correlation', 0))
    if correlation > candidate['collinearity_threshold']:
        candidate['collinearity_threshold'] -= 0.04
    else:
        candidate['collinearity_threshold'] += rng.uniform(-0.05, 0.05) * radius

    # Every fourth round probes a wider neighbourhood to avoid a local optimum.
    if round_number % 4 == 0:
        candidate['dynamic_threshold'] += rng.choice([-0.07, 0.07])
        candidate['outlier_sigma'] += rng.choice([-0.25, 0.25])

    if attempt:
        candidate['dynamic_threshold'] += rng.uniform(-0.11, 0.11)
        candidate['outlier_sigma'] += rng.uniform(-0.45, 0.45)
        candidate['collinearity_threshold'] += rng.uniform(-0.07, 0.07)
        candidate['lag_max_seconds'] += rng.choice([-30, -20, 20, 30])
        candidate['min_segment_minutes'] += rng.choice([-3, -2, 2, 3])

    return normalize_candidate(candidate, search_space)
