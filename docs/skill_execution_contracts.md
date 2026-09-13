# Skill 执行契约与细粒度化边界

## 目标

项目保留 30 个面向业务语义的 Skill，但不要求机械地维护 30 套完全独立算法。每个 Skill 必须有独立、可检查的输入输出契约；算法可以由阶段级 Executor 共用。

机器可读契约位于 `core/skills/contracts.py`，注册表接口会为每个 Skill 返回：

- `executor`：当前实际负责执行的 Executor；
- `capability`：Skill 在 Executor 内对应的明确能力入口；
- `execution_mode`：`orchestrate`、`compute` 或 `evidence`；
- `requires` / `produces`：规范化 artifact 类型；
- `quality_gates`：成功前必须满足的质量约束；
- `version`：契约版本。

## 共享 Executor 不等于独立算法

阶段级 Executor 会一次完成同一阶段的多项紧密耦合计算。例如 `modeling` Executor 同时组装数据集、选择阶次、训练模型、比较候选并执行诊断。运行记录使用以下字段消除歧义：

- `executor_selection_kind=direct`：用户意图直接命中该 Skill；
- `executor_selection_kind=stage_support`：执行共享阶段时一并完成，不代表启动了独立算法实例；
- `dispatch_mode=shared_stage`：一个阶段 Executor 覆盖多项能力；
- `capability_dispatch`：本阶段每个 Skill 到能力入口的映射。

只有业务逻辑、依赖、参数、产物或质量门槛确实不同，并且需要单独发布或扩缩容时，才应拆分新的独立 Executor。

## 统一真实状态

对外状态固定为五种：

- `executed`：本轮确实调用了算法或编排逻辑；
- `evidence_only`：只读取已有任务证据，没有重跑算法；
- `blocked`：输入、artifact 或能力前置条件不足；
- `skipped`：计划明确不执行；
- `failed`：已尝试执行但失败。

旧字段 `status` 和 `activity` 暂时保留以兼容现有客户端，新界面以 `execution_state` 为准。

## 本阶段重点能力

首批明确到具体能力入口的关键 Skill 为：缺失异常清洗、高信噪比动态段提取、时滞估计、系统辨识训练、模型诊断和闭环预处理寻优。测试覆盖完整注册、一致性、关键能力分派、共享阶段归因和状态闭集。
