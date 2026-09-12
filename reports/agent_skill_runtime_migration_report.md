# Agent Skill Runtime Migration Report

## 本次迁移

新增统一 `TaskSpec` 和 `TaskUnderstandingProvider`。Runtime 在非 legacy 模式下以 TaskSpec 的 objective、task kind、semantic intents、execution mode、negations 和多轮上下文为任务真值。旧字符 n-gram Router、Catalog triggers 和专家词表保留为候选召回及动作安全边界。

新增统一 `SkillResolution`，将 DataContext、发现到的 Skill manifest 和 Capability Resolver 结果合并。Capability Resolver 继续作为 capability selection 单一真值；Loader 和 analysis plan 不再自行选择 capability。

`industrial-analysis` 增加独立 Executor。它直接读取标准化 CSV 或调用方 DataFrame，逐项执行 `analysis_plan.selected_capabilities`，blocked/skipped 项不会进入 Executor。当前真实实现包括画像、数据质量/缺失、趋势/时序、z-score 异常、稳定性和相关分析；其余 capability 返回明确的上下文级结果与“尚无专用统计实现”限制。

`execute_skill_plan()` 现在会调用 Executor Registry，记录真实 `executed`、`executor_invocations` 和 `capabilities_executed`，并保存符合 result contract 顶层结构的结果。测试通过临时目录覆盖输出位置，不写正式 `runtime/agent_skill_runs`。

## 已移出主决策链

- `_detect_intent()`：仅 `legacy` 使用；hybrid/skill_runtime 的展示意图从 TaskSpec 派生。
- `_request_analysis()`：只为旧 Router 提供候选召回主题，不再决定非 legacy 执行模式。
- `router_model.py`：只产生候选，不决定最终 capability。
- Catalog triggers：只作为召回信号。
- `skill_id -> stop_after`：仅 hybrid/legacy 的旧 Pipeline 兼容路径；skill_runtime 禁止走该路径。

## 保留的兼容路径

当前 30 个 Catalog Skill 中，只有 `industrial-analysis` 包拥有真 Executor。标准化、清洗、动态段、建模、优化、评审与报告等旧 Skill ID 在 legacy/hybrid 下仍可映射到 Pipeline workflow；其他可视化、仿真、实验比较等仍是 Planner/Reader 或 unavailable 标记。

## SKILL.md 的实际作用

- 声明 capability 所有权和可加载资源；
- 提供 input requirements、output contract；
- 提供异常阈值等 execution policy；
- 提供 correlation/故障结论等 evidence policy；
- 控制 capability/workflow/reference 的延迟加载；
- policy 被传入 Executor，并由测试证明修改后会改变 Runtime 配置和异常检测结果。

## LLM 状态

当前没有配置 LLM，实际 Task Understanding 仍使用规则 fallback。已提供 `LLMTaskUnderstandingProvider` 和 `LLMResponseRenderer` 注入接口；接入真实 Provider 后不需要修改 Resolver 或 Executor。
