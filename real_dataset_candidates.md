# 真实数据候选
本轮新增7个候选/论文线索并复核既有22条，总计29条。来源真实性、字段契约、许可、原文件可得性分别判断。未知/null不是PASS；所有候选本轮均未获准进入两个目标场景数值链。
|scene|dataset|source type|publisher|rows|license|usable|reject reason|
|---|---|---|---|---:|---|---|---|
| debutanizer_column | [Fortuna 文本镜像](https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor) | BENCHMARK | 未核实 | 2394 | 未核实数据许可 | False | 0–1 归一化；无逐字段逆变换参数及物理采样周期；目标预移位 8 个样本。不能还原物理温度。 |
| debutanizer_column | [Coimbra 大学原始 MAT 包](https://home.isr.uc.pt/~fasouza/debutanizer_fortuna_dataset.zip) | PUBLIC_REAL_PROCESS / BENCHMARK | University of Coimbra | 2394 | 未核实数据许可 | False | 包内只有 u1–u7、y 数组，各 2394 条、范围 0–1；没有 inverse scaling 或真实时间元数据。 |
| debutanizer_column | [DC-dataset CSV 镜像](https://github.com/ydycly/DC-dataset) | BENCHMARK | 未核实 | 2394 | 未核实数据许可 | False | 归一化八列，无原始单位/时间/逆变换参数。 |
| debutanizer_column | [LostRunes DB DATA-B](https://github.com/LostRunes/debutanizer-model) | REAL_PLANT (作者声明) | LostRunes | 11399 | 未核实数据许可 | False | 有物理量及 DCS 点位，但缺第二底温、确定的第六塔板和下游流量；进料≠下游流量，重沸器出口≠第二底温。C4H6/C4H8 不能直接当丁烷目标。压力表压单位/编码需确认。 |
| debutanizer_column | [本地 360 行 raw sample](integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv) | BENCHMARK / 原始来源未证实 | 未核实 | 360 | 未核实数据许可 | False | 前阶段已审计：归一化温度不满足物理契约，缺逆缩放证据。 |
| debutanizer_column | [Danny-Taehyun-Kim hybrid demo](https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model) | SYNTHETIC | 未核实 | 未获取 | 未核实数据许可 | False | README 明示合成演示；不生成新数据替代实测。代码 MIT 不等于真实数据许可。 |
| debutanizer_column | [LPG composition paper](https://www.mdpi.com/2076-3417/11/24/11790) | BENCHMARK / paper lead | 未核实 | 263 | 未核实数据许可 | False | 论文实验点；未获取合格原始连续时间序列。 |
| debutanizer_column | [Column flooding paper](https://www.sciencedirect.com/science/article/pii/S0009250925004269) | BENCHMARK / paper lead | 未核实 | 525000 | 未核实数据许可 | False | 论文所述规模；未获取对应原始文件，所有文件门禁未验证。 |
| debutanizer_column | [Fortuna 其他复用仓库](https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column) | BENCHMARK / paper lead | 未核实 | 未获取 | 未核实数据许可 | False | 同类基准复用线索，未发现可信 inverse 参数；未额外下载验证。 |
| industrial_dryer | [DAISY 96-016 industrial dryer](https://homes.esat.kuleuven.be/~tokka/daisydata.html) | PUBLIC_REAL_PROCESS | KU Leuven / Jan Maciejowski, Cambridge | 867 | 未核实数据许可 | False | Cambridge Control Ltd 工业过程，大学贡献。实际为燃料流量/风机转速/原料流量及干湿球温度/原料水分；不等价于当前热风温度/风量/排气湿度/产品水分。原文未给单位、偏置/缩放参数；存在负水分值，不能解释成绝对百分比。 |
| industrial_dryer | [Coffee microwave/oven temperature experiment](https://zenodo.org/records/16729583) | PUBLIC_EXPERIMENT | Alfaifi / Mohamed, Zenodo | 50401 | CC-BY-4.0 | False | 温度实验，各加热方式多试次温度；没有连续水分目标、进料流量、风量及排气湿度。最终水分说明不能填充成时序目标。 |
| industrial_dryer | [Filter media drying moisture](https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction) | PUBLIC_EXPERIMENT | 未核实 | 322 | 未核实数据许可 | False | 论文描述 161 次实验、322 初末记录，七特征；不是当前连续流量/湿度时序契约。只获取页面，未获取原始文件；不能把页面 hash 当数据 hash。 |
| industrial_dryer | [Solar multipurpose dryer](https://data.mendeley.com/datasets/935258dxnt/1) | PUBLIC_EXPERIMENT | 未核实 | 未获取 | CC-BY-4.0 (来源页) | False | 来源页描述温度/空气流量/周期称重；下载请求403，未核实原始行列和目标。 |
| industrial_dryer | [Solar biomass fish dryer](https://data.mendeley.com/datasets/hc3hftr4sm/2) | PUBLIC_EXPERIMENT | 未核实 | 未获取 | CC-BY-4.0 (来源页) | False | 批次鱼干燥实验；下载请求403，文件门禁未验证。 |
| industrial_dryer | [Industrial laundry exhaust](https://www.sciencedirect.com/science/article/pii/S2352340920312178) | DERIVED / REAL_PLANT | 未核实 | 未获取 | 数据许可未核实；文章 CC-BY-NC-ND | False | 实测排气温度/速度派生排气质量流量，30秒；缺当前输入及产品水分契约。 |
| industrial_dryer | [LARCO tumble dryers](https://zenodo.org/records/18630186) | PUBLIC_EXPERIMENT | 未核实 | 未获取 | 未核实 | False | 家用电器能源与环境传感；未验证当前工业进料/产品水分字段。 |
| industrial_dryer | [WUR EHD dryer model](https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/) | DERIVED | 未核实 | 未获取 | 未核实 | False | 模型数据线索；未验证当前工业时序字段。 |
| industrial_dryer | [Rotary potash dryer paper](https://www.mdpi.com/2227-9717/14/5/871) | paper lead | 未核实 | 未获取 | 未核实 | False | 未获得可核验原始数据。 |
| industrial_dryer | [Batch rotary NARX paper](https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103) | paper lead | 未核实 | 未获取 | 未核实 | False | 未获得可核验原始数据。 |
| industrial_dryer | [Rotary nickel CO paper](https://juti.if.its.ac.id/index.php/juti/article/view/1599) | paper lead | 未核实 | 未获取 | 未核实 | False | 论文数据线索，未获取匹配当前字段契约的文件。 |
| industrial_dryer | [本地 867 行合成验收集](演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv) | SYNTHETIC | 未核实 | 867 | 未核实数据许可 | False | 保留上阶段固定数据运行证据，本轮不重跑/调参，不作为真实工业证明。 |
| industrial_dryer | [本地 360 行 dryer raw sample](integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv) | SYNTHETIC / 来源链待核实 | 未核实 | 360 | 未核实数据许可 | False | 前阶段本地搜索：未发现可信实测证据；不能因行数/字段相似当成 DAISY。 |
| debutanizer_column | [StevenShaw98 Fortuna CSV](https://github.com/StevenShaw98/Debutanizer-Column-Process) | BENCHMARK / real origin claimed | StevenShaw98 | 2394 | UNKNOWN | False | 新下载2394×8归一化CSV；无真实时间或逆缩放参数，README输入只描述Process variable 1–7。不能用列位置补物理量。 |
| debutanizer_column | [Basque refinery pentanes classification](https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/) | REAL_PLANT (paper lead) | 论文作者 / PMC | 未获取 | UNKNOWN | False | 论文目标为丁烷中的戊烷分类，输入来自上游稳定塔；不是当前丁烷含量测点契约。PMC正文触发captcha，未绕过、未获取原始文件。 |
| debutanizer_column | [UTP CRU debutanizer thesis](https://utpedia.utp.edu.my/id/eprint/6680/) | REAL_PLANT (thesis lead) | Universiti Teknologi PETRONAS | 未获取 | UNKNOWN | False | 检索到400组温度/流量/回流与iC5/nC5统计；不是Fortuna逐字段inverse元数据，不可挪用其min/max，未获取当前契约原始时序。 |
| industrial_dryer | [Tobacco Primary Processing data2](https://data.mendeley.com/datasets/v3bvdmccmm/1) | REAL_PLANT (publisher description) | Xiuming Chen / Mendeley Data | 未获取 | CC BY-NC-ND 4.0 | False | 2024年1–4月B产线；气流干燥温度/流量/氧量、干燥后水分/温度。原文件API返回403；未核实排气相对湿度、湿进料、Nm3/h基准及全部原始行列。 |
| industrial_dryer | [Solar dryer with thermal storage](https://data.mendeley.com/datasets/cgjpm86mwg/1) | PUBLIC_EXPERIMENT | Rulazi et al. / NM-AIST | 未获取 | CC BY 4.0 | False | 50kg批次胡萝卜/菠萝实验，温湿度/称重/风速；不是连续湿进料率，风速不等于标准体积风量。未获取完整原始文件。 |
| industrial_dryer | [Kiln beech-chip residence time](https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL) | PUBLIC_EXPERIMENT | Recherche Data Gouv | 未获取 | UNKNOWN | False | 旋转窑停留时间分布实验，页面示例60观测3变量；非当前温湿度/水分与连续流量契约。 |
| industrial_dryer | [Cassava dryer IoT design files](https://data.mendeley.com/datasets/yxwn9g2n6s/1) | PUBLIC_EXPERIMENT (design lead) | Mendeley Data | 未获取 | UNKNOWN | False | 固件/设计及环境电气监控资料；未确认产品含水和连续进料原始时序，不能以硬件说明充当数据。 |

## 逐项来源和12项预检
每条候选的全部要求字段记录于three_scene_real_runtime.json/candidates；包含source URL/type、publisher、paper/project、license、download method、原名、hash、行列、时间覆盖/采样、字段意义/单位、target/inputs、normalization/inverse metadata、usable/reject_reason。仅页面线索的行数不当作实际文件计数。

|dataset|file|rows|time|interval|target|inputs|units|anonymous|inverse|duplicate/constant|missing|physical safety|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Fortuna 文本镜像 | PASS | PASS | FAIL | UNKNOWN | FAIL | FAIL | FAIL | UNKNOWN | FAIL | PASS | PASS | FAIL |
| Coimbra 大学原始 MAT 包 | PASS | PASS | FAIL | UNKNOWN | FAIL | FAIL | FAIL | UNKNOWN | UNKNOWN | PASS | PASS | FAIL |
| DC-dataset CSV 镜像 | PASS | PASS | FAIL | UNKNOWN | FAIL | FAIL | FAIL | UNKNOWN | FAIL | PASS | PASS | FAIL |
| LostRunes DB DATA-B | PASS | PASS | PASS | REVIEW | FAIL | FAIL | REVIEW | UNKNOWN | UNKNOWN | PASS | PASS | FAIL |
| 本地 360 行 raw sample | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | FAIL | FAIL | FAIL | UNKNOWN | FAIL | UNKNOWN | UNKNOWN | FAIL |
| Danny-Taehyun-Kim hybrid demo | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| LPG composition paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Column flooding paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Fortuna 其他复用仓库 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| DAISY 96-016 industrial dryer | PASS | PASS | PASS (有序索引+来源明确10秒；无日历时间) | PASS | FAIL | FAIL | FAIL | UNKNOWN | FAIL | PASS | PASS | FAIL |
| Coffee microwave/oven temperature experiment | PASS | PASS | PASS (相对秒) | PASS | FAIL | FAIL | PARTIAL | UNKNOWN | UNKNOWN | PASS | REVIEW | FAIL |
| Filter media drying moisture | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | FAIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | FAIL |
| Solar multipurpose dryer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Solar biomass fish dryer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Industrial laundry exhaust | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| LARCO tumble dryers | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| WUR EHD dryer model | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Rotary potash dryer paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Batch rotary NARX paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Rotary nickel CO paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| 本地 867 行合成验收集 | UNKNOWN | PASS | PASS | PASS | PASS (合成目标) | PASS | PASS (合成声明) | UNKNOWN | UNKNOWN | PASS | PASS | UNKNOWN |
| 本地 360 行 dryer raw sample | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| StevenShaw98 Fortuna CSV | PASS | PASS | FAIL | UNKNOWN | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | PASS | FAIL |
| Basque refinery pentanes classification | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| UTP CRU debutanizer thesis | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Tobacco Primary Processing data2 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Solar dryer with thermal storage | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Kiln beech-chip residence time | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Cassava dryer IoT design files | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |