---
id: collinearity_detector_reducer
name: 共线性诊断与消减
version: 1.0.0
category: selection
description: 检查共线性、输入变量冗余和方差膨胀因子 VIF，建议保留或剔除输入。
triggers:
- 共线性
- 共线
- vif
- 冗余变量
depends_on:
- time_delay_estimator_compensator
requires:
- DELAY_COMPENSATED_DATA
- TIME_DELAY_ESTIMATES
produces:
- COLLINEARITY_REPORT
parameters:
- name: corr_threshold
  type: float
  default: 0.9
  required: false
- name: vif_threshold
  type: float
  default: 10.0
  required: false
executor:
  type: python
  module: core.skills.collinearity-detector-reducer.executor
  function: execute
execution_mode: execute
legacy_handler: collinearity
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
检查共线性、输入变量冗余和方差膨胀因子 VIF，建议保留或剔除输入。

# 什么时候使用
用户希望对当前工业数据计算共线性诊断与消减的实际指标，或提出相关诊断问题。

# 不应该什么时候使用
纯概念介绍、未授权执行、输入缺失时不能运行；解释请求只读取本文。

# 输入要求
DELAY_COMPENSATED_DATA, TIME_DELAY_ESTIMATES。项目预设场景不得替代数据识别场景。

# 参数说明
- default: 0.9
  name: corr_threshold
  required: false
  type: float
- default: 10.0
  name: vif_threshold
  required: false
  type: float

# 执行逻辑
使用时滞补偿后的完整训练行调用 correlation_matrix、compute_vif、recommend_variables。

# 输出要求
COLLINEARITY_REPORT，同时输出 metrics、artifacts、evidence、warnings。

# 证据边界
不跨数据缺口插值；不修改原始数据；共线性诊断不证明因果。

# 失败条件
缺失声明输入或算法有效样本不足时返回 unavailable；异常返回 failed 和具体原因。不得用 0 代替缺失指标。

# 后续 Skill 建议
由用户目标和质量证据决定下一步；建议不是自动执行授权。
