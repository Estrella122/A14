# 最终真实候选记录

| scene | dataset | source type | file status | 物理契约覆盖 | usable | 主要阻塞 |
| --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | Fixed Mendeley derived 720h | DERIVED_REAL | ACQUIRED_FILE | 6/6 | True | None |
| debutanizer_column | Fortuna 文本镜像 | BENCHMARK_REAL | ACQUIRED_FILE | 0/9 | False | 0–1 归一化；无逐字段逆变换参数及物理采样周期；目标预移位 8 个样本。不能还原物理温度。 |
| debutanizer_column | Coimbra 大学原始 MAT 包 | BENCHMARK_REAL | ACQUIRED_FILE | 0/9 | False | 包内只有 u1–u7、y 数组，各 2394 条、范围 0–1；没有 inverse scaling 或真实时间元数据。 |
| debutanizer_column | DC-dataset CSV 镜像 | BENCHMARK_REAL | ACQUIRED_FILE | 0/9 | False | 归一化八列，无原始单位/时间/逆变换参数。 |
| debutanizer_column | LostRunes DB DATA-B | UNKNOWN | ACQUIRED_FILE | 2/9 | False | 有物理量及 DCS 点位，但缺第二底温、确定的第六塔板和下游流量；进料≠下游流量，重沸器出口≠第二底温。C4H6/C4H8 不能直接当丁烷目标。压力表压单位/编码需确认。 |
| debutanizer_column | 本地 360 行 raw sample | UNKNOWN | ACQUIRED_FILE | 0/9 | False | 前阶段已审计：归一化温度不满足物理契约，缺逆缩放证据。 |
| debutanizer_column | Danny-Taehyun-Kim hybrid demo | SYNTHETIC | SOURCE_REFERENCE_ONLY | 0/9 | False | README 明示合成演示；不生成新数据替代实测。代码 MIT 不等于真实数据许可。 |
| debutanizer_column | LPG composition paper | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/9 | False | 论文实验点；未获取合格原始连续时间序列。 |
| debutanizer_column | Column flooding paper | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/9 | False | 论文所述规模；未获取对应原始文件，所有文件门禁未验证。 |
| debutanizer_column | Fortuna 其他复用仓库 | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/9 | False | 同类基准复用线索，未发现可信 inverse 参数；未额外下载验证。 |
| industrial_dryer | DAISY 96-016 industrial dryer | PUBLIC_REAL_PROCESS | ACQUIRED_FILE | 0/7 | False | Cambridge Control Ltd 工业过程，大学贡献。实际为燃料流量/风机转速/原料流量及干湿球温度/原料水分；不等价于当前热风温度/风量/排气湿度/产品水分。原文未给单位、偏置/缩放参数；存在负水分值，不能解释成绝对百分比。 |
| industrial_dryer | Coffee microwave/oven temperature experiment | PUBLIC_EXPERIMENT | ACQUIRED_FILE | 0/7 | False | 温度实验，各加热方式多试次温度；没有连续水分目标、进料流量、风量及排气湿度。最终水分说明不能填充成时序目标。 |
| industrial_dryer | Filter media drying moisture | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 论文描述 161 次实验、322 初末记录，七特征；不是当前连续流量/湿度时序契约。只获取页面，未获取原始文件；不能把页面 hash 当数据 hash。 |
| industrial_dryer | Solar multipurpose dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 来源页描述温度/空气流量/周期称重；下载请求403，未核实原始行列和目标。 |
| industrial_dryer | Solar biomass fish dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 批次鱼干燥实验；下载请求403，文件门禁未验证。 |
| industrial_dryer | Industrial laundry exhaust | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 实测排气温度/速度派生排气质量流量，30秒；缺当前输入及产品水分契约。 |
| industrial_dryer | LARCO tumble dryers | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 家用电器能源与环境传感；未验证当前工业进料/产品水分字段。 |
| industrial_dryer | WUR EHD dryer model | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 模型数据线索；未验证当前工业时序字段。 |
| industrial_dryer | Rotary potash dryer paper | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 未获得可核验原始数据。 |
| industrial_dryer | Batch rotary NARX paper | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 未获得可核验原始数据。 |
| industrial_dryer | Rotary nickel CO paper | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 论文数据线索，未获取匹配当前字段契约的文件。 |
| industrial_dryer | 本地 867 行合成验收集 | SYNTHETIC | ACQUIRED_FILE | 0/7 | False | 保留上阶段固定数据运行证据，本轮不重跑/调参，不作为真实工业证明。 |
| industrial_dryer | 本地 360 行 dryer raw sample | SYNTHETIC | ACQUIRED_FILE | 0/7 | False | 前阶段本地搜索：未发现可信实测证据；不能因行数/字段相似当成 DAISY。 |
| debutanizer_column | StevenShaw98 Fortuna CSV | BENCHMARK_REAL | ACQUIRED_FILE | 0/9 | False | 新下载2394×8归一化CSV；无真实时间或逆缩放参数，README输入只描述Process variable 1–7。不能用列位置补物理量。 |
| debutanizer_column | Basque refinery pentanes classification | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/9 | False | 论文目标为丁烷中的戊烷分类，输入来自上游稳定塔；不是当前丁烷含量测点契约。PMC正文触发captcha，未绕过、未获取原始文件。 |
| debutanizer_column | UTP CRU debutanizer thesis | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/9 | False | 检索到400组温度/流量/回流与iC5/nC5统计；不是Fortuna逐字段inverse元数据，不可挪用其min/max，未获取当前契约原始时序。 |
| industrial_dryer | Tobacco Primary Processing data2 | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 2024年1–4月B产线；气流干燥温度/流量/氧量、干燥后水分/温度。原文件API返回403；未核实排气相对湿度、湿进料、Nm3/h基准及全部原始行列。 |
| industrial_dryer | Solar dryer with thermal storage | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 50kg批次胡萝卜/菠萝实验，温湿度/称重/风速；不是连续湿进料率，风速不等于标准体积风量。未获取完整原始文件。 |
| industrial_dryer | Kiln beech-chip residence time | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 旋转窑停留时间分布实验，页面示例60观测3变量；非当前温湿度/水分与连续流量契约。 |
| industrial_dryer | Cassava dryer IoT design files | UNKNOWN | SOURCE_REFERENCE_ONLY | 0/7 | False | 固件/设计及环境电气监控资料；未确认产品含水和连续进料原始时序，不能以硬件说明充当数据。 |
| industrial_dryer | KLD-2 tobacco processed subset / transformer-lstm | DERIVED_REAL | ACQUIRED_FILE | 2/7 evidence-backed candidates, 0/7 auto acceptance | False | MISSING_REQUIRED_SENSORS / MISSING_METADATA; workshop humidity is not exhaust humidity; accumulated mass is not feed rate |

