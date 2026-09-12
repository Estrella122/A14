# Executor Runtime Artifact 迁移报告

## GitHub 同步与重复检查

实施前已执行 `git fetch origin`。本地 `main` 与 `origin/main` 均为 `427dc0bfab7cf51707d9a694f5245e723f69c54b`，没有待合并的远端提交，也没有 checkout/rebase 冲突。

远端新代码已经包含两部分可复用实现：

- `427dc0b` 已提供真实 `SegmentationExecutor` / `OptimizationExecutor` 和一个最小版 `RuntimeArtifactRef`。本次保留两个 Executor 的现有算法调用，扩展原有 artifact 模块，没有创建第二套系统。
- `4dec3d6` 已提供 simulation、visualization、experiment、supervision Executor。本次只通过公共结果工厂统一返回合同，没有重复实现这些 Executor。

因此本次改动是对现有 Runtime 的收敛，不是与 GitHub 新代码并行的重复实现。

## 修改前 artifact 传递

| Executor | 输入来源 | 输出表示 | 主要问题 |
|---|---|---|---|
| Standardization | `source_csv` 字符串或 DataFrame | report 中的路径字典 | 无类型、hash 和 schema 版本 |
| Cleaning | snapshot `standardized_csv` 或内存 state | `train.csv` / `validation.csv` / `test.csv` / split 路径 | 新旧 snapshot 的 artifact key 不一致 |
| Segmentation | state DataFrame，snapshot 字典/split | 最小 `RuntimeArtifactRef` | 只有 run/skill/type/path，无正式 registry 合同 |
| Modeling | `modeling_csv` 或 state | report 中路径 | 需要了解 `03_cleaning` 兼容布局 |
| Optimization | 大量 state/request 内对象 | report 路径 | planner 无法在执行前区分 artifact 缺失和策略合同缺失 |

## RuntimeArtifactRef 与 ArtifactResolver

`RuntimeArtifactRef` 现包含：`artifact_id`、`artifact_type`、`producer`、`run_id`、`stage`、`path`、`version`、`schema_version`、`content_hash`、`metadata`、`created_at`、`source_execution_id`。文件注册时计算 SHA-256。

`RuntimeArtifactResolver` 是唯一的查找和兼容层：

1. 先读当前 Runtime state 中的类型化引用。
2. 再读 pipeline snapshot 的 `artifact_registry`。
3. 将旧 snapshot 的 `source_csv`、`segments_csv`、`summary_json` 等 key 映射成标准 artifact type。
4. 对旧 snapshot 未登记但真实存在的 train/validation/test 分区，仅在 Resolver 内使用中央兼容布局。Executor 不再猜测阶段目录。
5. readiness 只把真实存在的文件视为可用，避免 stale path 被误报为 ready。
6. 旧 service 仍需要阶段目录时，由 Resolver 的 `compatibility_workspace()` 统一物化，而不是在 Executor 内散落拼路径。

Pipeline 每次写 `snapshot.json` 时同步生成 `artifact_registry`；字段字典也作为显式 artifact 持久化。

## Executor artifact 合同

| Executor | requires | produces |
|---|---|---|
| Standardization | `SOURCE_DATA` | `STANDARDIZED_DATA`, `FIELD_DICTIONARY` |
| Cleaning | `STANDARDIZED_DATA`, `FIELD_DICTIONARY` | `CLEANED_TRAIN`, `CLEANED_VALIDATION`, `CLEANED_TEST`, `FROZEN_SPLIT`, `MODELING_DATASET` |
| Segmentation | `CLEANED_TRAIN`, `FROZEN_SPLIT`, `FIELD_DICTIONARY` | `SEGMENTATION_REPORT`, `SELECTED_SEGMENTS`, `SEGMENT_SCORES`, `SNR_ESTIMATES`, `MODELING_DATASET` |
| Modeling | `MODELING_DATASET`, `CLEANED_VALIDATION`, `CLEANED_TEST`, `FROZEN_SPLIT`, `FIELD_DICTIONARY` | `MODEL_ARTIFACT`, `MODEL_METRICS` |
| Optimization | `MODEL_ARTIFACT`, `CLEANED_TRAIN`, `CLEANED_VALIDATION`, `CLEANED_TEST`, `FROZEN_SPLIT`, `SELECTED_SEGMENTS`, `FIELD_DICTIONARY` | `OPTIMIZATION_REPORT`, `OPTIMIZATION_WINNER` |

Optimization 的 `objective`、`decision_variables`、`bounds`、`constraints`、`search_space`、`optimization_policy`、`real_data` 是独立输入合同，必须由 TaskSpec/planner/snapshot 显式提供。ArtifactResolver 不生成或猜测这些策略。

