# 真实数据搜索报告

本轮主动联网搜索脱丁烷真实物理数据、inverse metadata、工业/旋转干燥器实测温湿度与进料数据，并检索Zenodo、Mendeley、Figshare、大学及论文GitHub。继承前阶段全格式本地搜索，不重复将runtime副本当新数据。候选29条，不代表穷尽全网。

新增实物： [StevenShaw98 CSV](https://github.com/StevenShaw98/Debutanizer-Column-Process)，2394×8，仍为归一化基准，无inverse参数。原样保存研究缓存，未纳入已接入数据集；没有造温度、造时钟或生成processed文件。

重要新线索：[烟草生产数据](https://data.mendeley.com/datasets/v3bvdmccmm/1)，生产线气流干燥与终端质量变量接近需求，但原始文件访问403，完整测点/单位尚未验证。其CC BY-NC-ND许可及限制照实记录，不发布衍生数据。原请求：https://data.mendeley.com/public-api/datasets/v3bvdmccmm/versions/1；未绕过访问控制。

其他新增：戊烷分类炼厂论文、UTP论文、太阳能蓄热干燥实验、旋转窑停留时间数据、木薯干燥监控设计资料。不同目标、批次/连续差异、量纲与测点不全使其不适合当前契约。论文min/max不属于当前原始文件的inverse参数。

再次读取当前两场景template/fields/physical_semantics并冻结到runtime JSON。没有改required、单位、安全门禁、SceneContext或Skill架构。旧大学MAT、DAISY原始文件继续保留hash和来源；可信来源不意味着与当前契约兼容。

本阶段只对通过预检的数据运行Pipeline；没有合格候选时明确不运行。高炉固定源单次对照结果见总验收及JSON。没有重跑synthetic做业务证明。
