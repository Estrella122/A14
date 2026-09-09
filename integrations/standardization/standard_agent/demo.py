from __future__ import annotations

import numpy as np
import pandas as pd


def generate_demo(scenario_id: str, rows: int = 240, seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    time = pd.date_range("2026-01-01 08:00:00", periods=rows, freq="min")
    x = np.arange(rows)
    if scenario_id == "steel_reheating_furnace":
        gas = 24500 + 900 * np.sin(x / 34) + rng.normal(0, 120, rows)
        air = gas * 1.78 + rng.normal(0, 240, rows)
        zone1 = 930 + 25 * np.sin(x / 42) + rng.normal(0, 2, rows)
        zone2 = 1120 + 20 * np.sin(x / 48) + rng.normal(0, 2, rows)
        zone3_c = 1240 + 14 * np.sin(x / 55) + rng.normal(0, 1.5, rows)
        return pd.DataFrame(
            {
                "采集时间": time,
                "GAS_FLOW_NM3H": gas,
                "助燃风量[Nm3/h]": air,
                "ZONE1_TEMP_C": zone1,
                "二段炉温(℃)": zone2,
                "均热段温度(°F)": zone3_c * 9 / 5 + 32,
                "WALKING_BEAM_SPEED": 1.2 + rng.normal(0, 0.01, rows),
                "入炉温度": 170 + rng.normal(0, 4, rows),
                "SLAB_OUT_TEMP_C": 1160 + 10 * np.sin(x / 65) + rng.normal(0, 1, rows),
                "炉压(kPa)": 0.008 + rng.normal(0, 0.001, rows),
                "O2_PERCENT": 3 + rng.normal(0, 0.08, rows),
                "板坯厚度": 220,
                "THROUGHPUT": 170 + rng.normal(0, 2, rows),
                "厂商临时标签": rng.integers(0, 3, rows),
            }
        )
    if scenario_id == "distillation_column":
        return pd.DataFrame(
            {
                "记录时间": pd.date_range("2026-01-01 08:00:00", periods=rows, freq="30s"),
                "回流量(t/h)": 82 + 3 * np.sin(x / 30) + rng.normal(0, 0.3, rows),
                "再沸器蒸汽": 68 + 2 * np.sin(x / 38) + rng.normal(0, 0.25, rows),
                "塔进料": 120 + rng.normal(0, 0.8, rows),
                "顶温(℃)": 78.5 + rng.normal(0, 0.08, rows),
                "釜温": 112 + rng.normal(0, 0.1, rows),
                "塔顶压力(kPa)": 135 + rng.normal(0, 0.4, rows),
                "TOP_PURITY": 98.2 + rng.normal(0, 0.08, rows),
                "釜液位": 52 + rng.normal(0, 0.5, rows),
            }
        )
    if scenario_id == "thermal_power_boiler":
        load = 620 + 45 * np.sin(x / 55) + rng.normal(0, 3, rows)
        coal = 0.48 * load + rng.normal(0, 2, rows)
        return pd.DataFrame(
            {
                "采集时间": pd.date_range("2026-01-01", periods=rows, freq="30s"),
                "UNIT_LOAD": load,
                "总煤量(t/h)": coal,
                "一次风流量": coal * 2100 + rng.normal(0, 5000, rows),
                "二次风流量": coal * 3200 + rng.normal(0, 8000, rows),
                "锅炉给水": 1.02 * load + rng.normal(0, 4, rows),
                "主汽压(MPa)": 24.2 + rng.normal(0, 0.08, rows),
                "MAIN_STEAM_TEMP": 568 + rng.normal(0, 1.2, rows),
                "主汽流量": load * 2.9 + rng.normal(0, 8, rows),
                "炉膛负压(Pa)": -85 + rng.normal(0, 5, rows),
                "空预器入口氧量[%]": 3.2 + rng.normal(0, 0.12, rows),
                "厂商状态字": rng.integers(0, 4, rows),
            }
        )
    if scenario_id == "cement_rotary_kiln":
        raw = 365 + 15 * np.sin(x / 70) + rng.normal(0, 1, rows)
        return pd.DataFrame(
            {
                "记录时间": pd.date_range("2026-01-01", periods=rows, freq="min"),
                "RAW_FEED": raw,
                "窑头煤量": 24 + 0.03 * raw + rng.normal(0, 0.2, rows),
                "分解炉煤量": 31 + rng.normal(0, 0.25, rows),
                "KILN_SPEED": 3.6 + rng.normal(0, 0.03, rows),
                "窑尾烟室温度(℃)": 1080 + rng.normal(0, 6, rows),
                "窑头罩温度": 1380 + rng.normal(0, 8, rows),
                "C1出口温度": 325 + rng.normal(0, 2, rows),
                "窑尾氧量[%]": 2.4 + rng.normal(0, 0.1, rows),
                "ID_FAN_SPEED": 860 + rng.normal(0, 5, rows),
                "主传电流": 620 + rng.normal(0, 8, rows),
                "FREE_LIME": 1.25 + rng.normal(0, 0.08, rows),
                "化验备注": ["正常"] * rows,
            }
        )
    if scenario_id == "wastewater_aeration":
        inflow = 4200 + 240 * np.sin(x / 65) + rng.normal(0, 30, rows)
        return pd.DataFrame(
            {
                "时间": pd.date_range("2026-01-01", periods=rows, freq="5min"),
                "IN_FLOW": inflow,
                "进水化学需氧量": 310 + rng.normal(0, 12, rows),
                "进水NH3-N": 38 + rng.normal(0, 2, rows),
                "鼓风量": 15500 + 0.7 * inflow + rng.normal(0, 120, rows),
                "BLOWER_FREQ": 43 + rng.normal(0, 0.8, rows),
                "曝气池DO[mg/L]": 2.1 + rng.normal(0, 0.12, rows),
                "MLSS": 3600 + rng.normal(0, 80, rows),
                "PH值": 7.2 + rng.normal(0, 0.05, rows),
                "池温(℃)": 24 + rng.normal(0, 0.2, rows),
                "OUT_COD": 31 + rng.normal(0, 2, rows),
                "EFFLUENT_NH3N": 2.8 + rng.normal(0, 0.25, rows),
                "RAS_FLOW": 1800 + rng.normal(0, 30, rows),
                "班组备注": ["A班"] * rows,
            }
        )
    raise ValueError(f"没有场景 {scenario_id} 的演示数据。")
