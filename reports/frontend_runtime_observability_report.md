# Web Agent Runtime 可观测性报告

## 修改前展示缺口

Agent 中枢原先已展示 Skill 列表、Skill 执行摘要、阶段流程、Pipeline trace 和最近一次运行的最终结果。以下后端已有字段没有进入 UI：

- capability 的 selected/blocked/deferred/skipped、最终分数和 reason。
- semantic、context、data precondition、scene、dependency、lexical 六项评分。
- `required_artifacts`、`artifact_readiness`、`missing_artifacts`、`producible_artifacts`、`artifact_readiness_score`。
- 与 artifact 缺失分离的 `missing_contract_fields`。
- Executor 的真实 requires/produces DAG、规划态与终态。
- `RuntimeArtifactRef` 的 producer、run、source execution 和 hash。
- Skill Runtime 本次实际加载的 capability/workflow/reference。

原 Skill 卡片还直接展开完整 metrics JSON，并将执行状态简化为成功/阻断两类。

## 新观测面板

### Capability 卡片

默认显示 capability 名称、ID、最终 score、状态和选择/不选择原因。展开“为什么”后显示六项 score breakdown、数据前置、artifact readiness 和缺失合同。

前端只在 `producible_artifacts` 非空时将未选 capability 显示为“等待上游依赖”。后端因语义分不足而给出的 deferred 候选会显示为“未选择”，避免误暗示必然等待执行。

### Execution DAG

DAG 节点默认显示 Executor 和终态。展开后显示：

- `requires_artifacts` / `produces_artifacts`
- readiness reason
- 缺失 artifact 及会生成它的上游 Executor
- 规划态→终态，例如 `deferred → success` 或 `deferred → partial`
- 结果要点，包括 Segmentation 的窗口/行数与 Optimization 的 validation/test/覆盖率

### Artifact 和 Skill 加载

折叠区显示实际加载的 Skill、capability、workflow 和 reference。Artifact 链默认仅显示 type、producer 和截断 hash；完整 artifact id、hash、source execution 和 path 位于二级高级详情。页面不再默认输出整块 JSON。

## 状态语义

Capability：已选择、等待上游依赖、前置条件不足、未选择。

Executor：成功、已完成但存在约束未满足、前置条件不足、执行失败、未执行。`partial`、`blocked` 和 `deferred` 均使用非破坏性的黄/中性视觉语义，不再统一显示为红色失败。

## 最近运行与刷新恢复

Agent 页顶部新增最近 20 次 pipeline run 选择器。选中的 snapshot 作为当前 Agent 证据上下文。每次回答的 runtime observability 按 pipeline run id 保存，切换回已访问运行时恢复它的 capability、DAG、artifact 和 Executor 结果。

页面刷新时会使用持久化的 `skill_run_id` 重读 SkillRun；如 Runtime 保留期已过，仍保留浏览器内已存的观测摘要。页面不再只恢复最终文字结论。最近运行请求限制为 20 条，避免加载全部历史 snapshot。

## 真实浏览器验证

使用本地 Django API、Vite 页面和 Playwright headed Chromium 验证：

- 案例 A：从最近运行选择 `xinan_completed_data.csv / 20260912_125129_8ad7214b`，输入“帮我找异常”。页面显示 `DATA_PROFILING`、`DATA_QUALITY_ANALYSIS`、`TREND_ANALYSIS`、`ANOMALY_DETECTION`；分数分别为 0.972/0.972/0.972/0.992。异常检测展开后显示六项评分、reason 和前置检查。
- 案例 B/C：浏览器组件状态验证显示 `segmentation: deferred → success`，等待 Cleaning 生成 `CLEANED_TRAIN`；`modeling: deferred → success`，`optimization` 等待 Modeling 生成 `MODEL_ARTIFACT`。requires/produces 与上游名称可见。
- 案例 D：用已验收的真实 Runtime 数值做浏览器组件状态回放。Optimization 显示“已完成，但存在约束未满足”，并显示 12 个候选、Validation R² 0.99895、Test R² 0.99815、训练覆盖率 1.04% 和最低要求 5.00%。该回放仅用于前端状态渲染验证，未调用或修改任何算法。
- 案例 E：对真实 xinan snapshot 请求“用已有模型和这批数据优化运行参数”。页面将 Optimization 显示为 blocked，artifact 和“前置合同缺失”分区显示，明确列出 `objective`、`bounds`、`optimization_policy` 等字段，没有显示为模型执行失败。
- 刷新恢复：在 capability 回答和 partial DAG 状态下分别刷新，观测面板均恢复；切换到 xinan 历史 run 后页面的任务 ID、下载链和 trace 一起更新。

## 修改文件

- `core/services/agent_chat.py`：仅新增已有 Runtime 决策的响应透传。
- `core/test_agent_skill_runtime_architecture.py`
- `frontend/src/api/pipeline.js`
- `frontend/src/views/AgentWorkflowView.vue`
- `frontend/src/components/AgentSkillCenter.vue`
- `frontend/src/components/RuntimeObservabilityPanel.vue`
- `frontend/src/utils/executionStatus.js`
- `frontend/src/utils/runtimeObservability.js`
- `frontend/tests/runtime-observability.test.js`

Capability Resolver、Artifact Resolver、ExecutionPlan、Executor、Registry、Segmentation/Optimization 算法与评分权重均未修改。

## 自动验证

- Django 全量测试：**237 passed, 1 skipped**
- Frontend 测试：**13 passed**
- ESLint 与项目 lint：**passed**
- Vite production build：**passed**
- `git diff --check`：**passed**
