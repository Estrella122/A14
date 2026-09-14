# 最终候选与来源档案

| scene | dataset | source type | file status | classification | physical coverage | license |
| --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | Fixed Mendeley derived 720h | DERIVED_REAL | ACQUIRED_FILE | ELIGIBLE | 6/6 | CC BY 4.0 |
| debutanizer_column | Fortuna 文本镜像 | BENCHMARK_REAL | ACQUIRED_FILE | UNUSABLE | 0/9 | 未核实数据许可 |
| debutanizer_column | Coimbra 大学原始 MAT 包 | BENCHMARK_REAL | ACQUIRED_FILE | REVIEW_BLOCKED | 0/9 | 未核实数据许可 |
| debutanizer_column | DC-dataset CSV 镜像 | BENCHMARK_REAL | ACQUIRED_FILE | UNUSABLE | 0/9 | 未核实数据许可 |
| debutanizer_column | LostRunes DB DATA-B | UNKNOWN | ACQUIRED_FILE | UNUSABLE | 2/9 | 未核实数据许可 |
| debutanizer_column | 本地 360 行 raw sample | UNKNOWN | ACQUIRED_FILE | REVIEW_BLOCKED | 0/9 | 未核实数据许可 |
| debutanizer_column | Danny-Taehyun-Kim hybrid demo | SYNTHETIC | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | 未核实数据许可 |
| debutanizer_column | LPG composition paper | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | 未核实数据许可 |
| debutanizer_column | Column flooding paper | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | 未核实数据许可 |
| debutanizer_column | Fortuna 其他复用仓库 | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | 未核实数据许可 |
| industrial_dryer | DAISY 96-016 industrial dryer | PUBLIC_REAL_PROCESS | ACQUIRED_FILE | UNUSABLE | 0/7 | 未核实数据许可 |
| industrial_dryer | Coffee microwave/oven temperature experiment | PUBLIC_EXPERIMENT | ACQUIRED_FILE | NORMALIZATION_BLOCKED | 0/7 | CC-BY-4.0 |
| industrial_dryer | Filter media drying moisture | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实数据许可 |
| industrial_dryer | Solar multipurpose dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | CC-BY-4.0 (来源页) |
| industrial_dryer | Solar biomass fish dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | CC-BY-4.0 (来源页) |
| industrial_dryer | Industrial laundry exhaust | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 数据许可未核实；文章 CC-BY-NC-ND |
| industrial_dryer | LARCO tumble dryers | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实 |
| industrial_dryer | WUR EHD dryer model | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实 |
| industrial_dryer | Rotary potash dryer paper | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实 |
| industrial_dryer | Batch rotary NARX paper | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实 |
| industrial_dryer | Rotary nickel CO paper | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | 未核实 |
| industrial_dryer | 本地 867 行合成验收集 | SYNTHETIC | ACQUIRED_FILE | REVIEW_BLOCKED | 0/7 | 未核实数据许可 |
| industrial_dryer | 本地 360 行 dryer raw sample | SYNTHETIC | ACQUIRED_FILE | REVIEW_BLOCKED | 0/7 | 未核实数据许可 |
| debutanizer_column | StevenShaw98 Fortuna CSV | BENCHMARK_REAL | ACQUIRED_FILE | UNUSABLE | 0/9 | UNKNOWN |
| debutanizer_column | Basque refinery pentanes classification | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | UNKNOWN |
| debutanizer_column | UTP CRU debutanizer thesis | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/9 | UNKNOWN |
| industrial_dryer | Tobacco Primary Processing data2 | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | CC BY-NC-ND 4.0 |
| industrial_dryer | Solar dryer with thermal storage | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | CC BY 4.0 |
| industrial_dryer | Kiln beech-chip residence time | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | UNKNOWN |
| industrial_dryer | Cassava dryer IoT design files | UNKNOWN | SOURCE_REFERENCE_ONLY | SOURCE_ONLY | 0/7 | UNKNOWN |
| industrial_dryer | KLD-2 tobacco processed subset / transformer-lstm | DERIVED_REAL | ACQUIRED_FILE | REVIEW_BLOCKED | 2/7 evidence-backed candidates, 0/7 auto acceptance | Apache-2.0 declared for archive; full plant source proprietary |

完整记录：datasets/real_validation/closeout/candidates.json，包含source_url/publisher/paper_or_project/license/source_type/download_date/original_filename/sha256/rows/columns/time_coverage/sampling_interval/field_documentation_available/units_available/target/normalization_status/inverse_metadata_available/source_confidence。历史下载时间不明保留不明，不用本轮复核时间冒充下载日期。

8个代表原文件再次运行 tools/precheck_real_dataset.py，结果在 datasets/real_validation/prechecks/*。ELIGIBLE只有高炉；SOURCE_ONLY没有原文件，不送入预检/Pipeline；归一化源多重阻塞中仍记录NORMALIZATION_BLOCKED理由，即使主分类因许可为UNUSABLE。NO_EQUIVALENT来自既有人工证据，不让模型自标真值。

新一轮有限检索：

- [MIMOSA官方脱丁烷数据](https://www.mimosa.org/ogi-pilot/debutanizer-fractionator/)包含P&ID、仪表/管线清单与产品资料；未提供可验收的同步运行时序。它是SOURCE_REFERENCE_ONLY/INCOMPATIBLE_PROCESS（静态工程数据），不能当历史数据库。
- [工业批式干燥器排气研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC7519236/)记录排气温度/速度并推算流量与湿度，周期短且缺本契约产品水分、湿进料等同步测点；不能把估算湿度当实测required。此线索属于已登记工业洗涤排气研究，未重复下载。
- [hybrid debutanizer仓库](https://github.com/danny-taehyun-kim/debutanizer-hybrid-model)明确示范数据为synthetic，不作真实验收。

检索没有带来新的ELIGIBLE来源；不同实验的温度/湿度/target不得合并。停止理由见 real_data_search_stop_report.md。
