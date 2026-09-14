---
id: segment_quality_scorer_ranker
name: 动态段质量评分排序
version: 1.0.0
category: selection
description: 复用共享分段算法已经计算的窗口评分排序，不重复跑窗口计算。
triggers:
- 窗口排序
- 评分排序
depends_on:
- high_snr_dynamic_segment_extractor
requires:
- SEGMENTATION_REPORT
- SELECTED_SEGMENTS
produces:
- SEGMENT_RANKING
executor:
  type: python
  module: core.skills.segment-quality-scorer-ranker.executor
  function: execute
execution_mode: read
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
- 排序
- 评分
---

# 能力说明
复用共享分段算法已经计算的窗口评分排序，不重复跑窗口计算。

# 什么时候使用
用户请求动态段质量评分排序，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
SEGMENTATION_REPORT, SELECTED_SEGMENTS；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
Skill 默认值 → SceneContext.default_parameters → 显式用户参数。实际值写入 audit。

# 执行逻辑
executor.py 适配现有 rank 计算或产物读取；没有场景分支。模式为 read，复用与计算必须区别记录。

# 输出要求
SEGMENT_RANKING；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
