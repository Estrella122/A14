---
id: engineering_visualization_builder
name: 工程可视化生成
version: 1.1.0
category: delivery
description: 将当前数据展示为图形可视化、图表和曲线。支持画图、能给我图形可视化吗、能耗趋势图、预测对比和寻优得分图。
intent_terms: [图形, 图表, 可视化, 曲线, 画, plot, chart]
triggers: [可视化, 图表, 曲线, 画图]
depends_on: []
requires: []
produces: [ENGINEERING_PLOTS]
parameters: []
executor:
  type: python
  module: core.skills.engineering-visualization-builder.executor
  function: execute
execution_mode: execute
workflow_scope: delivery
scope: PROJECT
quality_gates: [real_series_only, finite_values_only, source_required]
---

# 能力说明
将当前真实数据绘制为图形可视化、图表和曲线。普通画图请求默认展示目标字段及数值字段趋势；明确要求预测或寻优时读取相应产物。

# 什么时候使用
用户说“能给我图形可视化吗”“帮我画个图”“展示当前数据曲线”时，使用当前已关联数据生成图表，不要求用户使用固定命令。

# 不应该什么时候使用
纯概念解释、否定、引用和假设不执行。画图不授权重新训练、清洗或寻优。

# 输入要求
当前运行的标准化 CSV、预测结果或寻优记录至少一种可读。执行器按请求检查输入；没有真实数值时明确返回不可用。无需已有模型即可画数据趋势。

# 执行逻辑
沿用 VisualizationExecutor，读取有限列和行数、按原始索引等距抽样绘图。缺失值断开曲线，不平滑、不插值。记录字段、单位、源文件、源行数与显示点数。

# 输出要求
ENGINEERING_PLOTS，包含可下载 SVG 和图表清单，供聊天内联展示；保留来源和抽样限制。

# 证据边界
趋势图不等同于故障诊断；抽样可能遗漏局部极值。未生成的图不得声称已完成。
