#!/usr/bin/env python3
"""Collinearity detection and redundant-variable handling.

The module computes a correlation matrix and variance inflation factor (VIF)
scores, then produces a conservative keep/drop recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _prepare_numeric(df: pd.DataFrame, feature_cols: Sequence[str]) -> pd.DataFrame:
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    data = df.loc[:, feature_cols].apply(pd.to_numeric, errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan).interpolate(limit_direction="both").ffill().bfill()
    return data.dropna(axis=1, how="all")


def correlation_matrix(df: pd.DataFrame, feature_cols: Sequence[str]) -> pd.DataFrame:
    data = _prepare_numeric(df, feature_cols)
    return data.corr(method="pearson")


def compute_vif(df: pd.DataFrame, feature_cols: Sequence[str]) -> pd.DataFrame:
    """Compute VIF with least-squares regression and no external dependency."""
    data = _prepare_numeric(df, feature_cols).dropna()
    rows: List[Dict[str, float | str]] = []

    usable_cols = [c for c in data.columns if data[c].std(ddof=0) > 1e-12]
    if len(usable_cols) == 0:
        return pd.DataFrame(columns=["variable", "vif", "r_squared"])

    z = (data[usable_cols] - data[usable_cols].mean()) / data[usable_cols].std(ddof=0)
    z = z.replace([np.inf, -np.inf], np.nan).dropna()

    for col in usable_cols:
        y = z[col].to_numpy(dtype=float)
        others = [c for c in usable_cols if c != col]
        if not others:
            rows.append({"variable": col, "vif": 1.0, "r_squared": 0.0})
            continue
        x = z[others].to_numpy(dtype=float)
        x = np.column_stack([np.ones(len(x)), x])
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        pred = x @ beta
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        r2 = min(max(r2, 0.0), 0.999999)
        vif = 1.0 / (1.0 - r2)
        rows.append({"variable": col, "vif": float(vif), "r_squared": float(r2)})

    return pd.DataFrame(rows).sort_values("vif", ascending=False).reset_index(drop=True)


def highly_correlated_pairs(corr: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            value = corr.loc[a, b]
            if pd.notna(value) and abs(value) >= threshold:
                rows.append({"variable_a": a, "variable_b": b, "correlation": float(value), "abs_correlation": float(abs(value))})
    return pd.DataFrame(rows).sort_values("abs_correlation", ascending=False).reset_index(drop=True) if rows else pd.DataFrame(columns=["variable_a", "variable_b", "correlation", "abs_correlation"])


def recommend_variables(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    output_col: Optional[str] = None,
    corr_threshold: float = 0.9,
    vif_threshold: float = 10.0,
) -> Dict[str, object]:
    """Recommend variables to keep/drop based on pairwise correlation and VIF.

    If output_col is supplied, the variable with weaker absolute correlation to
    the output is dropped first inside highly correlated pairs.
    """
    data = _prepare_numeric(df, feature_cols)
    corr = data.corr()
    pairs = highly_correlated_pairs(corr, corr_threshold)
    vif = compute_vif(df, list(data.columns))
    output_corr = None
    if output_col and output_col in df.columns:
        joined = pd.concat([data, pd.to_numeric(df[output_col], errors="coerce").rename(output_col)], axis=1)
        output_corr = joined.corr()[output_col].drop(labels=[output_col], errors="ignore").abs().to_dict()

    drop: List[str] = []
    reasons: List[Dict[str, object]] = []
    kept = set(data.columns)

    for _, row in pairs.iterrows():
        a, b = str(row["variable_a"]), str(row["variable_b"])
        if a not in kept or b not in kept:
            continue
        if output_corr:
            drop_var = a if output_corr.get(a, 0.0) < output_corr.get(b, 0.0) else b
        else:
            vif_a = float(vif.loc[vif["variable"] == a, "vif"].iloc[0]) if (vif["variable"] == a).any() else 1.0
            vif_b = float(vif.loc[vif["variable"] == b, "vif"].iloc[0]) if (vif["variable"] == b).any() else 1.0
            drop_var = a if vif_a >= vif_b else b
        kept.discard(drop_var)
        drop.append(drop_var)
        reasons.append({"drop": drop_var, "reason": "high_pairwise_correlation", "pair": [a, b], "correlation": float(row["correlation"])})

    while len(kept) > 1:
        current_vif = compute_vif(df, sorted(kept))
        if current_vif.empty:
            break
        worst = current_vif.iloc[0]
        if float(worst["vif"]) < vif_threshold:
            break
        var = str(worst["variable"])
        kept.discard(var)
        drop.append(var)
        reasons.append({"drop": var, "reason": "high_vif", "vif": float(worst["vif"])})

    return {"keep": sorted(kept), "drop": drop, "reasons": reasons}


def merge_correlated_groups(
    df: pd.DataFrame,
    pairs: pd.DataFrame,
    prefix: str = "merged",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Merge correlated variables by averaging standardized values in each group."""
    out = df.copy()
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for _, row in pairs.iterrows():
        union(str(row["variable_a"]), str(row["variable_b"]))

    groups: Dict[str, List[str]] = {}
    for var in parent:
        groups.setdefault(find(var), []).append(var)

    rows = []
    for idx, cols in enumerate(groups.values(), start=1):
        if len(cols) < 2:
            continue
        data = _prepare_numeric(df, cols)
        z = (data - data.mean()) / data.std(ddof=0).replace(0, np.nan)
        new_col = f"{prefix}_{idx}"
        out[new_col] = z.mean(axis=1)
        rows.append({"merged_variable": new_col, "source_variables": ",".join(cols)})

    return out, pd.DataFrame(rows)


