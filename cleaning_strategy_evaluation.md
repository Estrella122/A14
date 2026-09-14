# 清洗策略评测

复用 DataCleaningSelectionAgent.process_missing_values，没有训练黑盒清洗器。

| 安全检查 | 结果 |
| --- | --- |
| target_missing_preserved | PASS |
| limited_forward_fill | PASS |
| long_gap_kept_missing | PASS |
| no_future_leakage | PASS |
| no_cross_gap_interpolation | PASS |
| test_partition_not_backfilled_from_train | PASS |

输入故障样本、实际清洗日志见 datasets/field_ground_truth/cleaning_evaluation.json。输入 u 仅向前填充最多 6 点，9 点长缺口尾部保持 missing；输出 y 缺失保持为空。改变最后一个未来值不改变此前结果；单独处理 test 不从 train 带入填充值。

这些是明确标为合成的故障评测，不是工业真实测量数据。另有固定高炉实际 Pipeline 的分区清洗 artifact 可追溯。

Cleaning Strategy：NOT_NEEDED（本轮六项因果安全用例）；通用选择器覆盖仍 PARTIAL。未新建可学习 selector，也未覆盖所有 quantity/sampling/outlier/constant 场景。不能把六项通过解释为完整策略空间已验收。
