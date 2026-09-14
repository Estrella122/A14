# 字段匹配安全剩余边界

- 本轮只给debutanizer_column启用physical_semantics；不宣称其他场景已获得同样的物理身份校验。
- 名称解析是保守词法规则；未知位置、未明确单位、未注明A/B通道、流向未知进入review。新设备词汇仍需维护，无法凭列名证明仪表来源真实性。
- 明确alias、点位字典及人工override仍是受信任来源；错误人工别名/错误人工覆盖需要独立治理。本次两个反例没有被加入alias。
- 字段模型本身仍可能召回错误候选；已阻断自动接受，保留候选给人复核。没有重训模型或通过降低阈值隐藏错误。
- 现有场景识别可能使用review候选作召回证据，但required/标准化只接受matched。本轮未改变识别算法。
- 脱丁烷物理数据与可信inverse metadata仍缺失。固定请求为UNAVAILABLE，12数值Executor没有执行；Modeling NOT_EXECUTED，第2项PARTIAL。
- 完整后端回归的阶段预测测试有3个断言失败（同一测试的三个子用例）：期望cleaning/selection/modeling，实际evidence_only。隔离复现时字段匹配器调用次数0。本次不修改Planner来修复该独立问题；详见验收报告及日志。