完整逐来源记录（publisher、URL、paper、license、原名、SHA256、rows、columns、时间、采样、单位、文档、target、normalization、inverse、coverage 和 reject reason）：datasets/real_validation/real_dataset_candidates_final.json。字段缺失保留 null，不能用论文样本数冒充已取得文件行数；current_file_rows 是本轮实际读取的表格行数。

有限搜索覆盖：大学基准源、Mendeley、Zenodo、论文数据可用性声明及研究 GitHub。新取得 [Zenodo 归档](https://doi.org/10.5281/zenodo.19334140)中的 FL2409JJ9070-049.xlsx，800×9；完整工业原始数据依论文声明为私有，公开部分是处理后子集。[原论文](https://www.nature.com/articles/s41598-026-49347-9)

[Mendeley Tobacco Primary Processing data2](https://data.mendeley.com/datasets/v3bvdmccmm/1) 仍只有来源描述；本轮文件 API 返回 403，未取得可核验原文件，故保留 SOURCE_REFERENCE_ONLY，而不是标记 REAL_PLANT 成功。

脱丁烷补充文献仍指向 Fortuna 2394 样本基准或不同工厂/不同 target；[公开研究的变量表](https://pmc.ncbi.nlm.nih.gov/articles/PMC9118388/)支持变量描述，但没有补齐当前缓存的单位、采样和逐字段 inverse 参数。[Aalto 文献](https://aaltodoc.aalto.fi/bitstreams/88c37aa9-be5f-45ab-b0a8-d512cb60fce6/download)相关试验为 simulator 且测点不同，不作真实验收。

达到合理来源覆盖后停止搜索。没有用单位范围猜字段、没有拼接不同实验，也没有把 OWS/CAD/图片/模拟文件当完整过程表。新文件不足以改变 ELIGIBLE 数量。
