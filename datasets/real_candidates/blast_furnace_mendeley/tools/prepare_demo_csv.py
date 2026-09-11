#!/usr/bin/env python3
"""Build a causal, upload-ready CSV from the immutable Mendeley workbook.

The process table is sampled hourly while hot-metal Si is sampled by the lab at
irregular times.  Each process row receives only the latest Si observation that
already existed at that timestamp.  Future laboratory values are never used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


FIELD_MAP = {
    "dt": "timestamp",
    "Fb": "blast_flow_rate",
    "Ph": "hot_blast_pressure",
    "Pc": "cold_blast_pressure",
    "Tc": "cold_blast_temperature",
    "Fo": "oxygen_flow_rate",
    "dP": "total_pressure_drop",
    "dPu": "upper_pressure_drop",
    "dPl": "lower_pressure_drop",
    "Pt": "top_gas_pressure",
    "Th": "hot_blast_temperature",
    "CO2": "top_gas_co2",
    "H2": "top_gas_h2",
    **{f"Tt{i}": f"top_gas_temp_{i}" for i in range(1, 5)},
    **{f"Tp{i}": f"peripheral_gas_temp_{i}" for i in range(1, 11)},
    "R": "ore_coke_ratio",
    "Si": "hot_metal_si",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(source: Path, output: Path, rows: int = 720, tolerance_hours: int = 3) -> dict:
    process = pd.read_excel(source, sheet_name="data")
    lab = pd.read_excel(source, sheet_name="Si")
    process["dt"] = pd.to_datetime(process["dt"], errors="raise")
    lab["dt"] = pd.to_datetime(lab["dt"], errors="raise")
    process = process.sort_values("dt").head(rows).copy()
    lab = lab.sort_values("dt").rename(columns={"dt": "lab_source_timestamp"})
    joined = pd.merge_asof(
        process,
        lab[["lab_source_timestamp", "Si"]],
        left_on="dt",
        right_on="lab_source_timestamp",
        direction="backward",
        tolerance=pd.Timedelta(f"{tolerance_hours}h"),
    )
    joined["lab_age_minutes"] = (joined["dt"] - joined["lab_source_timestamp"]).dt.total_seconds() / 60
    joined["lab_fresh"] = joined["Si"].notna()
    joined["lab_source_timestamp"] = joined["lab_source_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    joined = joined.rename(columns=FIELD_MAP)
    ordered = [FIELD_MAP[column] for column in process.columns if column in FIELD_MAP]
    ordered += ["hot_metal_si", "lab_source_timestamp", "lab_age_minutes", "lab_fresh"]
    joined = joined[ordered]
    joined["timestamp"] = joined["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    # Keep hours without a recent lab value. The downstream causal cleaning policy
    # must leave these targets missing, making leakage checks visible and auditable.
    joined = joined.reset_index(drop=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(output, index=False, encoding="utf-8-sig")
    return {
        "source_file": source.name,
        "source_sha256": sha256(source),
        "output_file": output.name,
        "rows": len(joined),
        "columns": len(joined.columns),
        "start": joined["timestamp"].iloc[0],
        "end": joined["timestamp"].iloc[-1],
        "alignment": "causal merge_asof(direction=backward)",
        "tolerance_hours": tolerance_hours,
        "future_lab_values_used": False,
        "dataset_doi": "10.17632/6d7jbc7tb5.1",
        "license": "CC BY 4.0",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--rows", type=int, default=720)
    args = parser.parse_args()
    manifest = build(args.source, args.output, max(args.rows, 24))
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
