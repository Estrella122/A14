#!/usr/bin/env python3
"""Prepare the public ordered-sample debutanizer data for ProcessPilot."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "debutanizer_data.txt"
OUTPUT = HERE / "debutanizer_processpilot.csv"

frame = pd.read_csv(SOURCE, sep=r"\s+", skiprows=5, header=None,
                    names=["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"])
if frame.shape != (2394, 8) or frame.isna().any().any():
    raise ValueError(f"公开数据形状或完整性异常：{frame.shape}")
frame.insert(0, "sample_index", range(len(frame)))
# The source preserves order but does not publish calendar timestamps or a
# sampling interval. This clock encodes order only and must not be interpreted
# as plant wall-clock time.
frame.insert(0, "sample_timestamp", pd.date_range("2000-01-01", periods=len(frame), freq="1s"))
frame.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
metadata = {
    "dataset": "Fortuna debutanizer column benchmark",
    "source_url": "https://raw.githubusercontent.com/Ujjwal-1267/industrial-debutanizer-soft-sensor/main/data/debutanizer_data.txt",
    "reference_doi": "10.1016/j.conengprac.2004.04.013",
    "rows": len(frame),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "prepared_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    "time_axis": "ordered_samples_with_derived_clock",
    "physical_sampling_interval": None,
    "delay_unit": "sample",
    "normalization": "source values are normalized; inverse scaling parameters are not published with this copy",
    "target_alignment": "source header states y was translated by 8 samples to compensate measurement delay",
    "real_plant_data": True,
    "derived_fields": ["sample_timestamp", "sample_index"],
}
(HERE / "dataset_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False, indent=2))
