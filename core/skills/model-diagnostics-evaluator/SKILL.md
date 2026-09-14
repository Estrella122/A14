---
id: model_diagnostics_evaluator
name: 模型诊断评估
version: 1.0.0
category: modeling
description: 检查残差自相关、白噪声证据和模型可靠性。评估数据质量与 ARX 适用性。检查验证和测试证据、稳定性、残差和持久性基准。
triggers:
- 模型诊断
- 是否可靠
- 数据质量
depends_on:
- system_identification_trainer
requires:
- MODEL_ARTIFACT
- MODEL_METRICS
produces:
- MODEL_DIAGNOSTICS
executor:
  type: python
  module: core.skills.model-diagnostics-evaluator.executor
  function: execute
execution_mode: execute
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
- 残差
- 自相关
- 诊断
- 可靠
- 质量
- 适用性
---

# 能力说明
评估数据质量与 ARX 适用性。检查验证和测试证据、稳定性、残差和持久性基准。

# 什么时候使用
查看残差自相关检验和白噪声证据；已有 ACF 不等于完成正式白噪声检验。
用户请求模型诊断评估，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
MODEL_ARTIFACT, MODEL_METRICS；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
Skill 默认值 → SceneContext.default_parameters → 显式用户参数。实际值写入 audit。

# 执行逻辑
executor.py 适配现有 diagnose 计算或产物读取；没有场景分支。模式为 execute，复用与计算必须区别记录。

# 输出要求
MODEL_DIAGNOSTICS；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
