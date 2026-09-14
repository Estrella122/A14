---
id: time_delay_estimator_compensator
name: 时滞估计与补偿
version: 1.0.0
category: selection
description: 估计输入变化到输出响应的时滞，计算延迟采样点并补偿。
triggers:
- 时滞
- 延迟
- 滞后
- 互相关
depends_on:
- segment_quality_scorer_ranker
requires:
- MODELING_DATASET
- FIELD_DICTIONARY
produces:
- TIME_DELAY_ESTIMATES
- DELAY_COMPENSATED_DATA
parameters:
- name: max_lag
  type: integer
  default: 60
  required: false
executor:
  type: python
  module: core.skills.time-delay-estimator-compensator.executor
  function: execute
execution_mode: execute
legacy_handler: lag
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
估计输入变化到输出响应的时滞，计算延迟采样点并补偿。

# 什么时候使用
用户希望对当前工业数据计算时滞估计与补偿的实际指标，或提出相关诊断问题。

# 不应该什么时候使用
纯概念介绍、未授权执行、输入缺失时不能运行；解释请求只读取本文。

# 输入要求
MODELING_DATASET, FIELD_DICTIONARY。项目预设场景不得替代数据识别场景。

# 参数说明
- default: 60
  name: max_lag
  required: false
  type: integer

# 执行逻辑
从字段字典确定输入输出，只使用训练数据估计非负因果滞后；复用 TimeDelayCapabilityExecutor。

# 输出要求
TIME_DELAY_ESTIMATES, DELAY_COMPENSATED_DATA，同时输出 metrics、artifacts、evidence、warnings。

# 证据边界
互相关并不证明因果；缺失角色、时间轴或有效配对样本时不可执行。

# 失败条件
缺失声明输入或算法有效样本不足时返回 unavailable；异常返回 failed 和具体原因。不得用 0 代替缺失指标。

# 后续 Skill 建议
由用户目标和质量证据决定下一步；建议不是自动执行授权。
