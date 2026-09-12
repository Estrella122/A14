# 核心 Skill Executor 验收

## 任务路由验收

| 输入 | Task kind | Mode | Executor DAG | 结果 |
|---|---|---|---|---|
| 帮我检查这份数据并清洗缺失值。 | execute_pipeline | execute | standardization → cleaning | 不含 modeling/optimization |
| 用这份数据建一个预测模型，并告诉我是否优于基线。 | execute_pipeline | execute | standardization → cleaning → modeling → review | modeling 返回 persistence baseline comparison |
| 直接优化运行参数。 | execute_pipeline | execute | optimization | 缺 objective/model/bounds/constraints/real_data 时 blocked；无 synthetic fallback |
| 给我生成这次分析报告。 | artifact_request | execute | report | 只消费既有结果，不重跑 Pipeline |

## 真实数据验证

使用当前本地真实运行 `20260912_125352_10174e21` 的 `vapor-pressure.csv` 源文件，直接调用 Standardization Executor：

- status：success
- detected scene：`vapor_pressure_soft_sensor`
- 执行入口：`StandardizationAgent.standardize`
- scenario_id：`auto`
- artifacts：3
- 未进入 cleaning/modeling/optimization

对同一 snapshot 调用 Report Executor：status=success，生成 1 个 Markdown 产物，trace 标记 `recomputed=false`。

对缺少前置合同的优化请求调用 Optimization Executor：status=blocked，证据记录 `synthetic_fallback=false`。

## 自动化验证

- Django 全量：177 tests，全部通过，1 skipped。
- 核心迁移专项：27 个新增边界/Registry/DAG/结果协议测试。
- Skill routing + loader + 核心迁移：57 tests，全部通过。
- `py_compile`：通过。
- `git diff --check`：通过。

覆盖内容包括四个验收请求、最小 DAG、Executor Registry 状态、统一结果 schema、缺输入阻断、报告不重算、评审不重算、无 synthetic fallback、DataFrame 输入、既有同义表达/知识解释/上下文门禁及 legacy 兼容测试。

## 最终能力矩阵

| 能力 | Planner | Reader | Executor | Pipeline Fallback | Production Ready |
|---|---:|---:|---:|---:|---:|
| industrial-analysis | 是 | 是 | 是 | 否 | 是 |
| standardization | 是 | 是 | 是 | hybrid 仅无迁移节点时 | 是 |
| data cleaning | 是 | 是 | 是 | hybrid 仅无迁移节点时 | 是 |
| dynamic/operating segment | 是 | 是 | reader-only | 是 | 否 |
| modeling | 是 | 是 | 是 | hybrid 仅无迁移节点时 | 条件就绪（依赖冻结 split artifacts） |
| optimization | 是 | 是 | partial/blocked | legacy 保留 | 否 |
| review | 是 | 是 | 是 | 否 | 是 |
| report | 是 | 是 | 是 | 否 | 是 |

## 剩余风险

1. 清洗和动态分段在底层历史 Agent 中仍有代码级耦合；纯清洗已通过开关禁用分段，但独立 segmentation Executor 仍需后续拆分。
2. 独立 modeling Executor 依赖冻结的 split artifacts；缺失时会 blocked/failed，不会自行伪造分区。
3. optimization 在独立合同完整前不会执行；这是有意的安全门禁，不应改成 synthetic fallback。
