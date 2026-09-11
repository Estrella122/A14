# 通用分析 Workflow

1. 校验输入 contract，保留调用方提供的语义。
2. 画像并检查字段类型、样本量、时间范围和有效数值变量。
3. 评估缺失、异常、重复、时间顺序与数据质量。
4. 生成 analysis_plan，逐项验证 capability requires。
5. 只加载并执行 selected capability。
6. 输出四层结果、置信度、证据与 skipped 原因。
