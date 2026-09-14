# 剩余真实数据缺口与最终决策

| Scene | Before coverage | After coverage | Main blocker | Pipeline |
| --- | --- | --- | --- | --- |
| blast_furnace 固定数据 | 6/6 | 6/6 | 无契约阻塞；模型有效性仍 PARTIAL | PASS |
| debutanizer LostRunes | 2/9 | 2/9 | Mixed：元数据时间列未识别 + 4 待复核 + 3 缺测点 | UNAVAILABLE |
| industrial_dryer DAISY | 0/7 | 0/7 | Data：3 待复核 + 4 缺对应物理变量 | UNAVAILABLE |

以上是各场景最可信代表文件，不能把不同实验/镜像列拼成一个完整工厂数据集。全部 30 个候选记录见 contract_coverage_audit.md。

1. 三场景阻塞中：高炉无字段识别阻塞；脱丁烷塔和干燥机均存在实质数据/元数据缺口。两份代表文件合计 7 项缺对应测点、7 项证据待复核；另 1 个已确认元数据时间列未自动映射。明确可学习的等价字段缺口为 0。不是声称所有未知源都没有这些物理量。
2. 未训练：没有字段被“训练解决”。缺传感器、单位、inverse metadata、采样/物理位置不能由学习补齐。先补源证据或换符合契约的数据。
3. 本轮新增 false auto accept=0（未改变字段决策）；已有脱丁烷塔列级错误接受 24/43 未消除，故整体工业识别目标尚未达标。
4. physical safety gate 保留，4 个强置信度错测点反例被阻断；但 alias / normalization 的列级路径仍有不足，不能声明所有路径零误接纳。
5. 脱丁烷塔：UNAVAILABLE。
6. 工业干燥机：UNAVAILABLE。
7. 高炉：Pipeline PASS，Modeling PARTIAL。
8. 三个真实 Pipeline 未全部完成；没有用 synthetic 冒充。
9. 图中第 2 项：PARTIAL。

字段 Agent：NO_MATERIAL_GAIN（不训练，当前数据缺口无需强行训练）。场景 Agent：NO_MATERIAL_GAIN（基线仍有 DAISY 错候选、医疗 OOD uncertain）。Cleaning Strategy：NOT_NEEDED（有限因果测试）；通用策略覆盖 PARTIAL。

Ground Truth 是源文档支持的人工解释和确定性转换标注，不是独立现场工程师签字认证；原模型训练集暴露未知；public mirror 非独立样本；小规模安全/OOD测试不可代替部署验收。对不明单位不新增 alias，对未知 inverse 不做反归一化。

本轮交付：14 个指定文件、2 个评测脚本、1 个报告生成脚本、10 个新增回归测试；另附 GitHub 同步兼容报告。此前本地未提交修改已原样保留，不能把整个 git diff 视为本轮新改动。
