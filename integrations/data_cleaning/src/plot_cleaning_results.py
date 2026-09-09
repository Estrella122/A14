from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR_2 = ROOT / "data"
OUTPUT_ROOT = ROOT / "output"
OUTPUT_DIR_4 = OUTPUT_ROOT / "output（4）"
OUTPUT_DIR_5 = OUTPUT_ROOT / "output（5）"
RAW_PATH = INPUT_DIR_2 / "raw_timeseries.csv"
FIGURE_DIR = OUTPUT_DIR_5 / "figures"


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW_PATH, parse_dates=["timestamp"])
    cleaned = pd.read_csv(OUTPUT_DIR_4 / "cleaned_modeling_data.csv", parse_dates=["timestamp"])
    segments = pd.read_csv(OUTPUT_DIR_5 / "selected_dynamic_segments.csv")
    with (OUTPUT_DIR_5 / "quality_report.json").open(encoding="utf-8") as file:
        report = json.load(file)

    plot_before_after(raw, cleaned)
    plot_dynamic_segments(cleaned, segments)
    plot_quality_scores(report)
    print(f"可视化图片已输出: {FIGURE_DIR}")


def plot_before_after(raw: pd.DataFrame, cleaned: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    axes[0].plot(raw["timestamp"], raw["furnace_temp"], color="#b42318", linewidth=1)
    axes[0].set_title("Raw furnace temperature with missing values and anomalies")
    axes[0].set_ylabel("degC")
    axes[0].grid(alpha=0.25)

    axes[1].plot(cleaned["timestamp"], cleaned["furnace_temp"], color="#1f7a4d", linewidth=1)
    axes[1].set_title("Cleaned furnace temperature for modeling")
    axes[1].set_ylabel("degC")
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "before_after_furnace_temp.png", dpi=180)
    plt.close(fig)


def plot_dynamic_segments(cleaned: pd.DataFrame, segments: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(cleaned["timestamp"], cleaned["gas_flow"], color="#2f5f98", linewidth=1, label="gas_flow")

    top_segments = segments[segments["level"] == "优质动态段"].head(5)
    for _, row in top_segments.iterrows():
        ax.axvspan(pd.to_datetime(row["start_time"]), pd.to_datetime(row["end_time"]), color="#33a852", alpha=0.18)

    ax.set_title("Selected high-dynamic segments")
    ax.set_ylabel("Nm3/h")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "selected_dynamic_segments.png", dpi=180)
    plt.close(fig)


def plot_quality_scores(report: dict) -> None:
    scores = report["dimension_scores"]
    labels = list(scores.keys())
    values = [scores[label] for label in labels]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, values, color=["#2f5f98", "#1f7a4d", "#8a5a1f", "#9b3a4a", "#5a5f73"])
    ax.set_ylim(0, 105)
    ax.set_title(f"Data quality score: {report['overall_score']}")
    ax.set_ylabel("score")
    ax.grid(axis="y", alpha=0.25)

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "quality_scores.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
