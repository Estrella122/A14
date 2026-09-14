# 真实数据契约覆盖审计

基于 evidence-v1 Ground Truth；先标注源文档，再调用当前 Agent 对照。共 30 个候选来源记录、298 行真值（含缺失标准字段占位）。不是 30 份独立完整真实数据。

| 数据集 | required | MATCH | REVIEW | MISSING | NO_EQUIVALENT源列 | optional coverage | 分类 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed Mendeley derived 720h | 6 | 6 | 0 | 0 | 0 | 96.30% | CAN_RUN_NOW |
| Fortuna 文本镜像 | 9 | 0 | 8 | 1 | 0 | 0.00% | DATA_LIMITED |
| Coimbra 大学原始 MAT 包 | 9 | 0 | 8 | 1 | 0 | 0.00% | DATA_LIMITED |
| DC-dataset CSV 镜像 | 9 | 0 | 8 | 1 | 0 | 0.00% | DATA_LIMITED |
| LostRunes DB DATA-B | 9 | 2 | 4 | 3 | 5 | 0.00% | MIXED_LIMITATION |
| 本地 360 行 raw sample | 9 | 0 | 8 | 1 | 0 | 0.00% | DATA_LIMITED |
| Danny-Taehyun-Kim hybrid demo | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| LPG composition paper | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| Column flooding paper | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| Fortuna 其他复用仓库 | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| DAISY 96-016 industrial dryer | 7 | 0 | 3 | 4 | 4 | N/A（无样本） | DATA_LIMITED |
| Coffee microwave/oven temperature experiment | 7 | 0 | 1 | 6 | 0 | N/A（无样本） | DATA_LIMITED |
| Filter media drying moisture | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Solar multipurpose dryer | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Solar biomass fish dryer | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Industrial laundry exhaust | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| LARCO tumble dryers | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| WUR EHD dryer model | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Rotary potash dryer paper | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Batch rotary NARX paper | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Rotary nickel CO paper | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| 本地 867 行合成验收集 | 7 | 0 | 0 | 7 | 0 | N/A（无样本） | DATA_LIMITED |
| 本地 360 行 dryer raw sample | 7 | 0 | 0 | 7 | 0 | N/A（无样本） | DATA_LIMITED |
| StevenShaw98 Fortuna CSV | 9 | 0 | 8 | 1 | 0 | 0.00% | DATA_LIMITED |
| Basque refinery pentanes classification | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| UTP CRU debutanizer thesis | 9 | 0 | 9 | 0 | 0 | 0.00% | DATA_LIMITED |
| Tobacco Primary Processing data2 | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Solar dryer with thermal storage | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Kiln beech-chip residence time | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |
| Cassava dryer IoT design files | 7 | 0 | 7 | 0 | 0 | N/A（无样本） | DATA_LIMITED |

MATCH/REVIEW/MISSING 按 required canonical 去重，三者之和等于 required。NO_EQUIVALENT 按源列计数，不与 required 相加。覆盖率是可核验物理契约覆盖，不是模型字符串命中率。

没有原文件的来源均为 SOURCE_UNAVAILABLE：全契约待复核；不能断言该工厂没有这些传感器。合成和来源未核实记录仅作库存，排除真实字段评估与真实训练样本。

代表数据：高炉 6/6；LostRunes 脱丁烷塔 2/9（4 待复核、3 缺对应测点）；DAISY 干燥机 0/7（3 待复核、4 缺对应测点）。脱丁烷塔另有一个已确认时间列 Unnamed: 0 未被 Agent 接纳，因此准确分类为 MIXED_LIMITATION；这是元数据预处理缺口，不是可训练的通用空表头别名。

来源与逐字段证据见 real_field_ground_truth.json；契约原件为 integrations/standardization/standards/scenarios/*/{fields.csv,template.json}。未删 required、未改变单位或测点。
