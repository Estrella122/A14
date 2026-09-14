---
id: system_identification_trainer
name: 系统辨识训练
version: 1.0.0
category: modeling
description: 训练模型、拟合动态系统。复用结构搜索中真实拟合的系数并完成一次冻结测试评价，不重新进行阶次搜索。
triggers:
- 系统辨识训练
- 完成系统辨识
- 模型辨识
depends_on:
- arx_structure_order_selector
requires:
- ARX_SELECTED_STRUCTURE
- CLEANED_TEST
produces:
- MODEL_ARTIFACT
- MODEL_METRICS
executor:
  type: python
  module: core.skills.system-identification-trainer.executor
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
- 系统辨识
- 训练模型
- 完成辨识
- 模型辨识
---

# 能力说明
复用结构搜索中真实拟合的系数并完成一次冻结测试评价，不重新进行阶次搜索。

# 什么时候使用
用户请求系统辨识训练、模型辨识、训练模型、拟合动态系统，输入由已识别的数据场景 SceneContext 提供，不使用项目预设覆盖。

# 不应该什么时候使用
概念解释不计算；缺失声明输入或科学验证条件不足时返回不可用。

# 输入要求
ARX_SELECTED_STRUCTURE, CLEANED_TEST；timestamp、inputs、target、units、constraints 来自既有 ScenarioRepository。

# 参数说明
Skill 默认值 → SceneContext.default_parameters → 显式用户参数。实际值写入 audit。

# 执行逻辑
executor.py 适配现有 train 计算或产物读取；没有场景分支。模式为 execute，复用与计算必须区别记录。

# 输出要求
MODEL_ARTIFACT, MODEL_METRICS；统一 status/metrics/artifacts/evidence/warnings/suggested_next_skills。

# 证据边界
不插值制造目标，不使用未来化验或测试集选择参数，不降低既有质量门限。

# 失败条件
空输入、缺时间轴、有效样本不足或模型门禁未通过时明确报告，不填默认零。

# 后续 Skill 建议
以 depends_on 和产物决定下游，不依据场景名称选择算法。
