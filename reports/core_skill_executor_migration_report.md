# 核心 Skill Executor 迁移报告

## 已完成

1. 新增 `core/skills/execution_plan.py`，把 Catalog 依赖与实际执行依赖分开，生成最小 Executor DAG。
2. 扩展 Executor Registry，注册 standardization、cleaning、modeling、optimization、review、report，并显式标记 segmentation 为 reader-only。
3. 新增统一核心 Executor，实现统一 `SkillExecutionResult` 字段。
4. `core/services/pipeline.py` 暴露稳定 stage-service 入口；Pipeline 与 Executor 共享标准化、清洗、建模、优化、评审、报告的现有实现，不复制底层算法。
5. 清洗 service 增加 `include_segmentation`，纯清洗请求不执行动态段算法；Pipeline 默认行为保持兼容。
6. 建模 Executor 明确返回 train/validation/test 指标和 persistence baseline comparison。
7. Review Executor 只消费已有 standardization/cleaning/modeling 结果，缺证据即 blocked。
8. Report Executor 只格式化 snapshot / SkillExecutionResult，写出 provenance，不重跑 Pipeline。
9. Optimization Executor 检查 objective/model/bounds/constraints/real_data，缺失即 blocked，并记录 `synthetic_fallback=false`。
10. `agent_chat.py` 在 hybrid 下优先执行迁移 Executor，不再对这些目标调用 `rerun_pipeline()`。
11. 执行汇总区分 selected、planned、executed、success、failed、blocked、skipped、unavailable、fallback_used；executed 按真实 Executor 调用计数。

## 兼容性

- 保留 `plan_skills()`、`analysis_plan`、Agent API 和旧私有 stage 函数。
- Pipeline 的默认 `include_segmentation=True`，现有上传全流程不变。
- 保留 `legacy` 模式；`hybrid` 仍是默认建议模式。

## 未完成部分

- segmentation 尚未从清洗 Agent 的组合职责中完全拆成独立算法调用，状态为 reader-only。
- optimization 的独立真实搜索尚未迁完，输入完整时返回 partial；Pipeline 的原实现没有删除。
- 旧 Catalog 仍包含面向文档/治理的长依赖链；实际执行已由 `ExecutionPlan` 隔离，但后续可继续精简 UI 展示。

## 修改文件

- `core/skills/core_executors.py`
- `core/skills/execution_plan.py`
- `core/skills/executor.py`
- `core/skills/runtime.py`
- `core/skills/task_understanding.py`
- `core/services/agent_chat.py`
- `core/services/pipeline.py`
- `core/services/report_service.py`
- `core/test_core_skill_executors.py`
- `core/test_skill_routing.py`
- `core/tests.py`
- 本目录下四份迁移报告
