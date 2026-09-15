# 数据需求规范来源与验证追踪

日期：2026-09-14。只修改两份需求规范并新增检查表/本追踪文件，不执行Pipeline、不训练、不修改业务代码。以下相对路径均以A14根目录为基准。编号对应两份规范章节。

## 逐项来源

| 规范章节/要求 | 直接来源 | 性质与边界 |
| --- | --- | --- |
| 1、2、3、4：场景/required/optional/role/target | 两个场景template.json：scenario_id/name、field_roles、primary_output；fields.csv所有行 | 字段数脱丁烷9+1，干燥器7+0；controlled不等于optional |
| 2、9：脱丁烷测点身份 | debutanizer_column/template.json physical_semantics逐canonical条目 | quantity_type、equipment_role、measurement_location、measurement_channel、flow_direction原值 |
| 2、9：干燥器身份 | industrial_dryer/fields.csv description/display_name | 无独立physical_semantics；表内位置/方向/数量为释义而非代码配置枚举 |
| 2、7、8：单位/类型/界限/alias | 两个fields.csv：unit/data_type/lower_bound/upper_bound/aliases | 清单逐字段复制；不增加alias |
| 4、11：target缺失 | template.constraints.missing_target_policy；integrations/data_cleaning/src/data_cleaning_agent.py process_missing_values/detect_and_repair_anomalies | 输出保留NaN，输入ffill(limit=6)；core/services/pipeline.py _cleaning_spec将controlled映射output |
| 5：时间可接受性 | tools/precheck_real_dataset.py precheck；data_cleaning_agent.py align_timestamp | 非数字文本parse、全有效、唯一、有序；周期中位数及采样证据；不是完整不规则采样认证 |
| 5、6：采样/行数/窗口/lag | template sampling_seconds/default_parameters/constraints；core/skills/stage_adapters.py align/extract | 150为入口硬值；有效周期取max(requested,native median)，分区与guard使用现代码 |
| 6：推荐样本数/时长 | 基于现有分区、lag和窗口的交付建议 | 3000/3600点、50/10小时不是硬阈值；最低入口不保证ARX可辨识 |
| 7：自动换算 | integrations/standardization/standard_agent/units.py UNIT_ALIASES/CONVERSIONS；precheck_real_dataset.py units_ok | 预检要求canonical单位，不直接执行数值换算；Nm3/h无普通m3/h等价承诺 |
| 8、9、10：最终接受边界 | integrations/standardization/standard_agent/physical_semantics.py final_field_acceptance_gate | 匿名字段要求场景绑定证据；可信alias仍过物理冲突；无独立语义块有额外保守约束 |
| 10、14：逆缩放与manifest | core/services/dataset_evidence.py restore_normalized_fields | 源hash、方法、逐字段参数、unit、场景/证据门禁；完整交付补充处理顺序/clipping/batch说明 |
| 12、13、15、16、17：来源包与拒收 | 当前用户交付要求；precheck_real_dataset.py source_ok/license_ok/normal_ok；dry template.data_provenance_required | SOURCE.md等目录是交付约定，非自动解析或真实性认证承诺 |
| 14：文件容器 | precheck_real_dataset.py读取分支；core/services/scene_skill_pipeline.py run_scene_skill_pipeline | xlsx/CSV预检；统一入口保存source.csv，Parquet需有审计转换，不宣称直接支持 |
| 18：SceneContext | core/skills/context.py build_scene_context | final/selected/agent/detected/scenario取数据场景，读取Registry，项目context不覆盖 |
| 18、19、20：执行/回执/泄漏边界 | core/services/scene_skill_pipeline.py；core/skills/stage_adapters.py align/train；three_scene_final_real_runtime.json | 既有统一MD流程；12名单核对现回执；本任务不重跑 |
| 1、21：最新状态 | debutanizer_final_real_acceptance.md；industrial_dryer_final_real_acceptance.md；three_scene_final_real_acceptance.md | 脱丁烷物理2/9自动1/9；DAISY物理0/7；烟草至多2/7候选自动0/7，两场景UNAVAILABLE |
| 21：GT和逐列证据 | real_field_ground_truth.json/.md；datasets/field_acceptance_safety/coverage.json；datasets/real_validation/tobacco_field_review.json；prechecks/dataset_04.json、dataset_10.json、tobacco_zenodo.json | 人工物理GT不等于raw自动匹配；历史GT不覆盖最新烟草子集时以最新专表为准 |
| 参考报告完整性 | [已移除的历史缺口报告](https://github.com/Estrella122/A14/blob/5fdcc11027b0ed16aceddc55accd4a77388ad1d8/remaining_real_data_gaps_final.md) | 原文件混入任务正文，不作当前数值真值；本轮清理移除，原始内容可查历史版本 |
| 23：规范校验 | 本次从原JSON/CSV读取、解析生成后的Markdown表再比较 | 校验required集合/unit/role/location/direction/target、optional分离及12 Skill名单；不修改业务代码 |

## 当前配置SHA-256

| 源文件 | SHA-256 |
| --- | --- |
| integrations/standardization/standards/scenarios/debutanizer_column/template.json | fb2c8271eb5f3895d2f545429d80be0018a36dc646d51f26d655a3059a55d386 |
| integrations/standardization/standards/scenarios/debutanizer_column/fields.csv | 3287b616f5153119d786a365e3995d6294daad48f7dafd2c351de4a048c7da37 |
| integrations/standardization/standards/scenarios/industrial_dryer/template.json | add1abb875d598921f8c438939638c4cca0c9a702a22a4a1af96b26adaed9c9f |
| integrations/standardization/standards/scenarios/industrial_dryer/fields.csv | f1b5b453ab4ee5cfa1ff61cd2dff0f78618eb4f0c85c72b5ca6522954c30e45f |

## 逐场景验证

| 场景 | Required | Optional | Target | 结果 |
| --- | --- | --- | --- | --- |
| debutanizer_column | 9 | 1 | bottom_butane_content | PASS |
| industrial_dryer | 7 | 0 | product_moisture | PASS |

八项检查均PASS：required集合、unit、target、role、physical location、optional独立、建议与强制分开、当前契约版本。干燥器physical_semantics缺项明确标注，不伪造配置。时间格式/Parquet等格式建议与当前读取能力已区分。

Requirement Spec Validation: **PASS**。

本次对core/integrations/tools内Python/JSON/CSV/Markdown文件在生成前后做SHA-256对比，完全一致。仅文档交付，不重复执行算法测试或声称两场景真实验收完成。现有final_regression_report.md及closeout/validation/manifest.json属于上一轮历史快照，其旧规格hash不代表本次新版本；未改写历史凭据。
