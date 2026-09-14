---
id: missing_anomaly_cleaner
name: 缺失与异常清洗
version: 1.0.0
category: data
description: 检查数据质量，按角色处理缺失和异常；不填造输出真值。
triggers:
- 清洗
- 缺失
- 数据质量
depends_on:
- time_axis_alignment_resampler
requires:
- ALIGNED_TRAIN
- ALIGNED_VALIDATION
- ALIGNED_TEST
- FIELD_DICTIONARY
produces:
- CLEANED_TRAIN
- CLEANED_VALIDATION
- CLEANED_TEST
executor:
  type: python
  module: core.skills.missing-anomaly-cleaner.executor
  function: execute
execution_mode: execute
legacy_handler: cleaning
workflow_scope: workflow
scope: PROJECT
parameters: []
evidence:
- method
- input_refs
quality_gates:
- preserve_missing_target
- training_only_preprocessing
- no_duplicate_stage_execution
suggested_next_skills: []
---

# 能力说明
检查数据质量，按角色处理缺失和异常；不填造输出真值。

# 什么时候使用
用户请求缺失与异常清洗，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
ALIGNED_TRAIN, ALIGNED_VALIDATION, ALIGNED_TEST, FIELD_DICTIONARY；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
Skill 默认值 → SceneContext.default_parameters → 显式用户参数。实际值写入 audit。

# 执行逻辑
executor.py 适配现有 clean 计算或产物读取；没有场景分支。模式为 execute，复用与计算必须区别记录。

# 输出要求
CLEANED_TRAIN, CLEANED_VALIDATION, CLEANED_TEST；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
