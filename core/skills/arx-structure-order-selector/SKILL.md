---
id: arx_structure_order_selector
name: ARX 结构阶次选择
version: 1.0.0
category: modeling
description: 判断数据是否适合 ARX 建模，比较结构阶次、正则化候选和 AR 基线，以验证集 BIC 选择结构。
triggers:
- arx
- 阶次
- 结构选择
- bic
depends_on:
- signal_noise_ratio_estimator
- modeling_dataset_assembler
requires:
- MODEL_READY_DATASET
- CLEANED_VALIDATION
- TIME_DELAY_ESTIMATES
- COLLINEARITY_REPORT
- SNR_ESTIMATES
produces:
- ARX_ORDER_SEARCH
- ARX_SELECTED_STRUCTURE
parameters: []
executor:
  type: python
  module: core.skills.arx-structure-order-selector.executor
  function: execute
execution_mode: execute
legacy_handler: modeling
workflow_scope: workflow
scope: PROJECT
evidence:
- method
- sample_count
- assumptions
quality_gates:
- missing_input_must_fail_explicitly
- missing_evidence_must_not_be_replaced_by_zero
suggested_next_skills: []
---

# 能力说明
判断数据是否适合 ARX 建模，比较结构阶次、正则化候选和 AR 基线，以验证集 BIC 选择结构。

# 什么时候使用
用户希望对当前工业数据计算ARX 结构阶次选择的实际指标，或提出相关诊断问题。

# 不应该什么时候使用
纯概念介绍、未授权执行、输入缺失时不能运行；解释请求只读取本文。

# 输入要求
MODELING_DATASET, CLEANED_VALIDATION, TIME_DELAY_ESTIMATES, COLLINEARITY_REPORT, SNR_ESTIMATES。项目预设场景不得替代数据识别场景。

# 参数说明
复用现有算法固定搜索空间，不增加另一套默认值。

# 执行逻辑
读取上游时滞、共线性建议和 SNR 证据，调用共享 search_structure_orders；训练拟合并在共同验证目标上比较。

# 输出要求
ARX_ORDER_SEARCH, ARX_SELECTED_STRUCTURE，同时输出 metrics、artifacts、evidence、warnings。

# 证据边界
不读取测试集；不重跑清洗、时滞或共线性；候选失败如实记录，不宣称生产可用。

# 失败条件
缺失声明输入或算法有效样本不足时返回 unavailable；异常返回 failed 和具体原因。不得用 0 代替缺失指标。

# 后续 Skill 建议
由用户目标和质量证据决定下一步；建议不是自动执行授权。
