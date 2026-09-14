# 三场景当前实现审计（修改前）

## 数据源与可运行状态

- blast_furnace：frontend/public/datasets/blast_furnace_real_720h.csv，720 小时真实高炉数据；上游 Mendeley 工作簿与因果派生工具位于 datasets/real_candidates/blast_furnace_mendeley。Si 化验非等间隔，缺失必须保留，不可插值造真值。
- debutanizer_column：标准化 raw_samples 小样本；本地历史 pipeline 的原始 CSV；datasets/public/debutanizer 元数据描述归一化公开基准，缺逆缩放和真实采样周期，不得套物理量边界伪造验证。验收优先取已有物理量 CSV，不临时生成 mock。
- industrial_dryer：演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv，已有 867 行合成验收数据；已有 pipeline 完成案例。必须明确它不是工厂实测。
- 三者都有 StandardizationAgent 字段接入与共享 pipeline 支持；第一阶段四个 MD Skill 仅用干燥器已有产物做过联合成功验收，尚未证明三个场景原始数据至诊断的同一 MD 主链。

## 字段与角色

### blast_furnace

采样：3600 秒；timestamp=timestamp；target=hot_metal_si。

| 字段 | 角色 | 单位 |
|---|---|---|
| timestamp | time | datetime |
| blast_flow_rate | manipulated | m3/min |
| hot_blast_pressure | state | kgf/cm2 |
| cold_blast_pressure | state | kgf/cm2 |
| cold_blast_temperature | state | degC |
| oxygen_flow_rate | manipulated | m3/h |
| total_pressure_drop | state | kgf/cm2 |
| upper_pressure_drop | state | kgf/cm2 |
| lower_pressure_drop | state | kgf/cm2 |
| top_gas_pressure | state | kgf/cm2 |
| hot_blast_temperature | manipulated | degC |
| top_gas_co2 | state | percent |
| top_gas_h2 | state | percent |
| top_gas_temp_1 | state | degC |
| top_gas_temp_2 | state | degC |
| top_gas_temp_3 | state | degC |
| top_gas_temp_4 | state | degC |
| peripheral_gas_temp_1 | state | degC |
| peripheral_gas_temp_2 | state | degC |
| peripheral_gas_temp_3 | state | degC |
| peripheral_gas_temp_4 | state | degC |
| peripheral_gas_temp_5 | state | degC |
| peripheral_gas_temp_6 | state | degC |
| peripheral_gas_temp_7 | state | degC |
| peripheral_gas_temp_8 | state | degC |
| peripheral_gas_temp_9 | state | degC |
| peripheral_gas_temp_10 | state | degC |
| ore_coke_ratio | manipulated | ratio |
| hot_metal_si | controlled | percent |
| lab_source_timestamp | identifier | string |
| lab_age_minutes | quality | min |
| lab_fresh | quality | boolean |
| blast_furnace_state | quality | string |
### debutanizer_column

采样：60 秒；timestamp=timestamp；target=bottom_butane_content。

| 字段 | 角色 | 单位 |
|---|---|---|
| timestamp | time | datetime |
| top_temperature | state | degC |
| top_pressure | state | Pa |
| reflux_flow | manipulated | t/h |
| next_process_flow | manipulated | t/h |
| tray6_temperature | state | degC |
| bottom_temperature_a | state | degC |
| bottom_temperature_b | state | degC |
| bottom_butane_content | controlled | percent |
| sample_index | identifier | string |
### industrial_dryer

采样：10 秒；timestamp=timestamp；target=product_moisture。

| 字段 | 角色 | 单位 |
|---|---|---|
| timestamp | time | datetime |
| hot_air_temperature | manipulated | degC |
| drying_air_flow | manipulated | Nm3/h |
| wet_feed_rate | manipulated | t/h |
| product_moisture | controlled | percent |
| product_temperature | controlled | degC |
| exhaust_humidity | controlled | percent |

## 共用算法、配置差异与领域约束

core/services/pipeline.py 的 _standardize/_clean/_model 共用；DataCleaningSelectionAgent 提供时间对齐、缺失异常、动态窗口和 SNR；segmentation_service 提供训练分区评分与选段；validated_modeling 提供时滞/共线性/ARX/独立验证。未发现三个场景各复制 clean/snr/vif/arx 的专属 pipeline。

配置差异已经在 template.json、fields.csv：字段别名、单位、角色、上下限、primary_output、采样周期、干燥器窗口长度及多输出名单。高炉真实约束包括化验 as-of 向后对齐与龄期；脱丁烷塔质量测量滞后；干燥器具有多个输出。不能机械删除这些差异。

通用核心 Skill 没有 if scenario == 分支；领域名称判断主要出现在标准化演示生成器、页面标签/3D 资产选择及测试工具。它们并不是重复辨识算法。现有 _effective_max_lag 读取测量延迟配置，属于参数适配，但分钟与采样点需由上下文明确换算。

## 本阶段可复用与缺口

- 第一阶段四项 MD 定义继续使用，不重做 Loader/Registry。
- SceneContext 应基于现有 ScenarioRepository 解析 timestamp/inputs/target/units/defaults，不读取 project UI scene 作为数据事实。
- 第二批八项可围绕现有清洗/分段/建模函数适配；动态检测、评分和优选共享 stage，必须记录哪些是计算、哪些复用。
- 当前 ModelingExecutor 会把时滞、VIF、阶次、拟合整段重跑；MD trainer 应复用已选阶次的拟合状态，避免再跑一遍上游。
- 前端已分离项目场景与数据场景；本阶段不改页面布局或场景状态绑定。
- 三场景最终状态需通过真实执行再决定；缺充分激励、有效样本或验证基准优势只能 PARTIAL/unavailable，不降低门槛。

## 后续数据查找核实

本次未找到合格的脱丁烷塔物理量 CSV；旧项目场景标为脱丁烷不代表数据实际属于脱丁烷。最终采用 raw_samples 归一化文件验证门禁，未将项目上下文作为数据来源证据。最终运行情况见 three_scene_migration_acceptance.md。
