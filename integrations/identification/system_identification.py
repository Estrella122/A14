#!/usr/bin/env python3
"""ARX / linear system identification for APC modeling data.

The ARX form is:
    y(k) = c + a1*y(k-1) + ... + b11*u1(k-1) + ... + error(k)

Use delay-compensated and collinearity-filtered data as input when available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        raise ValueError(f"Missing column: {col}")
    return pd.to_numeric(df[col], errors="coerce")


def build_arx_dataset(
    df: pd.DataFrame,
    output_col: str,
    input_cols: Sequence[str],
    output_order: int = 2,
    input_order: int = 2,
    input_delay: int = 1,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Build lagged ARX feature matrix and aligned target series."""
    if output_order < 0 or input_order < 0 or input_delay < 0:
        raise ValueError("Orders and delay must be non-negative.")

    y = _numeric_series(df, output_col)
    features = pd.DataFrame(index=df.index)

    for lag in range(1, output_order + 1):
        features[f"{output_col}_lag{lag}"] = y.shift(lag)

    for col in input_cols:
        x = _numeric_series(df, col)
        for lag in range(input_delay, input_delay + input_order):
            features[f"{col}_lag{lag}"] = x.shift(lag)

    dataset = pd.concat([features, y.rename(output_col)], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    x = dataset.drop(columns=[output_col])
    target = dataset[output_col]
    return x, target


def train_test_split_time_order(
    x: pd.DataFrame,
    y: pd.Series,
    train_ratio: float = 0.7,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    if not 0.1 <= train_ratio <= 0.95:
        raise ValueError("train_ratio must be between 0.1 and 0.95.")
    n = len(x)
    split = max(1, min(n - 1, int(n * train_ratio)))
    return x.iloc[:split], x.iloc[split:], y.iloc[:split], y.iloc[split:]


def fit_least_squares(x_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, object]:
    x = x_train.to_numpy(dtype=float)
    y = y_train.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    names = ["intercept"] + list(x_train.columns)
    return {"coef": coef, "coef_table": pd.DataFrame({"term": names, "coefficient": coef})}


def predict(model: Dict[str, object], x: pd.DataFrame) -> np.ndarray:
    coef = np.asarray(model["coef"], dtype=float)
    design = np.column_stack([np.ones(len(x)), x.to_numpy(dtype=float)])
    return design @ coef


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float], num_params: int) -> Dict[str, float]:
    y = np.asarray(list(y_true), dtype=float)
    pred = np.asarray(list(y_pred), dtype=float)
    residual = y - pred
    n = len(y)
    sse = float(np.sum(residual**2))
    mse = sse / n if n else np.nan
    rmse = float(np.sqrt(mse)) if n else np.nan
    mae = float(np.mean(np.abs(residual))) if n else np.nan
    ss_tot = float(np.sum((y - y.mean()) ** 2)) if n else np.nan
    r2 = 1.0 - sse / ss_tot if ss_tot and ss_tot > 0 else np.nan
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / max(n - num_params - 1, 1) if np.isfinite(r2) and n > 1 else np.nan
    fpe = float(mse * (n + num_params) / max(n - num_params, 1)) if n else np.nan
    aic = float(n * np.log(max(sse / n, 1e-12)) + 2 * num_params) if n else np.nan
    bic = float(n * np.log(max(sse / n, 1e-12)) + np.log(max(n, 1)) * num_params) if n else np.nan
    return {
        "n_samples": float(n),
        "num_params": float(num_params),
        "r2": float(r2),
        "adjusted_r2": float(adj_r2),
        "rmse": rmse,
        "mae": mae,
        "mse": float(mse),
        "sse": sse,
        "fpe": fpe,
        "aic": aic,
        "bic": bic,
    }


def residual_autocorrelation(residual: Iterable[float], max_lag: int = 20) -> pd.DataFrame:
    r = np.asarray(list(residual), dtype=float)
    r = r[np.isfinite(r)]
    rows = []
    if len(r) < 3:
        return pd.DataFrame(columns=["lag", "autocorrelation"])
    centered = r - r.mean()
    denom = float(np.sum(centered**2))
    for lag in range(1, min(max_lag, len(r) - 2) + 1):
        value = float(np.sum(centered[:-lag] * centered[lag:]) / denom) if denom > 0 else np.nan
        rows.append({"lag": lag, "autocorrelation": value})
    return pd.DataFrame(rows)


def fit_arx_model(
    df: pd.DataFrame,
    output_col: str,
    input_cols: Sequence[str],
    output_order: int = 2,
    input_order: int = 2,
    input_delay: int = 1,
    train_ratio: float = 0.7,
    residual_lags: int = 20,
) -> Dict[str, object]:
    x, y = build_arx_dataset(df, output_col, input_cols, output_order, input_order, input_delay)
    if len(x) < 10:
        raise ValueError("Not enough samples after lag construction. Try lower orders or more data.")

    x_train, x_test, y_train, y_test = train_test_split_time_order(x, y, train_ratio)
    model = fit_least_squares(x_train, y_train)

    train_pred = predict(model, x_train)
    test_pred = predict(model, x_test)
    all_pred = predict(model, x)
    num_params = len(model["coef"])

    train_metrics = regression_metrics(y_train, train_pred, num_params)
    test_metrics = regression_metrics(y_test, test_pred, num_params)
    all_metrics = regression_metrics(y, all_pred, num_params)
    residual = y.to_numpy(dtype=float) - all_pred
    residual_acf = residual_autocorrelation(residual, residual_lags)

    prediction = pd.DataFrame(
        {
            "index": y.index,
            "y_true": y.to_numpy(dtype=float),
            "y_pred": all_pred,
            "residual": residual,
            "split": ["train" if i < len(y_train) else "test" for i in range(len(y))],
        }
    )

    return {
        "coef_table": model["coef_table"],
        "metrics": {"train": train_metrics, "test": test_metrics, "all": all_metrics},
        "prediction": prediction,
        "residual_autocorrelation": residual_acf,
        "feature_columns": list(x.columns),
    }


def infer_input_columns(df: pd.DataFrame, output_col: str, timestamp_col: Optional[str]) -> List[str]:
    excluded = {output_col}
    if timestamp_col:
        excluded.add(timestamp_col)
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]


def run_identification_pipeline(
    input_csv: str | Path,
    output_col: str,
    input_cols: Optional[List[str]] = None,
    timestamp_col: Optional[str] = None,
    output_order: int = 2,
    input_order: int = 2,
    input_delay: int = 1,
    train_ratio: float = 0.7,
    output_dir: str | Path = "outputs/system_identification",
) -> Dict[str, str]:
    df = pd.read_csv(input_csv)
    if not input_cols:
        input_cols = infer_input_columns(df, output_col, timestamp_col)
    if not input_cols:
        raise ValueError("No input columns were provided or inferred.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = fit_arx_model(df, output_col, input_cols, output_order, input_order, input_delay, train_ratio)

    coef_path = out_dir / "arx_coefficients.csv"
    metrics_path = out_dir / "model_metrics.json"
    pred_path = out_dir / "prediction_residuals.csv"
    acf_path = out_dir / "residual_autocorrelation.csv"
    feature_path = out_dir / "model_features.json"

    result["coef_table"].to_csv(coef_path, index=False, encoding="utf-8-sig")
    metrics_path.write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    result["prediction"].to_csv(pred_path, index=False, encoding="utf-8-sig")
    result["residual_autocorrelation"].to_csv(acf_path, index=False, encoding="utf-8-sig")
    feature_path.write_text(json.dumps(result["feature_columns"], ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "arx_coefficients": str(coef_path),
        "model_metrics": str(metrics_path),
        "prediction_residuals": str(pred_path),
        "residual_autocorrelation": str(acf_path),
        "model_features": str(feature_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit an ARX/linear system-identification model.")
    parser.add_argument("--input", required=True, help="Input CSV file after time-delay and collinearity processing.")
    parser.add_argument("--output-col", required=True, help="Output variable, e.g. furnace actual temperature.")
    parser.add_argument("--input-cols", nargs="*", default=None, help="Input variables. Defaults to numeric non-output columns.")
    parser.add_argument("--timestamp-col", default=None, help="Timestamp column to exclude from features.")
    parser.add_argument("--output-order", type=int, default=2, help="Number of output autoregressive lags.")
    parser.add_argument("--input-order", type=int, default=2, help="Number of lag terms per input.")
    parser.add_argument("--input-delay", type=int, default=1, help="Minimum input lag after compensation.")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Time-ordered train split ratio.")
    parser.add_argument("--output-dir", default="outputs/system_identification", help="Directory for outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_identification_pipeline(
        input_csv=args.input,
        output_col=args.output_col,
        input_cols=args.input_cols,
        timestamp_col=args.timestamp_col,
        output_order=args.output_order,
        input_order=args.input_order,
        input_delay=args.input_delay,
        train_ratio=args.train_ratio,
        output_dir=args.output_dir,
    )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
