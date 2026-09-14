# 字段前后对照

未训练、未改字段决策代码，前后基线相同。没有 SOLVED_BY_TRAINING。

| 场景 | Before契约 | After契约 | Top3前=后 | precision前=后 | recall前=后 | false accept前=后 | hard-negative拒绝前=后 | review recall前=后 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | 6/6 | 6/6 | 100.00% | 100.00% | 100.00% | 0 | N/A（无样本） | N/A（无样本） |
| debutanizer_column | 2/9 | 2/9 | 100.00% | 4.00% | 50.00% | 24 | 100.00% | 33.33% |
| industrial_dryer | 0/7 | 0/7 | N/A（无样本） | N/A（无样本） | N/A（无样本） | 0 | 100.00% | 5.26% |

高炉保持可用；LostRunes 的 3 项缺测点、DAISY 的 4 项缺对应变量是 STILL_DATA_LIMITED；各 4/3 项单位、位置或时间语义待核验为 STILL_REVIEW_REQUIRED。LostRunes 时间元数据列未自动识别也是剩余集成缺口，不可训练空表头通用别名。

NEW_REGRESSION：字段评测没有新增错误接受。GitHub 合并后 MD 路径缺 knowledge_retrieval 的两项集成回归已修复，详见 github_sync_compatibility.md。已有列级 false accept 仍是风险，不被“新增为零”掩盖。
