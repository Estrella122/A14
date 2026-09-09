#!/usr/bin/env python3
"""Plot helpers for the member-4 modeling workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


def _load_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _write_svg(path: str | Path, width: int, height: int, body: str) -> str:
    path = Path(path).with_suffix(".svg")
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="#ffffff"/>\n'
        f"{body}\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "middle") -> str:
    safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" text-anchor="{anchor}" fill="#222">{safe}</text>'


def _normalize(values: Iterable[float], low: float, high: float) -> List[float]:
    vals = [float(v) for v in values]
    if not vals:
        return []
    vmin, vmax = min(vals), max(vals)
    if abs(vmax - vmin) < 1e-12:
        return [(low + high) / 2 for _ in vals]
    return [high - (v - vmin) / (vmax - vmin) * (high - low) for v in vals]


def _color_for_corr(value: float) -> str:
    value = max(-1.0, min(1.0, float(value)))
    if value >= 0:
        r, g, b = 220, int(245 - 110 * value), int(245 - 145 * value)
    else:
        r, g, b = int(245 + 10 * value), int(245 + 65 * value), 230
    return f"#{r:02x}{g:02x}{b:02x}"


def plot_delay_bar(delay_csv: str | Path, output_path: str | Path) -> Optional[str]:
    data = pd.read_csv(delay_csv)
    if data.empty:
        return None
    try:
        plt = _load_matplotlib()
    except ModuleNotFoundError:
        width, height = 820, 430
        left, right, top, bottom = 80, 30, 50, 95
        vals = data["delay_samples"].astype(float).tolist()
        max_abs = max(max(abs(v) for v in vals), 1.0)
        zero_y = top + (height - top - bottom) / 2
        scale = (height - top - bottom) / 2 / max_abs
        bar_w = (width - left - right) / max(len(vals), 1) * 0.65
        step = (width - left - right) / max(len(vals), 1)
        body = [_svg_text(width / 2, 28, "Estimated input-output delay", 18)]
        body.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="#333" stroke-width="1"/>')
        for i, (_, row) in enumerate(data.iterrows()):
            x = left + step * i + step / 2 - bar_w / 2
            v = float(row["delay_samples"])
            y = zero_y - max(v, 0) * scale
            h = abs(v) * scale
            if v < 0:
                y = zero_y
            color = "#2E86AB" if v >= 0 else "#C05746"
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}"/>')
            body.append(_svg_text(x + bar_w / 2, height - 55, row["input"], 11))
            body.append(_svg_text(x + bar_w / 2, y - 5 if v >= 0 else y + h + 15, f"{v:.0f}", 11))
        body.append(_svg_text(22, height / 2, "Delay", 12, "start"))
        return _write_svg(output_path, width, height, "\n".join(body))

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    colors = ["#2E86AB" if v >= 0 else "#C05746" for v in data["delay_samples"]]
    ax.bar(data["input"].astype(str), data["delay_samples"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Estimated input-output delay")
    ax.set_ylabel("Delay (samples)")
    ax.set_xlabel("Input variable")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)


def plot_correlation_heatmap(corr_csv: str | Path, output_path: str | Path) -> Optional[str]:
    corr = pd.read_csv(corr_csv, index_col=0)
    if corr.empty:
        return None
    try:
        plt = _load_matplotlib()
    except ModuleNotFoundError:
        n = len(corr.columns)
        cell = 52
        left, top = 150, 65
        width = left + cell * n + 40
        height = top + cell * n + 135
        body = [_svg_text(width / 2, 30, "Variable correlation matrix", 18)]
        for i, row_name in enumerate(corr.index):
            body.append(_svg_text(left - 10, top + i * cell + cell * 0.6, row_name, 10, "end"))
        for j, col_name in enumerate(corr.columns):
            body.append(_svg_text(left + j * cell + cell / 2, top + cell * n + 25, col_name, 10))
        for i, row_name in enumerate(corr.index):
            for j, col_name in enumerate(corr.columns):
                val = float(corr.loc[row_name, col_name])
                x, y = left + j * cell, top + i * cell
                body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{_color_for_corr(val)}" stroke="#fff"/>')
                body.append(_svg_text(x + cell / 2, y + cell * 0.58, f"{val:.2f}", 10))
        return _write_svg(output_path, width, height, "\n".join(body))

    fig, ax = plt.subplots(figsize=(7, 6), dpi=150)
    im = ax.imshow(corr.to_numpy(dtype=float), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=35, ha="right")
    ax.set_yticklabels(corr.index)
    ax.set_title("Variable correlation matrix")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)


def plot_prediction_and_residual(prediction_csv: str | Path, output_path: str | Path) -> Optional[str]:
    data = pd.read_csv(prediction_csv)
    if data.empty:
        return None
    try:
        plt = _load_matplotlib()
    except ModuleNotFoundError:
        width, height = 900, 560
        left, right = 70, 25
        top1, bot1 = 55, 245
        top2, bot2 = 330, 510
        n = len(data)
        xs = np.linspace(left, width - right, n)
        y_true = _normalize(data["y_true"], top1, bot1)
        y_pred = _normalize(data["y_pred"], top1, bot1)
        residual = _normalize(data["residual"], top2, bot2)
        true_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, y_true))
        pred_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, y_pred))
        res_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, residual))
        body = [
            _svg_text(width / 2, 28, "ARX model fit and residual", 18),
            f'<polyline points="{true_points}" fill="none" stroke="#234F68" stroke-width="1.5"/>',
            f'<polyline points="{pred_points}" fill="none" stroke="#E09F3E" stroke-width="1.3"/>',
            _svg_text(120, 48, "True", 12, "start"),
            '<line x1="85" y1="44" x2="115" y2="44" stroke="#234F68" stroke-width="2"/>',
            _svg_text(210, 48, "Predicted", 12, "start"),
            '<line x1="165" y1="44" x2="205" y2="44" stroke="#E09F3E" stroke-width="2"/>',
            f'<line x1="{left}" y1="{bot1}" x2="{width-right}" y2="{bot1}" stroke="#aaa"/>',
            _svg_text(width / 2, 302, "Residual sequence", 15),
            f'<polyline points="{res_points}" fill="none" stroke="#8A4F7D" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{bot2}" x2="{width-right}" y2="{bot2}" stroke="#aaa"/>',
        ]
        return _write_svg(output_path, width, height, "\n".join(body))

    x = np.arange(len(data))
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), dpi=150, sharex=True)
    axes[0].plot(x, data["y_true"], label="True", color="#234F68", linewidth=1.4)
    axes[0].plot(x, data["y_pred"], label="Predicted", color="#E09F3E", linewidth=1.2)
    axes[0].set_title("ARX model fit")
    axes[0].set_ylabel("Output")
    axes[0].legend(loc="best")

    axes[1].plot(x, data["residual"], color="#8A4F7D", linewidth=1.0)
    axes[1].axhline(0, color="#333333", linewidth=0.8)
    axes[1].set_title("Residual sequence")
    axes[1].set_xlabel("Sample")
    axes[1].set_ylabel("Residual")
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)


def plot_residual_acf(acf_csv: str | Path, output_path: str | Path) -> Optional[str]:
    data = pd.read_csv(acf_csv)
    if data.empty:
        return None
    try:
        plt = _load_matplotlib()
    except ModuleNotFoundError:
        width, height = 720, 390
        left, right, top, bottom = 70, 25, 50, 70
        vals = data["autocorrelation"].astype(float).tolist()
        max_abs = max(max(abs(v) for v in vals), 1.0)
        zero_y = top + (height - top - bottom) / 2
        scale = (height - top - bottom) / 2 / max_abs
        step = (width - left - right) / max(len(vals), 1)
        bar_w = step * 0.6
        body = [_svg_text(width / 2, 28, "Residual autocorrelation", 18)]
        body.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="#333"/>')
        for i, (_, row) in enumerate(data.iterrows()):
            v = float(row["autocorrelation"])
            x = left + step * i + step / 2 - bar_w / 2
            y = zero_y - max(v, 0) * scale
            h = abs(v) * scale
            if v < 0:
                y = zero_y
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#4B7F52"/>')
        return _write_svg(output_path, width, height, "\n".join(body))

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.bar(data["lag"], data["autocorrelation"], color="#4B7F52")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.axhline(0.2, color="#888888", linestyle="--", linewidth=0.8)
    ax.axhline(-0.2, color="#888888", linestyle="--", linewidth=0.8)
    ax.set_title("Residual autocorrelation")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Autocorrelation")
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)


def plot_metric_comparison(comparison_csv: str | Path, output_path: str | Path) -> Optional[str]:
    data = pd.read_csv(comparison_csv)
    metrics = [m for m in ["r2", "adjusted_r2", "rmse", "mae", "fpe"] if m in data.columns]
    if data.empty or not metrics:
        return None
    try:
        plt = _load_matplotlib()
    except ModuleNotFoundError:
        width, height = 980, 420
        left, right, top, bottom = 70, 30, 55, 80
        panel_w = (width - left - right) / len(metrics)
        body = [_svg_text(width / 2, 30, "Modeling metric comparison", 18)]
        colors = ["#2E86AB", "#E09F3E", "#4B7F52"]
        for mi, metric in enumerate(metrics):
            x0 = left + mi * panel_w
            vals = data[metric].astype(float).tolist()
            ymax = max(max(vals), 1e-9)
            bar_w = panel_w / (len(vals) + 1) * 0.55
            body.append(_svg_text(x0 + panel_w / 2, 58, metric.upper(), 12))
            body.append(f'<line x1="{x0+15:.1f}" y1="{height-bottom}" x2="{x0+panel_w-15:.1f}" y2="{height-bottom}" stroke="#aaa"/>')
            for i, (_, row) in enumerate(data.iterrows()):
                v = float(row[metric])
                h = max(0.0, v / ymax) * (height - top - bottom - 40)
                x = x0 + panel_w * (i + 1) / (len(vals) + 1) - bar_w / 2
                y = height - bottom - h
                body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[i % len(colors)]}"/>')
                body.append(_svg_text(x + bar_w / 2, y - 5, f"{v:.3g}", 10))
                body.append(_svg_text(x + bar_w / 2, height - bottom + 16, str(row["dataset"]).replace("_", " "), 9))
        return _write_svg(output_path, width, height, "\n".join(body))

    fig, axes = plt.subplots(1, len(metrics), figsize=(3.2 * len(metrics), 4), dpi=150)
    if len(metrics) == 1:
        axes = [axes]
    for ax, metric in zip(axes, metrics):
        ax.bar(data["dataset"], data[metric], color=["#2E86AB", "#E09F3E", "#4B7F52"][: len(data)])
        ax.set_title(metric.upper())
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return str(output_path)
