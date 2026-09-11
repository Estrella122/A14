# 工业语义

只消费调用方已标准化的语义，例如 `temperature`、`pressure`、`flow`、`energy`、`power`、`fuel`、`vibration`、`current`、`quality`、`state`、`time`。

测量语义不代表设备归属。必须通过 `equipment_context` 和 `process_context` 绑定资产或工段。字段别名、点位 ID、设备关系、正常范围与工程限值属于宿主 Registry。语义为 `uncertain` 时，将依赖该语义的结论降级或跳过。
