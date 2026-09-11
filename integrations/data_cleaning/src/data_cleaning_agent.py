from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR_2 = ROOT / "data"
OUTPUT_ROOT = ROOT / "output"
OUTPUT_DIR_4 = OUTPUT_ROOT / "output（4）"
OUTPUT_DIR_5 = OUTPUT_ROOT / "output（5）"
RAW_PATH = INPUT_DIR_2 / "raw_timeseries.csv"
DATA_DICTIONARY_PATH = INPUT_DIR_2 / "data_dictionary.json"
SCENE_TEMPLATE_PATH = INPUT_DIR_2 / "scene_template.json"


VARIABLE_SPEC = {
    "furnace_temp": {
        "role": "output",
        "unit": "degC",
        "min": 700,
        "max": 1350,
        "max_step": 45,
    },
    "gas_flow": {
        "role": "input",
        "unit": "Nm3/h",
        "min": 1500,
        "max": 5200,
        "max_step": 450,
    },
    "air_flow": {
        "role": "input",
        "unit": "Nm3/h",
        "min": 4000,
        "max": 13000,
        "max_step": 900,
    },
    "valve_opening": {
        "role": "input",
        "unit": "%",
        "min": 0,
        "max": 100,
        "max_step": 20,
    },
    "slab_temp": {
        "role": "quality",
        "unit": "degC",
        "min": 650,
        "max": 1250,
        "max_step": 35,
    },
}


@dataclass
class SegmentScore:
    start_time: str
    end_time: str
    segment_score: float
    input_change_score: float
    output_response_score: float
    completeness_score: float
    anomaly_score: float
    smoothness_score: float
    level: str
    snr_db: float | None = None
    snr_method: str = "robust_second_difference_white_noise_proxy"


