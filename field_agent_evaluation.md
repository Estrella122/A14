# 字段 Agent 基线评测

| 场景 | 源列n | MATCH支持 | Top1 | Top3 | Top5 | MATCH precision | MATCH recall | false accept数 | false accept/n | review recall | 源列硬负例拒绝 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | 32 | 32 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0 | 0.00% | N/A（无样本） | N/A（无样本） |
| debutanizer_column | 43 | 2 | 100.00% | 100.00% | 100.00% | 4.00% | 50.00% | 24 | 55.81% | 33.33% | 100.00% |
| industrial_dryer | 23 | 0 | N/A（无样本） | N/A（无样本） | N/A（无样本） | N/A（无样本） | N/A（无样本） | 0 | 0.00% | 5.26% | 100.00% |

Top-K 是当前规则候选加已有 semantic_model 的组合召回，并非纯神经检索模型准确率。只在 Ground Truth=MATCH 的源列上计算 Top-K；干燥机没有正例支持，必须 N/A。高炉已是标准化衍生列，因此不能据此声称陌生字段泛化 100%。

precision=正确接受/所有接受；recall=正确接受/GT MATCH；false accept rate=错误接受/所有源列；review recall=返回 review/GT REVIEW。镜像源不是独立抽样，不能给统计总体保证。

脱丁烷塔原始列级错误接受 24/43，含应等待归一化元数据的字段；不能称为 Critical False Accept=0。现有数据集 provenance/normalization gate 会阻止其进入真实完整 Pipeline，但不抹去列级缺陷。干燥机 review recall 很低：未匹配不等于正确提出 review。

固定物理硬负例 4/4 拒绝，使用候选 confidence=0.999 与单位相容条件，仍按设备/位置/方向阻断。原始已记录 reboiler outlet、feed flow 也保持 NO_EQUIVALENT。有限样本不证明所有未知设备安全。

目标 Review Recall>95% 未达标；Top3 仅有限正例满足，不能外推。before/after 是同一个冻结评估结果的对照，因没有训练或字段代码变更，增量 false accept=0；不是新训练模型通过安全验收。

完整映射 trace：datasets/field_ground_truth/evaluation.json；安全门禁 trace：field_metrics.json。
