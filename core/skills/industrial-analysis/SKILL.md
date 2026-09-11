---
name: industrial-analysis
description: 对调用方提供的标准字段、设备、工艺、质量与限值上下文执行可复用工业数据分析。用于画像、质量、趋势、时序、异常、相关、稳定性、能耗、设备健康、质量、工况、瓶颈、缺失和根因候选分析；不负责宿主工程代码、Pipeline、前端或 Registry 管理。
---

# Industrial Analysis

本 Skill 是项目 Agent 可独立加载的通用工业分析能力包。它不导入宿主工程模块，也不保存任何项目的场景注册表。

## 输入边界

接收数据或数据引用，以及调用方按需提供的 `scene`、`fields`、`equipment_context`、`process_context`、`units`、`engineering_limits`、`data_quality`、`mapping_confidence`、`scene_confidence`。这些上下文是证据，不是让 Skill 重新猜字段的提示。

解释标准语义时按需读取 [references/industrial-semantics.md](references/industrial-semantics.md)；涉及因果、故障或限值结论时读取 [references/evidence-rules.md](references/evidence-rules.md)；计算结论置信度时读取 [references/confidence-rules.md](references/confidence-rules.md)。

## 先规划后执行

任何分析前必须生成 `analysis_plan`。只选择 `requires` 已满足的 capability；请求了但证据不足的能力放入 `skipped_capabilities` 并给出原因。可调用 `scripts/build_analysis_plan.py` 生成确定性计划。

单项请求只加载对应 `capabilities/` 文件。综合分析读取 [workflows/generic-analysis.md](workflows/generic-analysis.md) 后动态加载多个 capability；`scene=unknown` 读取 [workflows/unknown-scene.md](workflows/unknown-scene.md)；验证或审计读取 [workflows/validation.md](workflows/validation.md)。完整路由表见 [references/capability-routing.md](references/capability-routing.md)。

## 输出边界

输出必须符合 `contracts/analysis-plan.schema.json` 与 `contracts/analysis-result.schema.json`。结果分为 `facts`、`findings`、`hypotheses`、`limitations`，重要结论携带 confidence 与 evidence。相关性不得写成因果；没有明确因果证据时，`ROOT_CAUSE_CANDIDATES` 只能输出候选因素。

未知场景允许数据画像、数据质量、趋势、相关、异常和缺失分析。除非调用方提供明确工业知识，否则禁止生成具体设备故障、具体工艺故障、确定根因或具体安全超限结论。
