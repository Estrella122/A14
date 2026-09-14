# 字段匹配现状（修复前审计）

范围：`integrations/standardization/standard_agent/engine.py::_match_one/map_columns`；本轮只启用脱丁烷物理语义门禁。

1. 原始列通过 split_header_unit 拆分名称/单位；normalize_name 规范大小写、分隔符。
2. 优先点位语义字典（限定场景），其次明确标准名/fields.csv aliases、learned_alias、已批准web alias。别名通常score=1。
3. 未命中则以 semantic_core 查唯一候选，vendor_core_alias=0.96。该规则会去除部分设备噪声/数字，不能独立证明测点相同。
4. 再按 0.58×fuzzy WRatio + 0.42×字符n-gram余弦取最高候选；这里的semantic不是LLM判断。
5. 若score低于auto_threshold（默认0.82），HybridSemanticModel提供前两名。超过模型accept_threshold（默认0.54）后，margin>=0.10用0.82+0.18×预测分数，命名trained_model_auto；否则0.64+0.20×分数。没有逐项物理身份判定。opaque点号另受字典约束。
6. 初始分数低于review_threshold（默认0.62）清空candidate。
7. 候选确定后检查单位一致/可转换/冲突；冲突将分数上限压至0.58。未声明单位此前不是拒绝原因。
8. 数值前2000行检查类型、物理范围、缺失等。score乘0.72+0.28×plausibility；高缺失再降分。范围合理不能证明位置等价。
9. 修复前最终只按有无candidate及confidence>=0.82分为matched/review/unmapped，随后处理重复列和字段相关性。没有独立quantity、physical role、measurement location、flow direction门禁。
10. 因此两个不同物理测点候选仍可自动接受：Reboiler o/l Temp→bottom_temperature_b，约0.879；Feed Flow to DB→next_process_flow，约0.883。二者来自trained_model_auto，不是明确alias。

修复后的流程及审计字段见 field_matching_safety_design.md；原始置信度保留，不能用高分覆盖物理冲突。
