---
id: high_snr_dynamic_segment_extractor
name: 高信噪比动态段提取
version: 1.0.0
category: selection
description: 提取适合建模的动态工况段。提取高质量动态段，严格门槛不足时如实记录原算法候选降级。
triggers:
- 高质量动态段
- 高信噪比动态段
depends_on:
- steady_transient_state_detector
- signal_noise_ratio_estimator
requires:
- CLEANED_TRAIN
- SEGMENTATION_REPORT
- SNR_ESTIMATES
produces:
- MODELING_DATASET
- SELECTED_SEGMENTS
executor:
  type: python
  module: core.skills.high-snr-dynamic-segment-extractor.executor
  function: execute
execution_mode: execute
legacy_handler: selection
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
intent_terms:
- 工况段
- 动态段
- 动态数据
- 提取
---

# 能力说明
提取高质量动态段，严格门槛不足时如实记录原算法候选降级。

# 什么时候使用
找出适合建模的动态工况段，提取高信噪比动态数据。
用户请求高信噪比动态段提取，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
CLEANED_TRAIN, SEGMENTATION_REPORT, SNR_ESTIMATES；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
共用 algorithm_policy resolver：算法默认 → 兼容场景默认 → 数据场景 algorithm_profile → 校验后的显式请求。effective_parameters、来源和 policy hash 写入 audit。

# 执行逻辑
executor.py 适配现有 select_segments 计算或产物读取；没有场景分支。模式为 execute，复用与计算必须区别记录。

# 输出要求
MODELING_DATASET, SELECTED_SEGMENTS；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
