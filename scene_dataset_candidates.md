# 场景数据候选与门禁
日期：2026-09-14。先沿用已完成的本地穷举搜索 `runtime/data_validation/local_data_search.json`，再查论文、大学和公共仓库。未发现≠证明全世界不存在。UNKNOWN 不作 PASS，门禁不合格不进入 Runtime。未修改字段或算法。
| scene | dataset | source type | rows | fields | units | usable | reason |
|---|---|---|---:|---|---|---|---|
| debutanizer_column | [Fortuna 文本镜像](https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor) | BENCHMARK | 2394 | u1, u2, u3, u4, u5, u6, u7, y | 无量纲 | 否（本阶段业务验收） | 0–1 归一化；无逐字段逆变换参数及物理采样周期；目标预移位 8 个样本。不能还原物理温度。 |
| debutanizer_column | [Coimbra 大学原始 MAT 包](https://home.isr.uc.pt/~fasouza/debutanizer_fortuna_dataset.zip) | BENCHMARK | 2394 | u1, u2, u3, u4, u5, u6, u7, y | 无量纲 | 否（本阶段业务验收） | 包内只有 u1–u7、y 数组，各 2394 条、范围 0–1；没有 inverse scaling 或真实时间元数据。 |
| debutanizer_column | [DC-dataset CSV 镜像](https://github.com/ydycly/DC-dataset) | BENCHMARK | 2394 | U1, U2, U3, U4, U5, U6, U7, U8 | 无量纲 | 否（本阶段业务验收） | 归一化八列，无原始单位/时间/逆变换参数。 |
| debutanizer_column | [LostRunes DB DATA-B](https://github.com/LostRunes/debutanizer-model) | REAL_PLANT (作者声明，未独立核实) | 11399 | Feed Flow to DB, Reboiler o/l Temp, Column top Temp, Reboiling steam flow, Reflux flow, Column Top pressure, Column bottom temp, Control tay temp, C4H6 in DB bottom, C4H8 in DB bottom | {'Feed Flow to DB': 'TPH', 'Reboiler o/l Temp': 'øC', 'Column top Temp': 'øC', 'Reboiling steam flow': 'TPH', 'Reflux flow': 'TPH', 'Column Top pressure': 'kg/cmýg', 'Column bottom temp': 'øC', 'Control tay temp': 'øC', 'C4H6 in DB bottom': 'Wt%', 'C4H8 in DB bottom': 'Wt%'} | 否（本阶段业务验收） | 有物理量及 DCS 点位，但缺第二底温、确定的第六塔板和下游流量；进料≠下游流量，重沸器出口≠第二底温。C4H6/C4H8 不能直接当丁烷目标。压力表压单位/编码需确认。 |
| debutanizer_column | 本地 360 行 raw sample | BENCHMARK / 原始来源未证实 | 360 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 前阶段已审计：归一化温度不满足物理契约，缺逆缩放证据。 |
| debutanizer_column | [Danny-Taehyun-Kim hybrid demo](https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model) | SYNTHETIC | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | README 明示合成演示；不生成新数据替代实测。代码 MIT 不等于真实数据许可。 |
| debutanizer_column | [LPG composition paper](https://www.mdpi.com/2076-3417/11/24/11790) | BENCHMARK / paper lead | 263 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 论文实验点；未获取合格原始连续时间序列。 |
| debutanizer_column | [Column flooding paper](https://www.sciencedirect.com/science/article/pii/S0009250925004269) | BENCHMARK / paper lead | 525000 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 论文所述规模；未获取对应原始文件，所有文件门禁未验证。 |
| debutanizer_column | [Fortuna 其他复用仓库](https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column) | BENCHMARK / paper lead | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 同类基准复用线索，未发现可信 inverse 参数；未额外下载验证。 |
| industrial_dryer | [DAISY 96-016 industrial dryer](https://homes.esat.kuleuven.be/~tokka/daisydata.html) | REAL_PLANT / BENCHMARK | 867 | sample_index, fuel_flow, exhaust_fan_speed, raw_material_flow, dry_bulb_temperature, wet_bulb_temperature, raw_material_moisture | 来源未标定 | 否（本阶段业务验收） | Cambridge Control Ltd 工业过程，大学贡献。实际为燃料流量/风机转速/原料流量及干湿球温度/原料水分；不等价于当前热风温度/风量/排气湿度/产品水分。原文未给单位、偏置/缩放参数；存在负水分值，不能解释成绝对百分比。 |
| industrial_dryer | [Coffee microwave/oven temperature experiment](https://zenodo.org/records/16729583) | PUBLIC_EXPERIMENT | 50401 | A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P | 秒、°C | 否（本阶段业务验收） | 温度实验，各加热方式多试次温度；没有连续水分目标、进料流量、风量及排气湿度。最终水分说明不能填充成时序目标。 |
| industrial_dryer | [Filter media drying moisture](https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction) | PUBLIC_EXPERIMENT | 322 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 论文描述 161 次实验、322 初末记录，七特征；不是当前连续流量/湿度时序契约。只获取页面，未获取原始文件；不能把页面 hash 当数据 hash。 |
| industrial_dryer | [Solar multipurpose dryer](https://data.mendeley.com/datasets/935258dxnt/1) | PUBLIC_EXPERIMENT | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 来源页描述温度/空气流量/周期称重；下载请求403，未核实原始行列和目标。 |
| industrial_dryer | [Solar biomass fish dryer](https://data.mendeley.com/datasets/hc3hftr4sm/2) | PUBLIC_EXPERIMENT | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 批次鱼干燥实验；下载请求403，文件门禁未验证。 |
| industrial_dryer | [Industrial laundry exhaust](https://www.sciencedirect.com/science/article/pii/S2352340920312178) | DERIVED / REAL_PLANT | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 实测排气温度/速度派生排气质量流量，30秒；缺当前输入及产品水分契约。 |
| industrial_dryer | [LARCO tumble dryers](https://zenodo.org/records/18630186) | PUBLIC_EXPERIMENT | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 家用电器能源与环境传感；未验证当前工业进料/产品水分字段。 |
| industrial_dryer | [WUR EHD dryer model](https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/) | DERIVED | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 模型数据线索；未验证当前工业时序字段。 |
| industrial_dryer | [Rotary potash dryer paper](https://www.mdpi.com/2227-9717/14/5/871) | paper lead | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 未获得可核验原始数据。 |
| industrial_dryer | [Batch rotary NARX paper](https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103) | paper lead | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 未获得可核验原始数据。 |
| industrial_dryer | [Rotary nickel CO paper](https://juti.if.its.ac.id/index.php/juti/article/view/1599) | paper lead | 未知 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 论文数据线索，未获取匹配当前字段契约的文件。 |
| industrial_dryer | 本地 867 行合成验收集 | SYNTHETIC | 867 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 保留上阶段固定数据运行证据，本轮不重跑/调参，不作为真实工业证明。 |
| industrial_dryer | 本地 360 行 dryer raw sample | SYNTHETIC / 来源链待核实 | 360 | 未获取/见说明 | 未核实 | 否（本阶段业务验收） | 前阶段本地搜索：未发现可信实测证据；不能因行数/字段相似当成 DAISY。 |

## 八项门禁
PASS 仅指该单项；样本数门禁以至少100条作初筛，不保证动力学激励充分。missing 指下载数值表，LostRunes 时间列另检；Excel 原始表头和空值均保留在 JSON。
| Dataset | schema | unit | timestamp | missing | constant | samples | consistency | target |
|---|---|---|---|---|---|---|---|---|
| Fortuna 文本镜像 | FAIL | FAIL | FAIL | PASS | PASS | PASS | UNKNOWN | FAIL |
| Coimbra 大学原始 MAT 包 | FAIL | FAIL | FAIL | PASS | PASS | PASS | UNKNOWN | FAIL |
| DC-dataset CSV 镜像 | FAIL | FAIL | FAIL | PASS | PASS | PASS | UNKNOWN | FAIL |
| LostRunes DB DATA-B | FAIL | REVIEW | PASS | PASS | PASS | PASS | REVIEW | FAIL |
| 本地 360 行 raw sample | FAIL | FAIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | FAIL |
| Danny-Taehyun-Kim hybrid demo | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| LPG composition paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Column flooding paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Fortuna 其他复用仓库 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| DAISY 96-016 industrial dryer | FAIL | FAIL | PASS (有序索引+来源明确10秒；无日历时间) | PASS | PASS | PASS | PASS | FAIL |
| Coffee microwave/oven temperature experiment | FAIL | PARTIAL | PASS (相对秒) | REVIEW | PASS | PASS | PASS | FAIL |
| Filter media drying moisture | FAIL | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Solar multipurpose dryer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Solar biomass fish dryer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Industrial laundry exhaust | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| LARCO tumble dryers | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| WUR EHD dryer model | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Rotary potash dryer paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Batch rotary NARX paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Rotary nickel CO paper | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| 本地 867 行合成验收集 | PASS | PASS (合成声明) | PASS | PASS | PASS | PASS | PASS | PASS (合成目标) |
| 本地 360 行 dryer raw sample | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

## 溯源文件
每个候选的 source、license、download_url、原文件名、SHA256、行列、单位、采样、输入、目标、物理含义及数值范围均记录在 `three_scene_numeric_runtime.json`。未取得文件的 SHA256/下载链接/行数留 null；论文所述行数不是本地实测行数。下载日志保留 HTTP 403/404，不绕过访问控制。许可未声明的原始文件仅保留本地核验，不纳入公开发布。
