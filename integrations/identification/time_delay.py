#!/usr/bin/env python3
"""Time-delay analysis and compensation for industrial time-series data.

This module estimates input-output delays with normalized cross-correlation.
Positive delay means the input leads the output by that many samples, so the
input is shifted forward for compensation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


def _numeric_frame(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    out = df.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    return out.interpolate(limit_direction="both").ffill().bfill()


def _aligned_for_lag(x: np.ndarray, y: np.ndarray, lag: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return aligned x/y arrays for a candidate lag.

    lag > 0: x happens earlier and is compared with future y.
    lag < 0: y happens earlier and is compared with future x.
    """
    if lag > 0:
        return x[:-lag], y[lag:]
    if lag < 0:
        return x[-lag:], y[:lag]
    return x, y


def normalized_cross_correlation(
    x: Iterable[float],
    y: Iterable[float],
    max_lag: int,
    min_overlap: int = 20,
) -> pd.DataFrame:
    """Compute normalized cross-correlation for lags in [-max_lag, max_lag]."""
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    rows: List[Dict[str, float]] = []

    for lag in range(-int(max_lag), int(max_lag) + 1):
        xa, ya = _aligned_for_lag(x_arr, y_arr, lag)
        mask = np.isfinite(xa) & np.isfinite(ya)
        xa, ya = xa[mask], ya[mask]
        if len(xa) < min_overlap:
            corr = np.nan
        else:
            xs = xa - xa.mean()
            ys = ya - ya.mean()
            denom = float(np.sqrt(np.sum(xs * xs) * np.sum(ys * ys)))
            corr = float(np.sum(xs * ys) / denom) if denom > 0 else np.nan
        rows.append({"lag": lag, "correlation": corr, "abs_correlation": abs(corr) if np.isfinite(corr) else np.nan})

    return pd.DataFrame(rows)


def estimate_delay(
    df: pd.DataFrame,
    input_col: str,
    output_col: str,
    max_lag: int = 60,
    min_overlap: int = 20,
) -> Dict[str, float]:
    """Estimate delay from input_col to output_col.

    Returns the lag with the largest absolute normalized correlation.
    """
    data = _numeric_frame(df, [input_col, output_col]).dropna()
    corr = normalized_cross_correlation(data[input_col], data[output_col], max_lag, min_overlap)
    valid = corr.dropna(subset=["correlation"])
    if valid.empty:
        raise ValueError(f"No valid correlation result for {input_col} -> {output_col}")
    best = valid.loc[valid["abs_correlation"].idxmax()]
    return {
        "input": input_col,
        "output": output_col,
        "delay_samples": int(best["lag"]),
        "correlation": float(best["correlation"]),
        "abs_correlation": float(best["abs_correlation"]),
        "max_lag": int(max_lag),
    }


def estimate_delays(
    df: pd.DataFrame,
    input_cols: Iterable[str],
    output_col: str,
    max_lag: int = 60,
    min_overlap: int = 20,
) -> pd.DataFrame:
    rows = [estimate_delay(df, col, output_col, max_lag, min_overlap) for col in input_cols]
    return pd.DataFrame(rows).sort_values("abs_correlation", ascending=False).reset_index(drop=True)


def compensate_delays(df: pd.DataFrame, delay_table: pd.DataFrame, suffix: str = "_aligned") -> pd.DataFrame:
    """Shift inputs according to estimated delays and append aligned columns."""
    out = df.copy()
    for _, row in delay_table.iterrows():
        col = row["input"]
        delay = int(row["delay_samples"])
        aligned_name = f"{col}{suffix}"
        out[aligned_name] = pd.to_numeric(out[col], errors="coerce").shift(delay)
    return out


def infer_input_columns(df: pd.DataFrame, output_col: str, timestamp_col: Optional[str]) -> List[str]:
    excluded = {output_col}
    if timestamp_col:
        excluded.add(timestamp_col)
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]


def run_time_delay_pipeline(
    input_csv: str | Path,
    output_col: str,
    input_cols: Optional[List[str]] = None,
    timestamp_col: Optional[str] = None,
    max_lag: int = 60,
    min_overlap: int = 20,
    output_dir: str | Path = "outputs/time_delay",
) -> Dict[str, str]:
    df = pd.read_csv(input_csv)
    if input_cols is None or len(input_cols) == 0:
        input_cols = infer_input_columns(df, output_col, timestamp_col)
    if not input_cols:
        raise ValueError("No input columns were provided or inferred.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    delay_table = estimate_delays(df, input_cols, output_col, max_lag, min_overlap)
    compensated = compensate_delays(df, delay_table)

    delay_path = out_dir / "delay_estimates.csv"
    aligned_path = out_dir / "delay_compensated_data.csv"
    json_path = out_dir / "delay_summary.json"

    delay_table.to_csv(delay_path, index=False, encoding="utf-8-sig")
    compensated.to_csv(aligned_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(delay_table.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "delay_estimates": str(delay_path),
        "delay_compensated_data": str(aligned_path),
        "delay_summary": str(json_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate and compensate input-output time delays.")
    parser.add_argument("--input", required=True, help="Input CSV file, usually the dynamic segment from member 3.")
    parser.add_argument("--output-col", required=True, help="Output variable, e.g. furnace temperature.")
    parser.add_argument("--input-cols", nargs="*", default=None, help="Input variables. Defaults to all numeric non-output columns.")
    parser.add_argument("--timestamp-col", default=None, help="Timestamp column to exclude from inputs.")
    parser.add_argument("--max-lag", type=int, default=60, help="Maximum lag in samples for cross-correlation search.")
    parser.add_argument("--min-overlap", type=int, default=20, help="Minimum overlapping samples for each candidate lag.")
    parser.add_argument("--output-dir", default="outputs/time_delay", help="Directory for CSV/JSON outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_time_delay_pipeline(
        input_csv=args.input,
        output_col=args.output_col,
        input_cols=args.input_cols,
        timestamp_col=args.timestamp_col,
        max_lag=args.max_lag,
        min_overlap=args.min_overlap,
        output_dir=args.output_dir,
    )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
