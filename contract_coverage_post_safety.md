# 安全修复后契约覆盖

GT 保持 evidence-v1、不重新让模型生成标签。matched_required 是有来源证据的物理匹配，不是自动接受数；最后单列当前实际自动接受，防止把候选当契约通过。

| 数据集 | required | GT MATCH | GT REVIEW | GT MISSING | NO_EQUIVALENT | 物理coverage | 实际自动required | 分类 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed Mendeley derived 720h | 6 | 6 | 0 | 0 | 0 | 6/6 | 6 | CAN_RUN_NOW |
| Fortuna 文本镜像 | 9 | 0 | 8 | 1 | 0 | 0/9 | 0 | DATA_LIMITED |
| Coimbra 大学原始 MAT 包 | 9 | 0 | 8 | 1 | 0 | 0/9 | 0 | DATA_LIMITED |
| DC-dataset CSV 镜像 | 9 | 0 | 8 | 1 | 0 | 0/9 | 0 | DATA_LIMITED |
| LostRunes DB DATA-B | 9 | 2 | 4 | 3 | 5 | 2/9 | 1 | MIXED_LIMITATION |
| 本地 360 行 raw sample | 9 | 0 | 8 | 1 | 0 | 0/9 | 1 | DATA_LIMITED |
| Danny-Taehyun-Kim hybrid demo | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| LPG composition paper | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| Column flooding paper | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| Fortuna 其他复用仓库 | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| DAISY 96-016 industrial dryer | 7 | 0 | 3 | 4 | 4 | 0/7 | 0 | DATA_LIMITED |
| Coffee microwave/oven temperature experiment | 7 | 0 | 1 | 6 | 0 | 0/7 | 0 | DATA_LIMITED |
| Filter media drying moisture | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Solar multipurpose dryer | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Solar biomass fish dryer | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Industrial laundry exhaust | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| LARCO tumble dryers | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| WUR EHD dryer model | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Rotary potash dryer paper | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Batch rotary NARX paper | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Rotary nickel CO paper | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| 本地 867 行合成验收集 | 7 | 0 | 0 | 7 | 0 | 0/7 | 7 | DATA_LIMITED |
| 本地 360 行 dryer raw sample | 7 | 0 | 0 | 7 | 0 | 0/7 | 7 | DATA_LIMITED |
| StevenShaw98 Fortuna CSV | 9 | 0 | 8 | 1 | 0 | 0/9 | 0 | DATA_LIMITED |
| Basque refinery pentanes classification | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| UTP CRU debutanizer thesis | 9 | 0 | 9 | 0 | 0 | 0/9 | 0 | DATA_LIMITED |
| Tobacco Primary Processing data2 | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Solar dryer with thermal storage | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Kiln beech-chip residence time | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |
| Cassava dryer IoT design files | 7 | 0 | 7 | 0 | 0 | 0/7 | 0 | DATA_LIMITED |

高炉 6/6；LostRunes 2/9 可信物理字段但实际自动 required=1（时间元数据未接入），4 待复核、3 缺对应变量；DAISY 0/7，3 待复核、4 缺对应变量。未取得源文件的论文条目是 SOURCE_UNAVAILABLE，而不是断言该设备不存在传感器。

安全收紧不改变物理存在性。Fortuna 匿名 normalized 列不再因 alias 虚增 coverage。完整来源、列、单位、采样、来源可信程度沿用 real_field_ground_truth.json 的 source_metadata；合成与未核实源不进入真实数值验收。
