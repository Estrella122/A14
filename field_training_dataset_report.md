# 字段训练/评测语料

已建立可复现语料，未拟合模型。文件：datasets/field_ground_truth/field_examples.jsonl。

| split | 样本数 |
| --- | --- |
| train | 169 |
| validation | 32 |
| test | 25 |
| hard_negative_test | 4 |
| cross_scene_test | 2 |
| real_unseen_test | 98 |

总数 330。label 为 MATCH / NO_MATCH / REVIEW_REQUIRED；HARD_NEGATIVE 是独立 sample_type（含跨场景反例），不是与 NO_MATCH 冲突的第四预测类别。来源包含三场景 canonical/alias、physical_semantics、证据真值、固定错测点测试。没有生成新物理测量值。

字段包含 source/candidate 的 unit、quantity_type、role、location、direction、equipment、scenario、reason_codes、source_type、scenario_split_group。未知属性保持 null，不猜测。

按 canonical semantic group 和 source dataset 分组，以标准化 source 字符串传播最强 holdout，避免轻微格式别名同时进入 train/test。固定哈希划分，无随机调参（seed=null）。real_unseen_test 只表示本语料构建时留出；原有预训练模型是否见过这些公开数据未知，不能称为经证明的全新分布。

GT SHA256：51dc4dd5dbc351e0578fb1540ebe892ac6e51667262ff74c5c323b1e5aa3b421
语料 SHA256：3bc8cddebe6d331dc0b129b49b8f815b6ab07e454a05b7e270ee70295d5eb19f

合成或未核实工业数据没有当作真实训练标签；反例字符串属于人工测试输入。原文件授权不明的缓存未发布到 GitHub。
