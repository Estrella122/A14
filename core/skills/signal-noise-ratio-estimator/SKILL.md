---
id: signal_noise_ratio_estimator
name: 信噪比估计
version: 1.0.0
category: selection
description: 对当前数据估计信噪比和噪声水平。量化有用信号功率与噪声功率，回答噪声是否过大。
triggers:
- 信噪比
- snr
- 噪声比
- 噪声水平
depends_on:
- missing_anomaly_cleaner
requires:
- CLEANED_TRAIN
produces:
- SNR_ESTIMATES
parameters:
- name: columns
  type: list
  required: false
executor:
  type: python
  module: core.skills.signal-noise-ratio-estimator.executor
  function: execute
execution_mode: execute
legacy_handler: selection
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
对当前数据估计信噪比和噪声水平。量化有用信号功率与噪声功率，回答噪声是否过大。

# 什么时候使用
用户希望对当前工业数据计算信噪比估计的实际指标，或提出相关诊断问题。

# 不应该什么时候使用
纯概念介绍、未授权执行、输入缺失时不能运行；解释请求只读取本文。

# 输入要求
CLEANED_TRAIN。项目预设场景不得替代数据识别场景。

# 参数说明
- name: columns
  required: false
  type: list

# 执行逻辑
输入为清洗后的训练时序。对每个数值字段调用 snr_details 的稳健二阶差分估计，不重新清洗或重新分段。

# 输出要求
SNR_ESTIMATES，同时输出 metrics、artifacts、evidence、warnings。

# 证据边界
常量和不足 15 点的样本返回 null；白噪声代理不等于仪表标定。

# 失败条件
缺失声明输入或算法有效样本不足时返回 unavailable；异常返回 failed 和具体原因。不得用 0 代替缺失指标。

# 后续 Skill 建议
由用户目标和质量证据决定下一步；建议不是自动执行授权。
