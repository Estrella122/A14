# 核心 Skill Executor 目标架构

## 执行链

```text
TaskSpec
  → SkillResolution
  → minimal ExecutionPlan
  → Executor Registry
  → shared stage service
  → SkillExecutionResult
  → review/report readers
```

`ExecutionPlan` 只表达本次必须执行的数据依赖。Catalog 的文档依赖不再自动等同于算法执行依赖。标准化、清洗和建模 Executor 调用 `core.services.pipeline` 暴露的稳定 stage-service 入口，因此 Pipeline 与 Skill Runtime 复用同一份已验证实现。

## 统一结果契约

所有新 Executor 返回：`status`、`skill_id`、`capabilities_executed`、`facts`、`findings`、`hypotheses`、`limitations`、`metrics`、`artifacts`、`evidence`、`warnings`、`execution_trace`、`duration_ms`。

## Registry 状态

| Executor | 状态 | 责任 |
|---|---|---|
| industrial-analysis | executable | 独立统计分析 capability |
| standardization | executable | 场景识别、字段映射、单位与证据 |
| cleaning | executable | 时间对齐、缺失/异常治理与审计 |
| segmentation | reader_only | 本轮仍读取 cleaning service 已产生的分段证据 |
| modeling | executable | 冻结分区建模、基线对比与诊断 |
| optimization | executable/partial | 严格检查真实数据、目标、模型、边界和约束；缺失即 blocked |
| review | executable | 只评审既有结构化证据 |
| report | executable | 只格式化既有结果与 provenance |

## 模式策略

- `legacy`：保留旧 Pipeline bundle。
- `hybrid`：迁移能力优先使用 Executor；只有没有迁移节点时才允许旧 Pipeline fallback。
- `skill_runtime`：不调用 `rerun_pipeline()`；无 Executor 的能力返回 unavailable/reader_only。

## 最小 DAG

- 清洗：standardization → cleaning。
- 建模并比较基线：standardization → cleaning → modeling → review。
- 优化：optimization 前置条件检查；不隐式重跑模型。
- 报告：report 读取已有结果；不隐式执行任何分析。

## 迁移边界

动态分段目前仍由既有 `DataCleaningSelectionAgent` 提供，Registry 准确标记为 `reader_only`。优化器保留 Pipeline 的成熟真实数据搜索实现；独立 Executor 在输入合同完整前返回 partial/blocked，且禁止 synthetic fallback。
