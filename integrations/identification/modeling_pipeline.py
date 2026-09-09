#!/usr/bin/env python3
"""One-command modeling pipeline for member 4.

This script is the integration entrypoint for Agent / frontend calls.
It runs time-delay compensation, collinearity handling, ARX identification,
and plot generation in a single workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from collinearity import run_collinearity_pipeline
from system_identification import run_identification_pipeline
from time_delay import infer_input_columns, run_time_delay_pipeline
from visualization import (
    plot_correlation_heatmap,
    plot_delay_bar,
    plot_prediction_and_residual,
    plot_residual_acf,
)


def _read_json(path: str | Path) -> Dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _aligned_names(input_cols: List[str]) -> List[str]:
    return [f"{col}_aligned" for col in input_cols]


def _safe_plot(plot_func, *args) -> Optional[str]:
    try:
        return plot_func(*args)
    except Exception as exc:
        return f"plot_failed: {exc}"


def run_full_modeling_pipeline(
    input_csv: str | Path,
    output_col: str,
    input_cols: Optional[List[str]] = None,
    timestamp_col: Optional[str] = None,
    max_lag: int = 60,
    min_overlap: int = 20,
    corr_threshold: float = 0.9,
    vif_threshold: float = 10.0,
    output_order: int = 2,
    input_order: int = 2,
    input_delay: int = 1,
    train_ratio: float = 0.7,
    output_dir: str | Path = "outputs/modeling_pipeline",
) -> Dict[str, object]:
    df = pd.read_csv(input_csv)
    if not input_cols:
        input_cols = infer_input_columns(df, output_col, timestamp_col)
    if not input_cols:
        raise ValueError("No input columns were provided or inferred.")

    out_dir = Path(output_dir)
    delay_dir = out_dir / "01_time_delay"
    col_dir = out_dir / "02_collinearity"
    id_dir = out_dir / "03_system_identification"
    plot_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    delay_outputs = run_time_delay_pipeline(
        input_csv=input_csv,
        output_col=output_col,
        input_cols=input_cols,
        timestamp_col=timestamp_col,
        max_lag=max_lag,
        min_overlap=min_overlap,
        output_dir=delay_dir,
    )

    aligned_cols = _aligned_names(input_cols)
    col_outputs = run_collinearity_pipeline(
        input_csv=delay_outputs["delay_compensated_data"],
        feature_cols=aligned_cols,
        output_col=output_col,
        timestamp_col=timestamp_col,
        corr_threshold=corr_threshold,
        vif_threshold=vif_threshold,
        merge=True,
        output_dir=col_dir,
    )

    recommendation = _read_json(col_outputs["variable_recommendation"])
    selected_inputs = list(recommendation.get("keep", []))
    if not selected_inputs:
        selected_inputs = aligned_cols

    id_outputs = run_identification_pipeline(
        input_csv=delay_outputs["delay_compensated_data"],
        output_col=output_col,
        input_cols=selected_inputs,
        timestamp_col=timestamp_col,
        output_order=output_order,
        input_order=input_order,
        input_delay=input_delay,
        train_ratio=train_ratio,
        output_dir=id_dir,
    )

    plots = {
        "delay_bar": _safe_plot(plot_delay_bar, delay_outputs["delay_estimates"], plot_dir / "delay_bar.png"),
        "correlation_heatmap": _safe_plot(plot_correlation_heatmap, col_outputs["correlation_matrix"], plot_dir / "correlation_heatmap.png"),
        "prediction_residual": _safe_plot(plot_prediction_and_residual, id_outputs["prediction_residuals"], plot_dir / "prediction_residual.png"),
        "residual_autocorrelation": _safe_plot(plot_residual_acf, id_outputs["residual_autocorrelation"], plot_dir / "residual_autocorrelation.png"),
    }

    summary: Dict[str, object] = {
        "input_csv": str(input_csv),
        "output_col": output_col,
        "input_cols": input_cols,
        "selected_inputs_after_collinearity": selected_inputs,
        "config": {
            "max_lag": max_lag,
            "min_overlap": min_overlap,
            "corr_threshold": corr_threshold,
            "vif_threshold": vif_threshold,
            "output_order": output_order,
            "input_order": input_order,
            "input_delay": input_delay,
            "train_ratio": train_ratio,
        },
        "time_delay": delay_outputs,
        "collinearity": col_outputs,
        "system_identification": id_outputs,
        "plots": plots,
    }

    summary_path = out_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["pipeline_summary"] = str(summary_path)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full member-4 modeling workflow.")
    parser.add_argument("--input", required=True, help="Input CSV file.")
    parser.add_argument("--output-col", required=True, help="Output variable.")
    parser.add_argument("--input-cols", nargs="*", default=None, help="Input variables. Defaults to numeric non-output columns.")
    parser.add_argument("--timestamp-col", default=None, help="Timestamp column to exclude.")
    parser.add_argument("--max-lag", type=int, default=60)
    parser.add_argument("--min-overlap", type=int, default=20)
    parser.add_argument("--corr-threshold", type=float, default=0.9)
    parser.add_argument("--vif-threshold", type=float, default=10.0)
    parser.add_argument("--output-order", type=int, default=2)
    parser.add_argument("--input-order", type=int, default=2)
    parser.add_argument("--input-delay", type=int, default=1)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--output-dir", default="outputs/modeling_pipeline")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_full_modeling_pipeline(
        input_csv=args.input,
        output_col=args.output_col,
        input_cols=args.input_cols,
        timestamp_col=args.timestamp_col,
        max_lag=args.max_lag,
        min_overlap=args.min_overlap,
        corr_threshold=args.corr_threshold,
        vif_threshold=args.vif_threshold,
        output_order=args.output_order,
        input_order=args.input_order,
        input_delay=args.input_delay,
        train_ratio=args.train_ratio,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
