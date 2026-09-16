"""Causal, segment-aware identification with frozen chronological holdouts.

Only candidate training data determines delays, variable selection and coefficients.
Orders/candidates use a common validation target set. Test is evaluated once after
selection from the persisted fitted state; it never participates in selection.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from collinearity import correlation_matrix, compute_vif, recommend_variables, highly_correlated_pairs
from system_identification import regression_metrics, residual_autocorrelation


def save_json(path, data):
    def clean(x):
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)): return [clean(v) for v in x]
        if isinstance(x, (float, np.floating)): return float(x) if np.isfinite(x) else None
        if isinstance(x, np.integer): return int(x)
        return x
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(clean(data), ensure_ascii=False, indent=2), encoding='utf-8')


def groups(df, seconds):
    t = pd.to_datetime(df.timestamp)
    return t.diff().dt.total_seconds().ne(seconds).cumsum()


def shifted(df, col, lag, seconds):
    if lag < 0: raise ValueError('Negative predictive lags are forbidden')
    return df[col].groupby(groups(df, seconds)).shift(lag)


def features(df, output, inputs, delays, order, seconds):
    x = pd.DataFrame(index=df.index)
    for lag in range(1, order + 1):
        x[f'{output}_lag{lag}'] = shifted(df, output, lag, seconds)
    for col in inputs:
        for lag in range(order):
            # At least one historical sample; delay 0 never means future input.
            total_lag = max(1, delays[col]) + lag
            x[f'{col}_aligned_lag{lag+1}'] = shifted(df, col, total_lag, seconds)
    return x


def fit(x, y, alpha=0.0):
    valid = x.notna().all(axis=1) & y.notna()
    x, y = x.loc[valid], y.loc[valid]
    if len(x) < max(20, 2 * (x.shape[1] + 1)):
        raise ValueError('连续有效训练样本不足以辨识当前阶次')
    mean, scale = x.mean(), x.std(ddof=0).replace(0, 1)
    z = (x - mean) / scale
    matrix = z.to_numpy()
    centered_y = y.to_numpy() - float(y.mean())
    if alpha > 0:
        coef_z = np.linalg.solve(matrix.T @ matrix + float(alpha) * np.eye(matrix.shape[1]), matrix.T @ centered_y)
    else:
        coef_z, *_ = np.linalg.lstsq(matrix, centered_y, rcond=None)
    raw = coef_z / scale.to_numpy()
    raw = np.r_[float(y.mean()) - np.dot(raw, mean), raw]
    rank = np.linalg.matrix_rank(matrix)
    return raw, valid, int(rank)


def predict(x, coef):
    return np.column_stack([np.ones(len(x)), x.to_numpy()]) @ np.array(coef)


def arx_response_analysis(state, horizon=120, frequency_points=96):
    """Generate per-channel discrete responses directly from a fitted ARX state."""
    order = int(state['order'])
    seconds = float(state['seconds'])
    coefficients = np.asarray(state['coef'], dtype=float)
    ar = coefficients[1:order + 1]
    denominator = np.r_[1., -ar]
    channels = []
    for input_index, input_name in enumerate(state['inputs']):
        start = 1 + order + input_index * order
        input_coef = coefficients[start:start + order]
        delay = max(1, int(state['delays'][input_name]))
        impulse_y = np.zeros(horizon, dtype=float)
        step_y = np.zeros(horizon, dtype=float)
        for position in range(horizon):
            ar_impulse = sum(ar[lag - 1] * impulse_y[position - lag] for lag in range(1, order + 1) if position >= lag)
            ar_step = sum(ar[lag - 1] * step_y[position - lag] for lag in range(1, order + 1) if position >= lag)
            impulse_input = sum(input_coef[lag] for lag in range(order) if position == delay + lag)
            step_input = sum(input_coef[lag] for lag in range(order) if position >= delay + lag)
            impulse_y[position] = ar_impulse + impulse_input
            step_y[position] = ar_step + step_input
        frequencies = []
        for omega in np.linspace(0, np.pi, frequency_points):
            z = np.exp(-1j * omega)
            numerator = sum(input_coef[lag] * z ** (delay + lag) for lag in range(order))
            denominator_value = 1 - sum(ar[lag - 1] * z ** lag for lag in range(1, order + 1))
            response = numerator / denominator_value if abs(denominator_value) > 1e-12 else complex(np.nan, np.nan)
            finite = np.isfinite(response.real) and np.isfinite(response.imag)
            frequencies.append({
                'hz': omega / (2 * np.pi * seconds),
                'magnitude_db': 20 * np.log10(max(abs(response), 1e-12)) if finite else None,
                'phase_degrees': np.degrees(np.angle(response)) if finite else None,
            })
        dc_denominator = 1 - float(ar.sum())
        dc_gain = float(input_coef.sum() / dc_denominator) if abs(dc_denominator) > 1e-12 else None
        channels.append({
            'input': input_name, 'output': state['output'], 'delay_samples': delay,
            'delay_seconds': delay * seconds, 'dc_gain': dc_gain,
            'numerator': input_coef.tolist(), 'denominator': denominator.tolist(),
            'impulse': [{'seconds': index * seconds, 'value': value} for index, value in enumerate(impulse_y.tolist())],
            'step': [{'seconds': index * seconds, 'value': value} for index, value in enumerate(step_y.tolist())],
            'frequency': frequencies,
        })
    return {
        'method': 'discrete_arx_deviation_response', 'sample_seconds': seconds,
        'horizon_samples': horizon,
        'assumptions': '其他外部输入保持零偏差；不包含拟合截距；频率上限为奈奎斯特频率',
        'channels': channels,
    }


def estimate_training_delays(df, output, inputs, seconds, max_lag):
    """Estimate segment-safe Pearson lags without rebuilding pandas frames per lag."""
    rows = []
    group_ids = groups(df, seconds).to_numpy()
    output_values = pd.to_numeric(df[output], errors='coerce').to_numpy(dtype=float)
    for col in inputs:
        input_values = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
        candidates = []
        for lag in range(max_lag + 1):
            if lag:
                same_segment = group_ids[lag:] == group_ids[:-lag]
                x_values = input_values[:-lag][same_segment]
                y_values = output_values[lag:][same_segment]
            else:
                x_values, y_values = input_values, output_values
            finite = np.isfinite(x_values) & np.isfinite(y_values)
            x_valid, y_valid = x_values[finite], y_values[finite]
            if len(x_valid) >= 20 and np.std(x_valid, ddof=1) > 1e-12 and np.std(y_valid, ddof=1) > 1e-12:
                corr = float(np.corrcoef(x_valid, y_valid)[0, 1])
                if np.isfinite(corr): candidates.append((abs(corr), lag, corr, len(x_valid)))
        if not candidates: raise ValueError(f'{col} 无有效因果时滞证据')
        _, lag, corr, n = max(candidates, key=lambda v: v[0])
        rows.append(dict(input=col, output=output, delay_samples=lag, correlation=corr,
                         abs_correlation=abs(corr), max_lag=max_lag, overlap=n,
                         boundary_hit=lag == max_lag, method='train_only_nonnegative_segment_correlation'))
    return pd.DataFrame(rows)


def residual_acf(df, indices, residual, seconds, max_lag=20):
    values = pd.Series(np.nan, index=df.index)
    values.loc[indices] = residual
    group = groups(df, seconds)
    rows = []
    for lag in range(1, max_lag + 1):
        previous = values.groupby(group).shift(lag)
        pair = pd.concat([values, previous], axis=1).dropna()
        if len(pair) < 3: continue
        corr = pair.iloc[:, 0].corr(pair.iloc[:, 1])
        rows.append({'lag': lag, 'autocorrelation': float(corr) if np.isfinite(corr) else 0.,
                     'valid_pairs': len(pair)})
    return pd.DataFrame(rows, columns=['lag', 'autocorrelation', 'valid_pairs'])


def evaluation(df, state, guard, split, detailed=True):
    df = df.reset_index(drop=True)
    output, seconds = state['output'], state['seconds']
    x = features(df, output, state['inputs'], state['delays'], state['order'], seconds)
    y = df[output]
    # Identical targets for every candidate, independent of fitted delays/order.
    age = df.groupby(groups(df, seconds)).cumcount()
    common = (age >= guard) & y.notna()
    baseline = shifted(df, output, 1, seconds)
    common &= baseline.notna()
    for lag in (1, 2, 3): common &= shifted(df, output, lag, seconds).notna()
    all_inputs = state.get('evaluation_inputs', state['inputs'])
    valid_inputs = df[all_inputs].notna().all(axis=1)
    common &= valid_inputs.rolling(guard + 1, min_periods=guard + 1).sum().eq(guard + 1)
    indices = df.index[common]
    if len(indices) < 10: raise ValueError('独立评估样本不足')
    if x.loc[indices].isna().any().any():
        raise ValueError('候选无法预测共同评估样本，禁止静默改变验证集')
    actual = y.loc[indices].to_numpy()
    pred = predict(x.loc[indices], state['coef'])
    if not np.isfinite(pred).all(): raise ValueError('预测非有限值')
    metrics = regression_metrics(actual, pred, len(state['coef']))
    persistence = regression_metrics(actual, baseline.loc[indices], 1)
    residual = actual - pred
    timestamps = df.loc[indices, 'timestamp'].astype(str).tolist()
    diagnostics = {
        'prediction_mode': 'one_step',
        'evaluation_target_hash': hashlib.sha256('\n'.join(timestamps).encode()).hexdigest(),
        'persistence': persistence,
        'rmse_improvement_over_persistence_pct': 100 * (1 - metrics['rmse'] / max(persistence['rmse'], 1e-12)),
        'evaluation_samples': len(indices),
        'partition_rows': len(df), 'guard_samples': guard, 'excluded_after_guard': int((age >= guard).sum()) - len(indices),
    }
    acf = residual_acf(df, indices, residual, seconds)
    prediction = pd.DataFrame({'timestamp': timestamps, 'index': indices, 'y_true': actual,
                               'y_pred': pred, 'residual': residual, 'split': split})
    if not detailed:
        return metrics, diagnostics, prediction, acf
    # Rolling 10-step prediction: measured y only before each forecast origin.
    horizon = 10
    order = state['order']
    coef = np.asarray(state['coef'], dtype=float)
    x_values = x.to_numpy(dtype=float, copy=True)
    y_values = y.to_numpy(dtype=float, copy=True)
    age_values = age.to_numpy(dtype=int, copy=False)
    end_positions = indices.to_numpy(dtype=int, copy=False)
    origins = end_positions - horizon + 1
    eligible = (origins >= order) & (age_values[end_positions] >= guard + horizon)
    end_positions, origins = end_positions[eligible], origins[eligible]

    # Every endpoint has its own ten-sample forecast window.  Evaluate all
    # endpoints together so the only Python loop is the fixed forecast horizon.
    forecast_paths = np.full((len(end_positions), horizon), np.nan, dtype=float)
    for step in range(horizon):
        positions = origins + step
        rows = x_values[positions].copy()
        for lag_index in range(order):
            lag = lag_index + 1
            simulated_step = step - lag
            if simulated_step >= 0:
                rows[:, lag_index] = forecast_paths[:, simulated_step]
            else:
                rows[:, lag_index] = y_values[positions - lag]
        with np.errstate(over='ignore', invalid='ignore'):
            forecast_paths[:, step] = coef[0] + rows @ coef[1:]
    forecasts = forecast_paths[:, -1]
    finite_forecasts = np.isfinite(forecasts)
    forecasts = forecasts[finite_forecasts]
    valid_ends = end_positions[finite_forecasts]
    valid_origins = origins[finite_forecasts]
    truths = y_values[valid_ends]
    holds = y_values[valid_origins - 1]
    diagnostics['multi_step'] = {'horizon_samples': horizon, 'future_inputs': 'observed historical inputs (conditional evaluation)',
        'metrics': regression_metrics(truths, forecasts, len(state['coef'])) if len(truths) else None,
        'persistence': regression_metrics(truths, holds, 1) if len(truths) else None}
    # Conditional free simulation: no measured output feedback after initialization.
    simulated = y_values.copy()
    for pos in range(len(df)):
        if age_values[pos] < guard: continue
        row = x_values[pos].copy()
        for j in range(order): row[j] = simulated[pos-j-1]
        with np.errstate(over='ignore', invalid='ignore'):
            simulated[pos] = coef[0] + np.dot(row, coef[1:])
    evaluation_positions = indices.to_numpy(dtype=int, copy=False)
    simulation_finite = np.isfinite(simulated[evaluation_positions]).all() and np.max(np.abs(simulated[evaluation_positions])) < 1e12
    diagnostics['free_simulation'] = {'conditional_on_observed_inputs': True, 'diverged': not bool(simulation_finite),
        'metrics': regression_metrics(actual, simulated[evaluation_positions], len(state['coef'])) if simulation_finite else None}
    acf = residual_acf(df, indices, residual, seconds)
    diagnostics['residual'] = {'acf_max_abs': float(acf.autocorrelation.abs().max()) if len(acf) else None,
                               'heuristic_95pct_bound': 1.96 / np.sqrt(len(residual)),
                               'whiteness_test': 'not_performed; ACF is diagnostic only'}
    prediction = pd.DataFrame({'timestamp': timestamps, 'index': indices, 'y_true': actual,
                               'y_pred': pred, 'residual': residual, 'split': split})
    return metrics, diagnostics, prediction, acf


def search_structure_orders(train, validation, output_col, input_cols, selected, delay_map, seconds, guard, policy=None):
    """Shared candidate fitting; selection never reads the held-out test set."""
    policy = policy or {}
    candidates, fitted = [], []
    families = [str(value).upper() for value in policy.get('model_families', ['ARX', 'AR'])]
    orders = [int(value) for value in policy.get('orders', [1, 2, 3])]
    ridge_alphas = [float(value) for value in policy.get('ridge_alphas', [0., 1., 10.])]
    family_specs = []
    if 'ARX' in families:
        family_specs.append(('ARX', selected, ridge_alphas))
    if 'AR' in families:
        family_specs.append(('AR', [], (0.,)))
    # Real order and model-family search, all on the same validation targets.
    for family, variables, alphas in family_specs:
        for order in orders:
            for alpha in alphas:
                try:
                    x = features(train, output_col, variables, delay_map, order, seconds)
                    coef, valid, rank = fit(x, train[output_col], alpha=alpha)
                    state = dict(output=output_col, seconds=seconds, inputs=variables, delays=delay_map,
                                 order=order, coef=coef.tolist(), family=family, regularization_alpha=alpha,
                                 evaluation_inputs=input_cols)
                    m, d, p, acf = evaluation(validation, state, guard, 'validation', detailed=True)
                    tm = regression_metrics(train.loc[valid, output_col], predict(x.loc[valid], coef), len(coef))
                    roots = np.roots(np.r_[1, -np.array(coef[1:order + 1])])
                    stable = bool(np.all(np.abs(roots) < 1))
                    simulation_valid = bool(d.get('free_simulation', {}).get('metrics')) and not d.get('free_simulation', {}).get('diverged')
                    eligible = stable and simulation_valid
                    candidates.append(dict(family=family, order=order, regularization_alpha=alpha,
                                           status='completed', eligible=eligible, stable_ar_poles=stable,
                                           validation_free_simulation_valid=simulation_valid,
                                           max_pole_magnitude=float(max(np.abs(roots))), validation=m, train=tm, rank=rank))
                    if eligible:
                        fitted.append((m['rmse'], state, tm, m, d, p, acf, list(x.columns)))
                except ValueError as exc:
                    candidates.append(dict(family=family, order=order, regularization_alpha=alpha,
                                           status='failed', error=str(exc)))
    return candidates, fitted


def run_validated_modeling(input_csv, output_col, input_cols, output_dir, validation_csv, guard, seconds, max_lag, policy=None):
    policy = policy or {}
    out = Path(output_dir)
    for folder in ('01_time_delay', '02_collinearity', '03_system_identification'): (out/folder).mkdir(parents=True, exist_ok=True)
    train, validation = pd.read_csv(input_csv), pd.read_csv(validation_csv)
    requested_max_lag = max_lag
    max_lag = max(0, min(max_lag, guard - 3))
    delays = estimate_training_delays(train, output_col, input_cols, seconds, max_lag)
    delay_map = dict(zip(delays.input, delays.delay_samples.astype(int)))
    aligned = train.copy()
    for col in input_cols: aligned[col+'_aligned'] = shifted(train, col, delay_map[col], seconds)
    aligned_cols = [c+'_aligned' for c in input_cols]
    # Drop incomplete rows before diagnostics; never interpolate across a gap.
    diagnostic_data = aligned.dropna(subset=aligned_cols+[output_col])
    if len(diagnostic_data) < 20: raise ValueError('时滞对齐后训练样本不足')
    corr = correlation_matrix(diagnostic_data, aligned_cols)
    vif = compute_vif(diagnostic_data, aligned_cols)
    corr_threshold = float(policy.get('correlation_threshold', 0.9))
    vif_threshold = float(policy.get('vif_threshold', 10.0))
    recommendation = recommend_variables(
        diagnostic_data, aligned_cols, output_col,
        corr_threshold=corr_threshold, vif_threshold=vif_threshold,
    )
    final_vif = compute_vif(diagnostic_data, recommendation["keep"])
    recommendation["final_vif"] = final_vif.to_dict("records")
    selected = [c.removesuffix('_aligned') for c in recommendation['keep']]
    coldir, modeldir, lagdir = out/'02_collinearity', out/'03_system_identification', out/'01_time_delay'
    corr.to_csv(coldir/'correlation_matrix.csv')
    vif.to_csv(coldir/'vif_table.csv', index=False)
    final_vif.to_csv(coldir/'final_vif_table.csv', index=False)
    highly_correlated_pairs(corr, corr_threshold).to_csv(coldir/'high_correlation_pairs.csv', index=False)
    save_json(coldir/'variable_recommendation.json', recommendation)
    delays.to_csv(lagdir/'delay_estimates.csv', index=False)
    aligned.to_csv(lagdir/'delay_compensated_data.csv', index=False)
    save_json(lagdir/'delay_summary.json', delays.to_dict('records'))
    families = [str(value).upper() for value in policy.get('model_families', ['ARX', 'AR'])]
    orders = [int(value) for value in policy.get('orders', [1, 2, 3])]
    ridge_alphas = [float(value) for value in policy.get('ridge_alphas', [0., 1., 10.])]
    candidates, fitted = search_structure_orders(
        train, validation, output_col, input_cols, selected, delay_map, seconds, guard, policy,
    )
    save_json(modeldir/'order_search.json', candidates)
    if not fitted: raise ValueError('所有结构候选均失败：' + '; '.join(sorted({c.get('error', '') for c in candidates})))
    # Prefer the validation BIC so a marginal one-step RMSE gain cannot promote a
    # very high-dimensional ARX model over a simpler, better-supported baseline.
    _, state, tm, vm, diagnostics, prediction, acf, names = min(fitted, key=lambda v: v[3]['bic'])
    vm, diagnostics, prediction, acf = evaluation(validation, state, guard, 'validation')
    roots = np.roots(np.r_[1, -np.array(state['coef'][1:state['order']+1])])
    diagnostics['stable_ar_poles'] = bool(np.all(np.abs(roots) < 1))
    diagnostics['max_pole_magnitude'] = float(max(np.abs(roots)))
    diagnostics['validation_only'] = True
    save_json(modeldir/'fitted_state.json', state)
    response_analysis = arx_response_analysis(state)
    save_json(modeldir/'response_analysis.json', response_analysis)
    save_json(modeldir/'order_search.json', candidates)
    save_json(modeldir/'model_metrics.json', {'train': tm, 'validation': vm})
    save_json(modeldir/'diagnostics.json', diagnostics)
    save_json(modeldir/'model_features.json', names)
    prediction.to_csv(modeldir/'prediction_residuals.csv', index=False)
    acf.to_csv(modeldir/'residual_autocorrelation.csv', index=False)
    pd.DataFrame({'term':['intercept']+names, 'coefficient':state['coef']}).to_csv(modeldir/'arx_coefficients.csv', index=False)
    config = dict(protocol='chronological_60_20_20_v2', max_lag=max_lag, requested_max_lag=int(requested_max_lag),
                  output_order=state['order'], input_order=state['order'], input_delay=1,
                  train_ratio=0.6, validation_ratio=0.2, test_ratio=0.2, guard_samples=guard,
                  family=state['family'], regularization='ridge' if state.get('regularization_alpha', 0) else 'none',
                  regularization_alpha=state.get('regularization_alpha', 0), preprocessing_fit='training_only',
                  causal_lags=True, segment_aware=True,
                  correlation_threshold=corr_threshold, vif_threshold=vif_threshold,
                  candidate_families=families, candidate_orders=orders, ridge_alphas=ridge_alphas)
    family_comparison = {}
    for family in ('ARX', 'AR'):
        completed = [row for row in candidates if row.get('family') == family and row.get('status') == 'completed' and row.get('eligible')]
        if completed:
            best_family = min(completed, key=lambda row: row['validation']['rmse'])
            family_comparison[family] = {
                'validation_rmse': best_family['validation']['rmse'],
                'validation_r2': best_family['validation']['r2'],
                'order': best_family['order'],
                'regularization_alpha': best_family.get('regularization_alpha', 0),
            }
    summary = dict(config=config, selection_criterion='minimum_validation_bic_with_stability_and_simulation_gate',
                   selected_inputs_after_collinearity=recommendation['keep'],
                   diagnostics=diagnostics, order_search=candidates, training_rows=len(train),
                   fitted_inputs=state['inputs'], response_analysis=response_analysis,
                   family_comparison=family_comparison)
    save_json(out/'pipeline_summary.json', summary)
    return summary


def finalize_test(output_dir, test_csv):
    out = Path(output_dir); modeldir = out/'03_system_identification'
    summary = json.loads((out/'pipeline_summary.json').read_text())
    state = json.loads((modeldir/'fitted_state.json').read_text())
    metrics, diagnostics, prediction, acf = evaluation(pd.read_csv(test_csv), state, summary['config']['guard_samples'], 'test')
    existing = json.loads((modeldir/'model_metrics.json').read_text()); existing['test'] = metrics
    save_json(modeldir/'model_metrics.json', existing)
    vd = json.loads((modeldir/'diagnostics.json').read_text())
    vd['test'] = diagnostics
    save_json(modeldir/'diagnostics.json', vd)
    prediction.to_csv(modeldir/'test_prediction_residuals.csv', index=False)
    acf.to_csv(modeldir/'test_residual_autocorrelation.csv', index=False)
    return existing, vd
