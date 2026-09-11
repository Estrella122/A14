from __future__ import annotations

import numpy as np
import pandas as pd


def generate_demo(scenario_id: str, rows: int = 240, seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    time = pd.date_range("2026-01-01 08:00:00", periods=rows, freq="min")
    x = np.arange(rows)
    if scenario_id == "steel_industry_energy":
        usage = 24 + 10 * np.sin(x / 36) + rng.normal(0, 1.2, rows)
        return pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=rows, freq="15min").strftime("%d/%m/%Y %H:%M"),
                "Usage_kWh": usage.clip(0),
                "Lagging_Current_Reactive.Power_kVarh": (usage * 0.45 + rng.normal(0, .5, rows)).clip(0),
                "Leading_Current_Reactive_Power_kVarh": (usage * 0.08 + rng.normal(0, .15, rows)).clip(0),
                "CO2(tCO2)": (usage * 0.00045).clip(0),
                "Lagging_Current_Power_Factor": (92 + rng.normal(0, 2, rows)).clip(0, 100),
                "Leading_Current_Power_Factor": (98 + rng.normal(0, 1, rows)).clip(0, 100),
                "NSM": (x * 900) % 86400,
                "WeekStatus": ["Weekday"] * rows,
                "Day_of_week": ["Monday"] * rows,
                "Load_Type": ["Medium_Load"] * rows,
            }
        )
    if scenario_id == "debutanizer_column":
        time = pd.date_range("2026-07-01 00:00:00", periods=rows, freq="min")
        reflux = 82 + 4.8 * np.sin(x / 85) + rng.normal(0, 0.45, rows)
        product = 112 + 6.2 * np.sin(x / 110 + 0.7) + rng.normal(0, 0.55, rows)
        pressure_kpa = 620 + 24 * np.sin(x / 140 + 0.3) + rng.normal(0, 2.2, rows)
        top_temp = 54 + 0.018 * pressure_kpa - 0.026 * reflux + rng.normal(0, 0.12, rows)
        tray6 = 75 + 0.085 * product - 0.031 * reflux + rng.normal(0, 0.16, rows)
        bottom_a = 102 + 0.048 * product + 0.010 * pressure_kpa + rng.normal(0, 0.18, rows)
        bottom_b = bottom_a + 1.2 * np.sin(x / 70) + rng.normal(0, 0.12, rows)
        lag = min(max(30, rows // 45), 75)
        lagged_reflux = pd.Series(reflux).shift(lag).bfill().to_numpy()
        lagged_product = pd.Series(product).shift(lag).bfill().to_numpy()
        lagged_tray6 = pd.Series(tray6).shift(max(1, lag - 8)).bfill().to_numpy()
        c4 = (
            1.18
            - 0.0105 * (lagged_reflux - 82)
            + 0.0072 * (lagged_product - 112)
            + 0.018 * (lagged_tray6 - 84)
            + 0.10 * np.sin(x / 180)
            + rng.normal(0, 0.018, rows)
        )
        return pd.DataFrame(
            {
                "采集时间": time,
                "塔顶温度(℃)": top_temp.clip(20, 120),
                "塔顶压力(kPa)": pressure_kpa.clip(0, 2000),
                "回流流量(t/h)": reflux.clip(0, 500),
                "后续流程流量(t/h)": product.clip(0, 500),
                "第六塔板温度(℃)": tray6.clip(20, 150),
                "塔底温度A(℃)": bottom_a.clip(50, 180),
                "塔底温度B(℃)": bottom_b.clip(50, 180),
                "C4浓度(%)": c4.clip(0, 10),
            }
        )
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
