# Web Agent Runtime 实时执行报告

## 结论

Web Agent 中枢已从“请求结束后展示最终快照”升级为真实 Runtime 增量事件流。后端在任务理解、Skill 解析、执行计划、Executor 调用、artifact 生成和回答整理的真实代码位置写入事件；前端通过带序列游标的轮询追加事件，不再用定时器猜测进度或当前节点。

本次没有修改 Capability Resolver、Artifact Resolver、ExecutionPlan、Executor 算法、Registry 或 industrial-analysis 算法与评分。

## 改造前审计

- `core/services/agent_chat.py::chat()` 同步完成规划、执行和回答后才返回。
- `core/skills/runtime.py::execute_skill_plan()` 执行期间没有事件出口，只在结束时写最终 JSON。
- `agent_skill_run_events()` 只会读取最终 JSON 后临时转换事件，不支持运行中读取、游标或重放。
- `AgentWorkflowView.vue` 每 240 ms 人工增加 8%，并按百分比推算 `currentNode`。
- 工程没有 SSE/WebSocket 或已有任务队列。为保持改动边界，采用现有 HTTP API 上的增量 polling。

## 事件模型与持久化

`RuntimeEventStore` 事件包含 `sequence`、`run_id`、`skill_run_id`、`timestamp`、`event_type`、`stage`、`skill_id`、`capability_id`、`executor`、`status`、`message`、`progress` 和 `metadata`。

事件写入 `runtime/agent_skill_runs/<skill_run_id>.events.jsonl`，运行状态和最终结果写入 `<skill_run_id>.live.json`。单次查询最多 200 条，单运行持久历史最多保留 500 条。线程锁保证同一进程内并发 Executor 写入不会产生重复序列。

事件只包含可观察的运行事实、门禁原因和安全摘要，不包含模型思维链或 SKILL.md 正文。只有后端明确传入 `progress` 时前端才显示百分比。

## 传输与恢复

- `POST /api/agent/chat/live/` 校验请求、预分配 `skill_run_id`、启动后台运行，立即返回 HTTP 202。
- `GET /api/agent/skill-runs/<skill_run_id>/events/?after=<sequence>` 只返回游标后的新事件，同时返回下一序列、运行状态、性能指标和完成后的最终结果。
- 原 events URL 保留旧 Skill Run 的最终事件兼容路径。
- 前端每 450 ms 拉取一次增量，按 `sequence` 合并去重。
- 活跃 `skill_run_id`、最后序列和已收事件存入 localStorage。刷新后从最后序列继续；`after=0` 可重放保留历史。

## 实时状态来源

- 任务理解和 Skill Resolution：`chat()` 进入真实规划的前后。
- Capability selected/blocked/deferred：统一 resolver 的真实 candidate trace。
- Skill selected/loaded：真实 Skill Resolution 与 Skill Runtime 加载结果，只传文件清单和 capability 摘要。
- Execution plan 与 queued/waiting：真实 ExecutionPlan 节点和 readiness。
- Executor started/completed/partial/blocked/failed：`executor.execute()` 调用前后。
- Artifact produced：Executor 返回的真实 artifact。
- Answer generation：执行证据进入最终回答整理阶段。

Capability 的 executing/completed 状态从对应 Executor 事件派生；DAG 各节点按 `executor` 独立更新。`partial` 显示为警告，不提升为 success。没有增加伪取消按钮。

## 前端呈现

聊天区在用户消息和最终回答之间插入“实时执行”时间线，默认展示关键事件；完整 capability 评分、DAG、Skill 加载、Executor 状态和 artifact 链继续由 Runtime Observability 面板呈现。原 8%/5% 定时器、按百分比推算节点和无依据进度条已移除。

## 验收

### A. xinan 异常分析

真实运行 `20260912_125129_8ad7214b`，请求“帮我找异常”：Skill Run `skillrun_b0e428e273f6`；选中 `ANOMALY_DETECTION`、`DATA_PROFILING`、`DATA_QUALITY_ANALYSIS`、`TREND_ANALYSIS`；事件 30 条，序列 1–30 无重复；客户端获得 6 次增量更新；平均事件载荷 625.6 B；最终状态 `completed`。

真实浏览器中，时间线位于用户问题与最终回答之间，展示任务理解、四个核心 capability、Skill 加载、ExecutionPlan、industrial-analysis/visualization Executor、artifact 和回答完成事件。

### B–E

- cleaning → segmentation：等待/执行状态按事件独立更新；已有 artifact readiness 回归测试验证上游 artifact 才能解除 deferred/waiting。
- modeling → optimization partial：optimization 可先显示 waiting，modeling 同时显示 executing；最终 `partial` 保留为警告。
- 缺 objective/前置条件：阻断事件保留后端 reason，前端不会当作 success。
- 刷新恢复：游标持久化、`after` 增量读取和序列去重通过；相同批次重放不会重复。

## 修改文件

- `core/skills/runtime_events.py`
- `core/skills/runtime.py`
- `core/services/agent_chat.py`
- `core/agent_api.py`
- `core/urls.py`
- `frontend/src/api/agent.js`
- `frontend/src/utils/runtimeEvents.js`
- `frontend/src/components/AgentExecutionTimeline.vue`
- `frontend/src/views/AgentWorkflowView.vue`
- `core/test_runtime_events.py`
- `frontend/tests/runtime-events.test.js`
- `runtime_live_execution_report.md`

## 测试结果

- 后端完整回归：239 tests passed，1 skipped
- 前端测试：16 passed
- ESLint：通过，38 个 JS/Vue 文件
- Vite production build：通过
- 真实 HTTP 增量轮询：通过
- 真实浏览器 Agent 中枢：通过

## 剩余风险

当前后台执行使用进程内 daemon thread，适合当前本地单服务部署。若以后部署为多进程、多主机或要求服务重启后继续执行，应将任务调度迁移到共享队列。JSONL 和状态文件已为这一迁移提供稳定事件协议。