class DataCleaningSelectionAgent:
    def __init__(self, variable_spec: dict[str, dict], resample_rule: str = "10s", primary_output: str | None = None):
        self.variable_spec = variable_spec
        self.resample_rule = resample_rule
        self.primary_output = primary_output
        self.logs: list[str] = []
        self.anomaly_flags: pd.DataFrame | None = None
        self.raw_missing_rate: dict[str, float] = {}
        self.snr_evidence: list[dict] = []

    def run(self, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        aligned = self.align_timestamp(data)
        missing_processed = self.process_missing_values(aligned)
        cleaned = self.detect_and_repair_anomalies(missing_processed)
        selected_segments = self.select_dynamic_segments(cleaned)
        report = self.build_quality_report(aligned, cleaned, selected_segments)
        return cleaned, selected_segments, report

    def align_timestamp(self, data: pd.DataFrame) -> pd.DataFrame:
        frame = data.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp")
        numeric_columns = [column for column in self.variable_spec if column in frame.columns]
        if not numeric_columns:
            raise ValueError("数据中没有与变量规范匹配的数值过程字段。")
        ignored_columns = [column for column in frame.columns if column not in {"timestamp", *numeric_columns}]
        if ignored_columns:
            self.logs.append(f"重采样已排除非建模元数据字段：{', '.join(ignored_columns)}。")
        for column in numeric_columns:
            original = frame[column]
            converted = pd.to_numeric(original, errors="coerce")
            invalid_count = int((original.notna() & converted.isna()).sum())
            if invalid_count:
                self.logs.append(f"{column} 有 {invalid_count} 个非数值内容，已转为缺失值并进入缺失修复。")
            if converted.notna().sum() == 0:
                raise ValueError(f"过程字段 {column} 没有可解析的数值，无法执行重采样。")
            frame[column] = converted
        frame = frame[["timestamp", *numeric_columns]]
        frame = frame.set_index("timestamp")
        aligned = frame.resample(self.resample_rule, closed="right", label="right").mean()
        self.logs.append(f"时间戳已按 {self.resample_rule} 统一重采样。")
        return aligned

    def process_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        frame = data.copy()
        for column in frame.columns:
            missing_rate = float(frame[column].isna().mean())
            self.raw_missing_rate[column] = round(missing_rate, 4)

            if self.variable_spec.get(column, {}).get("role") in {"output", "quality"}:
                action = "缺失输出保留为空，不作为训练或评估真值"
            else:
                frame[column] = frame[column].ffill(limit=6)
                action = "仅向前填充最多6个采样点；不读取未来值"

            self.logs.append(f"{column} 缺失率 {missing_rate:.2%}，处理策略：{action}。")
        return frame

    def detect_and_repair_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        frame = data.copy()
        flags = pd.DataFrame(False, index=frame.index, columns=frame.columns)

        for column, spec in self.variable_spec.items():
            if column not in frame.columns:
                continue

            series = frame[column]
            range_flag = (series < spec["min"]) | (series > spec["max"])
            step_flag = series.diff().abs() > spec["max_step"]

            rolling_median = series.rolling(window=9, center=False, min_periods=3).median()
            local_deviation = (series - rolling_median).abs()
            mad = local_deviation.rolling(window=9, center=False, min_periods=3).median()
            spike_flag = local_deviation > (6 * mad.replace(0, np.nan))
            spike_flag = spike_flag.fillna(False)

            flags[column] = range_flag | step_flag | spike_flag
            anomaly_count = int(flags[column].sum())
            if anomaly_count:
                frame.loc[flags[column], column] = np.nan
                if spec.get("role") not in {"output", "quality"}:
                    frame[column] = frame[column].ffill(limit=6)
            self.logs.append(f"{column} 检测到 {anomaly_count} 个异常点，已标记；输入有限前向填充，输出不伪造真值。")

        self.anomaly_flags = flags
        return frame

    def select_dynamic_segments(self, data: pd.DataFrame) -> pd.DataFrame:
        window = 30
        step = 15
        input_columns = [
            name for name, spec in self.variable_spec.items()
            if spec["role"] == "input" and name in data.columns
        ]
        output_columns = [
            name for name, spec in self.variable_spec.items()
            if spec["role"] in {"output", "quality"} and name in data.columns
        ]

        primary_output = self.primary_output if self.primary_output in output_columns else None
        if primary_output is None and len(output_columns) == 1:
            primary_output = output_columns[0]
        if primary_output:
            output_columns = [primary_output]
        segments: list[SegmentScore] = []
        for start in range(0, max(len(data) - window + 1, 0), step):
            chunk = data.iloc[start:start + window]
            input_change = self._relative_range_score(chunk[input_columns], scale=1500)
            output_response = self._relative_range_score(chunk[output_columns], scale=1800)
            completeness = 100 * (1 - chunk.isna().mean().mean())
            anomaly_rate = 0.0
            if self.anomaly_flags is not None:
                anomaly_rate = float(self.anomaly_flags.iloc[start:start + window].mean().mean())
            anomaly_score = 100 * (1 - anomaly_rate)
            smoothness = self._smoothness_score(chunk)

            score = (
                0.35 * input_change
                + 0.25 * output_response
                + 0.20 * completeness
                + 0.10 * anomaly_score
                + 0.10 * smoothness
            )
            for col in dict.fromkeys(input_columns + output_columns):
                detail = self.snr_details(chunk[col])
                self.snr_evidence.append({"start_time": str(chunk.index[0]), "end_time": str(chunk.index[-1]),
                                          "variable": col, **detail})
            input_snr = [self.estimate_snr(chunk[c]) for c in input_columns]
            output_snr = [self.estimate_snr(chunk[c]) for c in output_columns]
            finite_input = [v for v in input_snr if v is not None]
            finite_output = [v for v in output_snr if v is not None]
            snr = min(max(finite_input), min(finite_output)) if finite_input and len(finite_output) == len(output_columns) and finite_output else None
            level = "优质动态段" if score >= 80 and snr is not None and snr >= 10 else "可用数据段" if score >= 60 else "不推荐"
            segments.append(
                SegmentScore(
                    start_time=str(chunk.index[0]),
                    end_time=str(chunk.index[-1]),
                    segment_score=round(float(score), 2),
                    input_change_score=round(float(input_change), 2),
                    output_response_score=round(float(output_response), 2),
                    completeness_score=round(float(completeness), 2),
                    anomaly_score=round(float(anomaly_score), 2),
                    smoothness_score=round(float(smoothness), 2),
                    level=level,
                    snr_db=round(snr, 3) if snr is not None else None,
                )
            )

        result = pd.DataFrame([segment.__dict__ for segment in segments])
        if not result.empty:
            result = result.sort_values("segment_score", ascending=False).reset_index(drop=True)
        self.logs.append("已完成滑动窗口动态评分和高动态数据段筛选。")
        return result

    def build_quality_report(
        self,
        aligned: pd.DataFrame,
        cleaned: pd.DataFrame,
        selected_segments: pd.DataFrame,
    ) -> dict:
        mean_missing = float(np.mean(list(self.raw_missing_rate.values()))) if self.raw_missing_rate else 0
        completeness = max(0, 100 * (1 - mean_missing))

        anomaly_rate = 0.0
        if self.anomaly_flags is not None:
            anomaly_rate = float(self.anomaly_flags.mean().mean())
        validity = max(0, 100 * (1 - anomaly_rate))

        smoothness = self._smoothness_score(cleaned)
        dynamic = float(selected_segments["segment_score"].head(5).mean()) if not selected_segments.empty else 0
        consistency = self._timestamp_consistency_score(aligned)

        overall = (
            0.25 * completeness
            + 0.20 * validity
            + 0.15 * smoothness
            + 0.30 * dynamic
            + 0.10 * consistency
        )

        return {
            "module": "DataCleaningSelectionAgent",
            "overall_score": round(float(overall), 2),
            "dimension_scores": {
                "completeness": round(float(completeness), 2),
                "validity": round(float(validity), 2),
                "smoothness": round(float(smoothness), 2),
                "dynamic": round(float(dynamic), 2),
                "consistency": round(float(consistency), 2),
            },
            "missing_rate": self.raw_missing_rate,
            "selected_segment_count": int((selected_segments["level"] == "优质动态段").sum())
            if not selected_segments.empty
            else 0,
            "logs": self.logs,
        }

    @staticmethod
    def estimate_snr(series: pd.Series) -> float | None:
        return DataCleaningSelectionAgent.snr_details(series)["snr_db"]

    @staticmethod
    def snr_details(series: pd.Series) -> dict:
        values = pd.to_numeric(series, errors="coerce")
        delta2 = values.diff().diff().dropna()
        detail = {"snr_db": None, "signal_power": None, "noise_power": None,
                  "valid_samples": int(values.notna().sum()), "calibrated": False,
                  "method": "robust_second_difference_white_noise_proxy"}
        if len(delta2) < 12 or values.notna().sum() < 15:
            return detail
        sigma = float((delta2 - delta2.median()).abs().median()) / 0.67448975 / np.sqrt(6)
        total = float(values.var(ddof=0))
        if total <= 1e-12 or sigma <= 1e-12:
            return detail
        signal = max(total - sigma ** 2, 1e-12)
        detail.update(signal_power=signal, noise_power=sigma ** 2,
                      snr_db=float(10 * np.log10(signal / (sigma ** 2))))
        return detail


    def _relative_range_score(self, data: pd.DataFrame, scale: float) -> float:
        if data.empty:
            return 0.0
        scores = []
        for column in data.columns:
            mean_abs = data[column].abs().mean()
            if mean_abs == 0:
                scores.append(0)
                continue
            relative_range = (data[column].max() - data[column].min()) / mean_abs
            scores.append(min(100, relative_range * scale))
        return float(np.mean(scores))

    def _smoothness_score(self, data: pd.DataFrame) -> float:
        if data.empty:
            return 0.0
        scores = []
        for column in data.columns:
            diff = data[column].diff().abs()
            baseline = data[column].abs().mean() + 1e-9
            roughness = diff.mean() / baseline
            scores.append(max(0, 100 - roughness * 600))
        return float(np.mean(scores))

    def _timestamp_consistency_score(self, data: pd.DataFrame) -> float:
        if len(data.index) < 3:
            return 100.0
        intervals = data.index.to_series().diff().dropna().dt.total_seconds()
        return 100.0 if intervals.nunique() == 1 else max(0, 100 - intervals.std())


def generate_sample_data(path: Path) -> None:
    rng = np.random.default_rng(14)
    timestamps = pd.date_range("2026-08-02 08:00:00", periods=720, freq="10s")
    t = np.arange(len(timestamps))

    gas_flow = 3200 + 350 * np.sin(t / 45) + rng.normal(0, 45, len(t))
    air_flow = 8500 + 700 * np.sin(t / 50 + 0.4) + rng.normal(0, 80, len(t))
    valve_opening = 62 + 8 * np.sin(t / 60) + rng.normal(0, 1.2, len(t))
    furnace_temp = 1060 + 0.035 * (gas_flow - 3200) + 0.012 * (air_flow - 8500)
    furnace_temp += 18 * np.sin((t - 9) / 65) + rng.normal(0, 4, len(t))
    slab_temp = 910 + 0.55 * (furnace_temp - 1060) + rng.normal(0, 5, len(t))

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "furnace_temp": furnace_temp,
            "gas_flow": gas_flow,
            "air_flow": air_flow,
            "valve_opening": valve_opening,
            "slab_temp": slab_temp,
        }
    )

    missing_rows = rng.choice(frame.index, size=35, replace=False)
    frame.loc[missing_rows[:10], "gas_flow"] = np.nan
    frame.loc[missing_rows[10:20], "air_flow"] = np.nan
    frame.loc[missing_rows[20:], "furnace_temp"] = np.nan

    frame.loc[120, "furnace_temp"] = 1600
    frame.loc[250, "gas_flow"] = 900
    frame.loc[380, "air_flow"] = 16000
    frame.loc[500:540, "valve_opening"] = 64.0
    frame.loc[600, "slab_temp"] = 1450

    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def write_sample_interface_files() -> None:
    if not DATA_DICTIONARY_PATH.exists():
        with DATA_DICTIONARY_PATH.open("w", encoding="utf-8") as file:
            json.dump(VARIABLE_SPEC, file, ensure_ascii=False, indent=2)

    if not SCENE_TEMPLATE_PATH.exists():
        template = {
            "scene_name": "steel_reheating_furnace",
            "scene_label": "钢厂加热炉",
            "sampling_rule": "10s",
            "time_column": "timestamp",
            "description": "用于演示流程工业时序数据清洗、优质动态段筛选和建模数据交付。",
            "required_files": [
                "raw_timeseries.csv",
                "data_dictionary.json",
                "scene_template.json",
            ],
        }
        with SCENE_TEMPLATE_PATH.open("w", encoding="utf-8") as file:
            json.dump(template, file, ensure_ascii=False, indent=2)