def infer_feature_columns(df: pd.DataFrame, output_col: Optional[str], timestamp_col: Optional[str]) -> List[str]:
    excluded = {c for c in [output_col, timestamp_col] if c}
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]


def run_collinearity_pipeline(
    input_csv: str | Path,
    feature_cols: Optional[List[str]] = None,
    output_col: Optional[str] = None,
    timestamp_col: Optional[str] = None,
    corr_threshold: float = 0.9,
    vif_threshold: float = 10.0,
    merge: bool = False,
    output_dir: str | Path = "outputs/collinearity",
) -> Dict[str, str]:
    df = pd.read_csv(input_csv)
    if not feature_cols:
        feature_cols = infer_feature_columns(df, output_col, timestamp_col)
    if not feature_cols:
        raise ValueError("No feature columns were provided or inferred.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corr = correlation_matrix(df, feature_cols)
    pairs = highly_correlated_pairs(corr, corr_threshold)
    vif = compute_vif(df, feature_cols)
    recommendation = recommend_variables(df, feature_cols, output_col, corr_threshold, vif_threshold)

    corr_path = out_dir / "correlation_matrix.csv"
    pairs_path = out_dir / "high_correlation_pairs.csv"
    vif_path = out_dir / "vif_table.csv"
    rec_path = out_dir / "variable_recommendation.json"
    corr.to_csv(corr_path, encoding="utf-8-sig")
    pairs.to_csv(pairs_path, index=False, encoding="utf-8-sig")
    vif.to_csv(vif_path, index=False, encoding="utf-8-sig")
    rec_path.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        "correlation_matrix": str(corr_path),
        "high_correlation_pairs": str(pairs_path),
        "vif_table": str(vif_path),
        "variable_recommendation": str(rec_path),
    }

    if merge:
        merged, merge_map = merge_correlated_groups(df, pairs)
        merged_path = out_dir / "merged_variables_data.csv"
        merge_map_path = out_dir / "merge_map.csv"
        merged.to_csv(merged_path, index=False, encoding="utf-8-sig")
        merge_map.to_csv(merge_map_path, index=False, encoding="utf-8-sig")
        outputs.update({"merged_variables_data": str(merged_path), "merge_map": str(merge_map_path)})

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect collinearity and recommend redundant-variable handling.")
    parser.add_argument("--input", required=True, help="Input CSV file, usually delay-compensated data.")
    parser.add_argument("--feature-cols", nargs="*", default=None, help="Feature columns. Defaults to all numeric non-output columns.")
    parser.add_argument("--output-col", default=None, help="Output variable for keeping variables more related to the target.")
    parser.add_argument("--timestamp-col", default=None, help="Timestamp column to exclude from features.")
    parser.add_argument("--corr-threshold", type=float, default=0.9, help="Absolute correlation threshold for redundancy.")
    parser.add_argument("--vif-threshold", type=float, default=10.0, help="VIF threshold for severe multicollinearity.")
    parser.add_argument("--merge", action="store_true", help="Also create standardized merged variables for correlated groups.")
    parser.add_argument("--output-dir", default="outputs/collinearity", help="Directory for outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_collinearity_pipeline(
        input_csv=args.input,
        feature_cols=args.feature_cols,
        output_col=args.output_col,
        timestamp_col=args.timestamp_col,
        corr_threshold=args.corr_threshold,
        vif_threshold=args.vif_threshold,
        merge=args.merge,
        output_dir=args.output_dir,
    )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
