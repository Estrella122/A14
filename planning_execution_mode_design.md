# Planning执行模式修复

原则：用户执行意图与数据准备状态分开。缺snapshot或artifact不能把明确execute意图改写成只读；也不能为了execute跳过requires。

## 最小修改

1. core/skills/md_planning.py：无snapshot仅在没有execute意图时采用analyze。解释/否定冲突仍优先。execute计划可包含blocked节点；真正运行依赖现有readiness/Executor门禁。
2. 同文件补“查看/解释已有结果、为什么筛选/清洗、当前指标、哪些参数需要重新辨识”的证据边界；仅在task本来不是execute时启用，避免覆盖明确重新执行。证据型匹配加载文档，但不产生MD数值执行节点。
3. system-identification-trainer/SKILL.md增加“模型辨识”同义召回词，不改execution_mode、requires、depends_on、算法或参数。

保留现有数值查询约定：“当前数据的信噪比是多少”可按现有MD测试从数据计算指标，这与重跑清洗/筛选/建模阶段不同；没有把全部疑问句一律禁用。现有条件句、引用、否定保护继续有效。

## 三阶段语义

|阶段|已有结果查询|明确执行|
|---|---|---|
|Cleaning|查看清洗结果 → analyze/evidence_only|重新执行数据清洗 → execute|
|Selection|为什么筛选成这样 → analyze/evidence_only|重新提取高信噪比动态段 → execute|
|Modeling|当前模型指标如何 → analyze/evidence_only|训练系统辨识模型 → execute|

“哪些参数需要重新辨识”和“为什么当前模型结果这样”保持只读；“请重新运行模型辨识”保持execute。关键词“重新”本身不构成动作授权。

## 三模式和artifact复用

legacy沿用原路由。hybrid优先MD且保留已有混合/全流程兼容。md只使用MD节点。测试不要求三种模式选择完全相同Skill；如legacy“模型辨识”可选择multi_model_benchmark，MD选择system_identification_trainer，但执行边界一致。无匹配文档的MD解释请求可返回空计划，不因此启动执行。

MD resolver仍可用已有requires满足输入并省略上游依赖。最终目标节点仍保留；缺输入会blocked。没有把“execute”状态当成真实执行成功，也没有强制全依赖重算。

## 测试设计

新增core/test_planning_execution_modes.py共10项测试，含三阶段6项、两个保护问句、模型辨识动作及原三个请求。每项覆盖legacy/hybrid/md、snapshot=None和真实artifact fixture两种上下文。无mock规划函数；检查plan.mode、predicted_stop、MD解释节点为空、执行节点存在、无数据时blocked。

测试fixture仅用于规划结构与artifact可用性，不作为工业数值/模型效果证明。原core/test_acceptance.py全部断言原样保留。
