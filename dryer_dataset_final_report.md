# 工业干燥器数据最终报告

结论：Pipeline PARTIAL；Modeling PARTIAL；现有可执行数据仍为 SYNTHETIC。

[DAISY原始工业数据](https://homes.esat.kuleuven.be/~tokka/daisydata.html)已获取867×7数值及大学贡献者说明。10秒采样、有序索引、无空值和常数列。但是燃料流量不等于热风温度，风机转速不等于体积风量，湿球温度不等于湿度，原料水分不等于产品水分。单位和偏置未给，水分有负值，不能当成绝对质量百分比。该数据值得后续独立适配，但本阶段禁止改SceneContext/配置以替代原业务，因此不调用Runtime。

[咖啡公开实验](https://zenodo.org/records/16729583)下载了实际XLSX，只有各加热方式温度序列，缺连续产品水分及当前输入。[滤材实验](https://arxiv.org/html/2303.15570v1)是初末采样预测资料，不能充当连续工业时序。太阳能/鱼干燥来源保留待验证状态；全部候选及下载失败证据见总表。

## 既有合成数据数值证据（复用上阶段回执，本轮没有重跑）

- run_id：`scene_427eda599cfa`；skill_run_id：`skillrun_ac93e4b88600`；SHA256：`798660db9fa687d87c064c31dbeeb8bac98c68d529ae24d74cf6bd426d86cad1`
- 严格动态窗口：0；SNR汇总：24.452879071653605 dB（未标定二阶差分白噪声代理，保留null）。
- 候选：12；胜出：AR(1)，未隐藏AR-only。
- validation RMSE：0.033130798503325044；test RMSE：0.03980552463869197。
- test persistence RMSE：0.029539172224691445；relative improvement：-34.75504437263479%。
- test 10-step：{"horizon_samples": 10, "future_inputs": "observed historical inputs (conditional evaluation)", "metrics": {"n_samples": 144.0, "num_params": 2.0, "r2": 0.7591322686935522, "adjusted_r2": 0.7557157051289217, "rmse": 0.2600404436695548, "mae": 0.21026377544363364, "mse": 0.0676210323438589, "sse": 9.73742865751568, "fpe": 0.06952585015636197, "aic": -383.9124149566724, "bic": -377.9727883575204}, "persistence": {"n_samples": 144.0, "num_params": 1.0, "r2": 0.9190927362086333, "adjusted_r2": 0.9185229667453139, "rmse": 0.15071113631018326, "mae": 0.12783620213435556, "mse": 0.02271384660790664, "sse": 3.2707939115385565, "fpe": 0.023031522784241, "aic": -543.0084003133302, "bic": -540.0385870137542}}
- test free simulation：{"conditional_on_observed_inputs": true, "diverged": false, "metrics": {"n_samples": 154.0, "num_params": 2.0, "r2": -0.4422645714345699, "adjusted_r2": -0.46136741344032584, "rmse": 0.6200945486926053, "mae": 0.5104249548101851, "mse": 0.3845172493182858, "sse": 59.21565639501601, "fpe": 0.39463612430034595, "aic": -143.1880609209233, "bic": -137.11415571609604}}
- 稳定性：True；残差：{"acf_max_abs": 0.5522602797422981, "heuristic_95pct_bound": 0.15794130094897454, "whiteness_test": "not_performed; ACF is diagnostic only"}
- 时滞：{"output": "product_moisture", "input_count": 3, "max_lag": 24, "sampling_seconds": 10.0, "delays": [{"input": "hot_air_temperature", "output": "product_moisture", "delay_samples": 5, "correlation": -0.7586023831275089, "abs_correlation": 0.7586023831275089, "max_lag": 24, "overlap": 56, "boundary_hit": false, "method": "train_only_nonnegative_segment_correlation"}, {"input": "drying_air_flow", "output": "product_moisture", "delay_samples": 17, "correlation": -0.8980400151969418, "abs_correlation": 0.8980400151969418, "max_lag": 24, "overlap": 21, "boundary_hit": false, "method": "train_only_nonnegative_segment_correlation"}, {"input": "wet_feed_rate", "output": "product_moisture", "delay_samples": 17, "correlation": 0.9331305488840885, "abs_correlation": 0.9331305488840885, "max_lag": 24, "overlap": 21, "boundary_hit": false, "method": "train_only_nonnegative_segment_correlation"}]}
- 共线性：{"keep": ["drying_air_flow_aligned", "hot_air_temperature_aligned", "wet_feed_rate_aligned"], "drop": [], "reasons": [], "final_vif": [{"variable": "drying_air_flow_aligned", "vif": 1.245091969463567, "r_squared": 0.19684647839240488}, {"variable": "hot_air_temperature_aligned", "vif": 1.2216391725969573, "r_squared": 0.18142768959004263}, {"variable": "wet_feed_rate_aligned", "vif": 1.0527868020182751, "r_squared": 0.050140068166772855}]}

严格窗口0，只有降级候选72行。模型较persistence更差，不能称为业务有效。潜在原因包括激励弱/近积分动态/变量不足，但本次不作已证实因果结论。不试seed、不依test挑窗，不替换baseline。旧FROZEN_SPLIT声明guard57，而模型评估实际guard20，保留原回执差异，不把合成结果当严格工业验收。残差仅ACF启发式诊断，未做正式白噪声检验。
