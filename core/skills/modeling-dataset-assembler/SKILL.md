---
id: modeling_dataset_assembler
name: 建模数据集组装
version: 1.0.0
category: modeling
description: 按已选窗口及变量建议组装模型训练视图，不重新清洗和估计。
triggers:
- 组装训练数据
- 建模数据集
depends_on:
- collinearity_detector_reducer
requires:
- MODELING_DATASET
- COLLINEARITY_REPORT
- TIME_DELAY_ESTIMATES
produces:
- MODEL_READY_DATASET
executor:
  type: python
  module: core.skills.modeling-dataset-assembler.executor
  function: execute
execution_mode: read
legacy_handler: modeling
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
- 组装
- 建模数据集
---

# 能力说明
按已选窗口及变量建议组装模型训练视图，不重新清洗和估计。

# 什么时候使用
用户请求建模数据集组装，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
MODELING_DATASET, COLLINEARITY_REPORT, TIME_DELAY_ESTIMATES；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
Skill 默认值 → SceneContext.default_parameters → 显式用户参数。实际值写入 audit。

# 执行逻辑
executor.py 适配现有 assemble 计算或产物读取；没有场景分支。模式为 read，复用与计算必须区别记录。

# 输出要求
MODEL_READY_DATASET；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
