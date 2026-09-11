# 字段统一 Agent 场景覆盖报告

验收日期：2026-09-11

## 当前 Registry 场景覆盖

场景 Registry 从 3 个扩充到 6 个。保留原有 `blast_furnace`、`debutanizer_column`、`industrial_dryer`，恢复 `steel_industry_energy`，新增 `thermal_power_boiler_long_tail` 和 `vapor_pressure_soft_sensor`。

新增场景继续使用 `template.json + fields.csv`，并声明 `required_features`、`supporting_features`、`conflicting_features`、`priority`、`minimum_evidence`、`minimum_confidence` 和 `minimum_required_field_coverage`。没有降低 Agent 的自动映射、复核、歧义和未知场景阈值。

## 新增和恢复场景

| 场景 | 状态 | 字段数 | 识别依据 |
|---|---|---:|---|
| `steel_industry_energy` | 恢复 | 11 | UCI 钢铁工业能源数据字段、单位及范围 |
| `thermal_power_boiler_long_tail` | 新增 | 31 | 论文 DOI `10.1038/s41597-025-05096-4` Table 1 的精确点位语义 |
| `vapor_pressure_soft_sensor` | 新增 | 31 | 用户真实文件中的温度、阀位、流量、压力、估计器和目标字段簇 |

## 点位语义字典

新增 `knowledge/point_semantics.csv`，字段为 `point_id`、`semantic_name`、`standard_field`、`measurement_type`、`unit`、`equipment`、`process_module`、`scene`、`confidence`、`source`。

西南锅炉数据的 30 个工业点位已经登记。例如：

| 点位 | 语义 | 设备 | 工艺模块 | 标准字段 |
|---|---|---|---|---|
| `PT_8313A.AV_0#` | 上炉膛压力 A | boiler | furnace | `upper_furnace_pressure_a` |
| `TE_8319A.AV_0#` | 省煤器出口左侧烟气温度 | economizer | flue_gas_system | `economizer_outlet_flue_gas_temperature_left` |
| `FT_8301.AV_0#` | 一次风机出口流量 | primary_fan | primary_air_system | `primary_fan_outlet_flow` |
| `TE_8332A.AV_0#` | 锅炉出口蒸汽温度 | boiler | main_steam_system | `boiler_outlet_steam_temperature` |

字典匹配必须同时满足精确点位 ID、场景和模板标准字段。未知 `TE/PT/FT` 只产生 `temperature/pressure/flow_rate` 候选，置信度为 0.35，并返回缺少设备、工艺模块、场景、单位和标准字段映射；不会自动匹配。

## unresolved 点位和缺失知识

本次西南数据的 30 个点位均在论文中找到精确语义，因此语义层没有 unresolved 点位。仍需现场确认以下工业知识：

- 论文 Table 1 没有列出全部工程单位。压力、流量、振动等单位目前根据量纲和数据尺度登记，投产前需要 DCS 点表确认。
- `PTCA_8324` 和 `PTCA_8322A` 的设备中文命名需要现场 P&ID 或设备位号表确认。
- `FT_8306A/B` 的原始工程单位未公开，Registry 使用 `source_scale`，禁止自动单位换算。
- 数据没有机组编号、锅炉额定负荷、燃料种类、启停状态和报警信息，不能据此完成工况或故障分类。
- 未知的新 TE/PT/FT 点位仍需点位表、设备层级、工艺模块和单位，不能靠前缀补全。

## 真实数据验收

| 文件 | 行×列 | 场景结果 | 状态/置信度 | 字段覆盖 | 数据决策 | 具体缺失知识 |
|---|---:|---|---|---:|---|---|
| `Steel_industry_data.csv` | 35,040×11 | `steel_industry_energy` | confirmed / 0.947 | 11/11 | ready | 无；模板与真实字段完整匹配 |
| `vapor-pressure.csv` | 18,743×30 | 候选 `vapor_pressure_soft_sensor` | uncertain / 0.928 | 30/30（29 matched，1 review） | review | 缺绝对时间戳；目标列缺失约 98.8%；flow/pres 通道单位、设备和数据来源元数据待确认 |
| `xinan_completed_data.csv` | 86,400×31 | `thermal_power_boiler_long_tail` | confirmed / 0.948 | 31/31 | ready | 部分工程单位仍需 DCS 点表确认 |
| `xinan_uncompleted_data.csv` | 86,400×31 | `thermal_power_boiler_long_tail` | confirmed / 0.948 | 31/31 | ready | `YJJWSLL.AV_0#` 有缺失记录；部分工程单位仍需 DCS 点表确认 |

`vapor-pressure.csv` 没有被强行确认。虽然字段簇明确对应新增模板，但缺失绝对时间戳和主要目标值，因此保留 `uncertain`。西南未完成数据的场景和字段语义可以确认，但缺失值处理仍由后续清洗模块负责。

## 修改前后覆盖率

| 指标 | 修改前 | 修改后 |
|---|---:|---:|
| Registry 场景数 | 3 | 6 |
| 四份真实数据有正确场景候选 | 0/4 | 4/4 |
| 四份真实数据 confirmed | 0/4 | 3/4 |
| 钢铁能耗字段语义覆盖 | 0/11 | 11/11 |
| 蒸气压字段语义覆盖 | 0/30 | 30/30 |
| 西南锅炉字段语义覆盖 | 1/31（仅时间） | 31/31 |

覆盖提升来自新增场景模板和有来源的点位知识。`uncertain`、`ambiguous` 和 `unknown` 的门槛未放宽。