def load_variable_spec() -> dict[str, dict]:
    if DATA_DICTIONARY_PATH.exists():
        with DATA_DICTIONARY_PATH.open(encoding="utf-8") as file:
            return json.load(file)
    return VARIABLE_SPEC


def main() -> None:
    INPUT_DIR_2.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR_4.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR_5.mkdir(parents=True, exist_ok=True)
    write_sample_interface_files()
    if not RAW_PATH.exists():
        generate_sample_data(RAW_PATH)

    raw = pd.read_csv(RAW_PATH)
    agent = DataCleaningSelectionAgent(load_variable_spec())
    cleaned, selected_segments, report = agent.run(raw)

    cleaned.to_csv(OUTPUT_DIR_4 / "cleaned_modeling_data.csv")
    selected_segments.to_csv(OUTPUT_DIR_4 / "selected_dynamic_segments.csv", index=False)
    with (OUTPUT_DIR_4 / "quality_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    selected_segments.to_csv(OUTPUT_DIR_5 / "selected_dynamic_segments.csv", index=False)
    with (OUTPUT_DIR_5 / "quality_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print("数据清洗与优质数据筛选完成")
    print(f"总体质量评分: {report['overall_score']}")
    print(f"优质动态段数量: {report['selected_segment_count']}")
    print(f"4号建模产物目录: {OUTPUT_DIR_4}")
    print(f"5号展示产物目录: {OUTPUT_DIR_5}")


if __name__ == "__main__":
    main()
