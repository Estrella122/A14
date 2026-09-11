# 训练数据包说明

## 文件

- `field_semantics_all.csv`：全部字段语义样本。
- `field_semantics_train.csv`：训练集。
- `field_semantics_validation.csv`：验证集。
- `field_semantics_test.csv`：测试集。
- `scenario_intents.csv`：自然语言场景意图样本。
- `multi_scenario_dictionary.csv`：钢铁高炉、炼油脱丁烷精馏塔和工业干燥器三场景统一数据字典。
- `raw_samples/`：每个场景 360 行原始异构字段 CSV。
- `manifest.json`：数据版本、场景和样本数量。

## 字段语义数据列

- `text`：模型输入的原始字段名称或命名变体。
- `scenario_id`：所属场景。
- `standard_name`：目标标准字段；`__irrelevant__` 表示无关字段。
- `relevance`：`required`、`useful` 或 `irrelevant`。
- `role`：变量角色。
- `unit`：目标标准单位。
- `source`：样本生成或采集来源。
- `group_id`：原始别名组标识；同组增强变体只能进入同一个数据切分。
- `split`：训练、验证或测试。

此数据包是工程首版的可运行种子数据，不应被表述为已覆盖所有真实工业标签。真实项目需由各场景工艺人员持续补充并审核。
