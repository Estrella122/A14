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

## 重点能力的独立入口

注册表中的 30 个业务 Skill 均已有独立、可按需发现的 `SKILL.md`。Runtime 只加载本次直接相关的业务 Skill 文档，避免把整套目录注入上下文。

以下 6 项关键 Skill 另外拥有专用 Executor 注册项：

- 缺失异常清洗、高信噪比动态段提取、系统辨识训练和闭环预处理寻优：独立分派入口，复用现有经过验证的阶段实现；只把用户请求的 Skill 记为直接执行，不再把阶段内所有业务 Skill 都记作独立调用。
- 时滞估计：独立执行非负、分段安全的互相关时滞算法，单独输出估计表和补偿数据，不触发模型训练。
- 模型诊断：独立读取冻结模型证据并执行质量门禁，单独输出诊断评估，不重训模型、不增加测试集评估次数。

当同一请求确实包含多个紧密耦合能力时，仍可使用共享阶段 Executor；运行记录会明确标记 `shared_stage`。

## 路由质量门槛

`training/skill_router/quality_gate.py` 在发布前检查冻结模型和留出集哈希，并要求合成留出集达到：精确 Skill 集准确率不低于 95%、micro precision/recall 不低于 95%、未知请求拒绝率不低于 95%、有支持 Skill 的最低 F1 不低于 75%。

当前冻结评测为 97% 精确 Skill 集准确率、96.97% micro precision、100% recall、100% 未知请求拒绝率，达到门槛，因此本轮没有为了刷分重复训练。该数据为合成数据，不能声称是生产准确率；后续应积累经工程师确认的真实误调样本，并用新的独立留出集评估。
