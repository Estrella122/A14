# 诊断后契约复核（本轮未训练）

| 场景 | Before契约 | After契约 | Top3前=后 | precision前=后 | recall前=后 | false accept前=后 | hard-negative拒绝前=后 | review recall前=后 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | 6/6 | 6/6 | 100.00% | 100.00% | 100.00% | 0 | N/A（无样本） | N/A（无样本） |
| debutanizer_column | 2/9 | 2/9 | 100.00% | 4.00% | 50.00% | 24 | 100.00% | 33.33% |
| industrial_dryer | 0/7 | 0/7 | N/A（无样本） | N/A（无样本） | N/A（无样本） | 0 | 100.00% | 5.26% |

“post_training” 沿用要求的交付文件名，不代表实际发生训练。全来源矩阵见 contract_coverage_audit.md。

场景识别 → 字段候选/当前门禁 → 单位与 provenance 证据 → 契约检查。只有高炉合格，继续实际因果清洗与 12 Skill 执行；脱丁烷塔和干燥机在契约前停止，不对未知单位进行反归一化、不补造 target。三个场景尚未全部通过真实数据验收。
