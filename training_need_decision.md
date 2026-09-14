# 训练必要性门禁

结论：本轮不训练字段、场景或清洗模型。所有可取得源文件中，没有确认“学习字段名称即可补齐 required 契约”的缺口。此结论只针对当前可核验候选，不代表 Agent 已达到工业泛化目标。

| 来源 | 诊断 | 训练决定 |
| --- | --- | --- |
| 高炉固定真实衍生数据 | 6/6，当前 Agent 正确映射 | NOT_NEEDED |
| LostRunes | 2/9；空表头时间列存在但未识别，另有 4 项待复核、3 项缺失 | MIXED_LIMITATION；无明确可学习映射，不训练 |
| Fortuna 及镜像 | 缺绝对物理单位、inverse metadata、采样语义 | DATA_LIMITED，不训练 |
| DAISY | 工业干燥设备，但测点不等于本项目契约 | DATA_LIMITED，不训练 |
| 只有论文或不可得源文件 | 实际列与单位无法核验 | STILL_REVIEW_REQUIRED |

training_cannot_solve：missing physical sensor；missing unit；missing normalization metadata；unknown sampling semantics；incompatible process location。

Unnamed: 0 只能由该文件的 Date/Time 元数据行作有来源记录的预处理，不能训练成任意文件空表头=timestamp。本轮保留该集成缺口；即便补上仍不能满足完整契约。

模型候选 confidence 不构成测点证明。现有归一化列被 alias 接受的基线缺陷、DAISY 错候选和 OOD uncertain 均需继续治理；没有使用测试集调阈值，也没有用训练掩盖这些结果。