## Readiness、DAG 和状态

Capability Resolver 现在对每个候选输出：

- `artifact_readiness`、`required_artifacts`、`missing_artifacts`、`producible_artifacts`、`artifact_readiness_score`
- `missing_contract_fields`
- 结合 artifact 比例后的 `dependency_readiness_score`
- `selected` / `blocked` / `deferred` 和可解释 `reason`

ExecutionPlan 使用 produces/requires 建立 DAG edge。完整流程为 Standardization → Cleaning → Segmentation → Modeling → Optimization → Review。已有 artifact 可使不必要的上游节点从最小计划中消失。Runtime 在上游执行后重新计算 readiness，deferred 节点在 artifact 齐备后才进入 Executor。

`SkillExecutionResult` 统一字段为 `skill_id`、`executor`、`status`、`reason`、`inputs`、`outputs`、`missing_requirements`、`missing_artifacts`、`metrics`、`evidence`、`provenance`、`warnings`，并保留现有 facts/findings/limitations/trace 兼容字段。Executor 状态只允许：

- `success`：核心算法完成且成功合同满足。
- `partial`：有效计算和产物已完成，但业务可行性约束未满足。
- `blocked`：执行前缺少不能由当前 DAG 补齐的条件。
- `failed`：核心执行过程出现异常。
- `skipped`：当前计划明确不执行。

`deferred` 是规划/readiness 状态，不是 Executor 终态。

## 验收结果

### DAG A-F

- A：Segmentation 已有 train/split/dictionary 时为 selected/executable，artifact readiness = 1.0。
- B：缺 train 且不允许上游补齐时 blocked，显式列出 `CLEANED_TRAIN`。
- C：Cleaning 在同一 DAG 时 Segmentation 为 deferred，依赖 Cleaning 生成 artifact。
- D：Optimization 的 artifact 和策略合同完整时 selected，可执行真实搜索。
- E：缺 `MODEL_ARTIFACT` 且没有 Modeling 上游时 blocked。
- F：Modeling 在同一 DAG 时 Optimization 为 deferred，建立 Modeling → Optimization edge。

### 真实运行 `20260912_125129_8ad7214b`

Segmentation 回归：

- candidate windows: **287**
- selected high-quality windows: **2**
- selected modeling rows: **45**
- validation rows read: **0**
- test rows read: **0**
- status: **success**
- 五类输出均有 RuntimeArtifactRef、真实路径和 SHA-256。

Optimization 回归：

- candidate count: **12**
- winner: **top_k=5, max_lag=60**
- validation R²: **0.9989545421**
- test R²: **0.9981521170**
- training coverage: **1.04%**
- explicit minimum coverage: **5%**
- test evaluation count: **1**
- test used for search: **false**
- synthetic fallback: **false**
- status: **partial**

该 partial 保留了原有可行性语义：搜索和冻结后测试均已完成，但显式覆盖率约束未满足。本次未修改 min coverage、候选搜索、validation 评分或 test safety。

## Web 状态

Agent 中枢现通过统一状态映射显示：成功、已完成但存在约束未满足、前置条件不足、执行失败、未执行。`partial` 使用 warning 语义，不再被页面的二值判断归为失败。指标仍从后端 `metrics` 读取，不在前端生成或改写证据。

## 修改文件

- `core/skills/artifacts.py`
- `core/skills/context.py`
- `core/skills/capability_resolver.py`
- `core/skills/skill_resolver.py`
- `core/skills/execution_plan.py`
- `core/skills/executor.py`
- `core/skills/core_executors.py`
- `core/skills/runtime.py`
- `core/services/pipeline.py`
- `core/test_artifact_readiness_runtime.py`
- `core/test_segmentation_optimization_executors.py`
- `frontend/src/utils/executionStatus.js`
- `frontend/src/views/AgentWorkflowView.vue`

## 自动验证

- Django 定向 Runtime/Executor 测试：**118 passed**
- Django 全量测试：**237 passed, 1 skipped**
- Frontend tests：**7 passed**
- Frontend ESLint + project lint：**passed**
- Frontend Vite production build：**passed**
- `git diff --check`：**passed**

## 剩余风险

Pipeline 内部的已验证 service 仍使用历史阶段目录合同。该布局已被隔离在 ArtifactResolver 的兼容工作区，但如果后续直接改造 service API 为接收 ArtifactRef，可删除这一兼容层。旧 snapshot 没有原生 registry，当前由中央 legacy adapter 恢复；新 snapshot 已原生写入 registry。
