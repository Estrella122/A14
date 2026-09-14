# 字段 Agent 训练记录

training_performed=false。字段 Agent 最终标签：NO_MATERIAL_GAIN（仅基线评估，没有实施训练或宣称训练收益）。对当前物理契约缺口的训练决定是 NOT_NEEDED，二者含义不同。

复用已有 StandardizationAgent / semantic_model.predict 生成候选，复用现有 physical_semantics.evaluate 检查最终安全门禁；没有引入新模型，没有调整 threshold、alias、单位、required 或模型权重。

没有训练，故不生成伪造的 train_metrics、validation_metrics、test_metrics 或 model config。dataset_manifest.json 记录语料版本、哈希、schema 和 training_performed；field_metrics.json 记录冻结基线。

当前结构中规则物理门禁仍存在；本轮未新增 learned physical classifier。评测不等于完成了一个新的学习分类器。后续若取得可靠单位、同测点定义和独立标签，再按训练门禁启动增量训练。
