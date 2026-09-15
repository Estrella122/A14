# 工业干燥器：真实数据交付需求规范

版本日期：2026-09-14。scenario_id：`industrial_dryer`。本规范仅说明现有契约与接入要求，不修改程序。

标记约定：**配置**是仓库现值；**代码行为**是当前实现；**交付要求**是来源与可验收性要求；**建议**不增加软件硬阈值。逐项出处及SHA-256见 [来源追踪](https://github.com/Estrella122/A14/blob/b0f3e360f0eecffb77c4a709e4275aed17dd9793/real_data_requirement_source_trace.md)。

## 1. 场景说明

当前过程单元：连续式热风工业干燥装置。输入用于时序质量、动态段、时滞与ARX辨识，主目标是 `product_moisture`。输入角色从 template.field_roles 读取；数据场景由标准化结果确定，项目UI场景不能替代数据场景。

当前 Contract FAIL、Pipeline UNAVAILABLE、12 Skill未执行、Modeling NOT_EXECUTED；具体已读候选限制见第21节。来源：[industrial_dryer_final_real_acceptance.md](https://github.com/Estrella122/A14/blob/b0f3e360f0eecffb77c4a709e4275aed17dd9793/industrial_dryer_final_real_acceptance.md)、[最新三场景验收](https://github.com/Estrella122/A14/blob/b0f3e360f0eecffb77c4a709e4275aed17dd9793/three_scene_final_real_acceptance.md)。

## 2. Required Fields（配置，共7项）

Role同时列出fields.csv角色及SceneContext用途。数值字段均为float；时间为datetime。是否可替代的“否”指禁止用另一个物理测点冒充；可信同测点改名/单位换算不属于替换传感器。

| Canonical Field | 中文含义 | Role | Quantity Type | Measurement Location | Direction | Unit | Required | 是否可替代 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| timestamp | 时间戳 | time / timestamp | time | 采样时刻 | 不适用 | datetime | true | 否 | 工业时序采样时间 |
| hot_air_temperature | 热风入口温度 | manipulated / input | temperature | 热风入口（字段描述） | inlet（字段描述） | degC | true | 否 | 进入干燥器的热风温度 |
| drying_air_flow | 干燥风量 | manipulated / input | volumetric_flow | 热风入口（字段描述） | inlet（字段描述） | Nm3/h | true | 否 | 进入干燥器的热风体积流量 |
| wet_feed_rate | 湿料进料量 | manipulated / input | mass_flow | 湿物料入口（字段描述） | inlet（字段描述） | t/h | true | 否 | 进入干燥器的湿物料质量流量 |
| product_moisture | 产品含水率 | controlled / target | moisture_mass_percentage | 产品出口（字段描述） | outlet（字段描述） | percent | true | 否 | 干燥产品出口含水质量百分数 |
| product_temperature | 产品出口温度 | controlled / model_output | temperature | 产品出口（字段描述） | outlet（字段描述） | degC | true | 否 | 干燥产品离开设备时的温度 |
| exhaust_humidity | 排风湿度 | controlled / model_output | relative_humidity | 尾气/排风出口（字段描述） | outlet（字段描述） | percent | true | 否 | 干燥器尾气相对湿度 |

本场景template **未配置独立physical_semantics块**。表中Quantity Type、Location与Direction是对fields.csv.description的释义，非新增Registry枚举；设备应为同一连续热风干燥器。三个controlled字段均仍为required；product_temperature和exhaust_humidity不是optional。model_outputs列有三个输出，SceneContext主target仅为product_moisture，不据此承诺每条执行路径都拟合三个独立模型。

## 3. Optional Fields（配置）

当前fields.csv与optional_context均无可选字段。维护/工况/字典附件是建议证据，不新增required或optional canonical字段。缺附件不直接等于字段契约失败，但会限制异常归因和工况解释。

## 4. Target规范

`product_moisture`：干燥产品出口含水质量百分数；float，单位percent。必须提供同一过程的真实仪表/化验观测及计量基准。产品含水率为质量百分数；须注明干基/湿基及检测方法，代码未独立规定基准转换公式。

允许保留缺失为NaN（constraints.missing_target_policy=preserve_nan）；不允许插值、前向/后向填充或用模型预测值补造真实标签。时间箱内真实观测均值属于带来源的重采样，不是补造缺失标签；原测值必须保留。预检至少要求一个可解析target观测，但这远不保证ARX能训练/评估，需各分区有效真值。

允许有来源的normalized测量记录，但只有可信、可审计的逆变换恢复物理量后才能进入当前物理契约。必需元数据见第10节。入口水分不能替代出口产品水分。

## 5. 时间字段规范

必须有`timestamp`。交付推荐ISO 8601文本（例如2026-01-01T08:00:00+08:00），或统一的YYYY-MM-DD HH:MM:SS文本并附timezone。当前预检使用pandas.to_datetime，无封闭格式白名单；需全部可解析、单调且唯一。数字epoch必须附单位/时区并先脚本化转为文本时间，不能让数字被默认为纳秒。

仅sample index不能满足timestamp。只有来源证明起始时刻、原始间隔、样本顺序以及丢样/停机记录时，才可用脚本构造t=t0+i×Δt并记录证据、source/output hash；缺任一项不能凭模板默认周期构造。构造属于有证据派生时间，不冒充实测时钟。

最大重复timestamp：**最终预检输入为0**（is_unique）。清洗内部会排序去重，不表示来源冲突可静默丢弃；原文件保留，重复处理需要可追溯规则。

允许有记录的不规则采样进入审查：预检实际核对相邻间隔中位数与metadata.sampling_interval及sampling_evidence，不验证每个间隔完全相等。运行会重采样，不能视为已证实等间隔。必须记录原周期、时区、夏令时/时钟调整、时间范围、丢样与停机；不允许时间顺序不可恢复或跨来源错位。

当前代码无全局硬编码“最大时间断档秒数”；建议连续输入缺失不超过6个有效重采样间隔，超过的区间标记排除/不可用，不靠填充造连续数据。它是清洗填充上限的交付建议，不是时间轴拒收阈值。

## 6. 采样周期与数据时长

配置sampling_seconds=10秒；默认resample_seconds=10，max_lag=60点，window_length=18点，step=6点，top_k=5。selection_window_samples=18、selection_step_samples=6；默认180秒窗口、60秒步长。

**硬入口**：minimum_rows=150（配置和align/预检）；这是重采样前入口计数，重采样后及过滤缺失后仍可能不足。默认等间隔150点首尾跨度1490秒，不是保证12 Skill成功的最短时长。

可接受采样周期没有固定min/max数值范围；要求真实且有记录。align实际采用max(请求重采样周期,正时间差中位数)，不会以更细网格制造信息。建议按10秒原生采集；更粗数据须重新确认能分辨目标动态，不能承诺等价效果。

**验收建议，非原契约强制项**：至少交付3600点、约10小时的有效连续数据，并覆盖多个正常运行动态变化段；不是用样本数量替代目标质量。当前代码无硬编码该推荐样本数或推荐持续时间。

时滞、动态窗口与ARX需要足够的有效成对观测和变化。默认lag搜索跨度约600秒、窗口约180秒；采样变更会改变真实跨度。时序60/20/20分区先冻结，清洗分区独立，验证/测试还扣除guard。guard按max(4,min(2×max_lag+3,min(validation_rows,test_rows)//3))生成；ARX回归还消耗历史阶次。150行并不能保证存在有效动态窗口、可估计时滞或满秩模型；无有效窗口会UNAVAILABLE。

## 7. 单位及工程界限（配置/当前支持）

| 字段 | Expected Unit | 可接受等价单位 | 现有转换公式 | lower_bound / upper_bound |
| --- | --- | --- | --- | --- |
| timestamp | datetime | datetime；见时间规范 | 仅同单位/规范化拼写；无另行换算承诺 | 未配置数值界限 |
| hot_air_temperature | degC | degC、℃、°C；degF、K有转换 | degF→(x−32)×5/9；K→x−273.15 | [0, 500] |
| drying_air_flow | Nm3/h | Nm3/h、Nm³/h；普通m3/h不能直接等价 | 仅同单位/规范化拼写；无另行换算承诺 | [0, 500000] |
| wet_feed_rate | t/h | t/h；kg/h有转换 | kg/h→x/1000 | [0, 200] |
| product_moisture | percent | percent、%；不自动把0–1比例视为百分数 | 仅同单位/规范化拼写；无另行换算承诺 | [0, 100] |
| product_temperature | degC | degC、℃、°C；degF、K有转换 | degF→(x−32)×5/9；K→x−273.15 | [0, 300] |
| exhaust_humidity | percent | percent、%；不自动把0–1比例视为百分数 | 仅同单位/规范化拼写；无另行换算承诺 | [0, 100] |

标准化支持上表注册转换；当前独立预检只读原文件，metadata.units必须为canonical单位，且不会在map_columns后自动改写数据值。因此非canonical交付要先做有证据脚本转换、保留原件与转换manifest，再预检物理文件。所有转换保留原始单位metadata。

单位缺失时关键required字段默认不能直接AUTO_ACCEPT，除非现有Registry可信非匿名身份且物理门禁允许；这个门禁例外不免除真实数据预检对单位文件的要求。Nm3/h需要标准状态定义，不能把实际体积流量无条件等同；浓度/含水率/相对湿度的percent彼此也不能互换。界限用于当前检测，不等于仪表量程证明，超界点须保留并标记，禁止为了符合界限剪裁原文件。

## 8. 字段命名与alias

允许大小写、下划线/空格等可识别写法差异，以下为当前fields.csv的精确alias清单。文档支持的缩写可以提供给审查，但不保证未经当前门禁就自动接受；T1、Temp_B、Flow2须附点位字典。

| Canonical Field | 现有aliases |
| --- | --- |
| timestamp | 时间 / 采集时间 / 记录时间 / TIME / DATETIME / TS |
| hot_air_temperature | 入口热风温度 / 进风温度 / HOT_AIR_TEMP / INLET_AIR_TEMP |
| drying_air_flow | 热风流量 / 进风量 / 干燥空气流量 / DRYING_AIR_FLOW / AIR_FLOW |
| wet_feed_rate | 湿料流量 / 进料量 / 给料量 / WET_FEED_RATE / FEED_RATE |
| product_moisture | 出口含水率 / 产品水分 / 物料含水率 / PRODUCT_MOISTURE / OUTLET_MOISTURE |
| product_temperature | 物料出口温度 / 产品温度 / PRODUCT_TEMP / OUTLET_PRODUCT_TEMP |
| exhaust_humidity | 尾气湿度 / 出口空气湿度 / 排气湿度 / EXHAUST_HUMIDITY / OUTLET_AIR_HUMIDITY |

禁止依据数值范围、列顺序或单纯字符串相似度猜身份；同为temperature/flow不能忽略设备、位置和方向。已有AIR_FLOW/物料含水率等宽泛alias不能替代真实物理来源证明。

**危险反例**：排风机rpm不能等价为drying_air_flow；累计料重不能等价为wet_feed_rate；原料含水率不能等价为product_moisture；湿球温度或车间相对湿度不能等价为exhaust_humidity；板温/加热设定值不能自动等价为hot_air_temperature。

## 9. 物理测点身份附件

每个关键字段给出equipment/equipment_id、measurement_location、适用的channel、flow_direction、sensor/tag description、unit与physical meaning，并将original_column绑定canonical field和scenario_id。未知项目写“未确认”，不能填猜测值。需点表、P&ID定位或仪表说明等可信依据；字段名相似不足以证明同测点。

资料用于审核，不会因为上传一份metadata就自动认证其真实性。当前预检并不把任意字段metadata自动注册为alias；有证据但未匹配的字段保持REVIEW_REQUIRED，交由现有受审计映射路径处理，不能只改表头消除冲突。

## 10. 归一化/标准化元数据

必须逐字段交付normalization method、独立参数（min/max或mean/std）、canonical/original field identity、original unit、source hash或版本、处理顺序、是否clipping、是否per-batch normalization及批次边界。另附来源证据与scenario绑定；代码restore_normalized_fields检查source_hash与受支持方法，不按范围推断参数。

无可信可逆参数不做inverse transform。min-max和z-score需明确正向定义及输出区间；不能默认一定是[0,1]。存在clipping/舍入导致不可逆时说明信息损失，不能声称恢复原始观测。每批缩放要逐批参数，不跨实验补字段。只有处理后物理量文件与完整transform receipt才可继续预检。

## 11. 缺失值规范

Input：原始缺失统一为空或声明的NA；清洗仅在各冻结分区内按时间向前填充最多6点，不读取未来。建议单段gap不超过6点；长gap保留为空并报告，不从别的数据集补齐。

Target及其它controlled输出：保留NaN，不前填、不后填、不用未来插值或预测生成标签。不得为了增加有效样本数伪造真值。当前没有统一硬编码最大缺失百分比；建议所有必需字段尽可能连续，尤其各分区target和动态窗口完整。缺一整列不能用缺失处理解决。

## 12. 异常值与工况附件

建议提供instrument limits、engineering bounds、maintenance periods、shutdown/startup flags、sensor fault flags及标注来源。这些是证据建议，不是新增canonical required字段。原始异常保留，附标志；无现场证据时A14仅能做统计/场景约束检测，不能把统计异常等同真实传感器故障。

## 13. 数据来源证据

附SOURCE.md：来源、所有者/发布方、场景与生产线、真实工厂或实验装置、采集系统、时间范围、许可/授权、脱敏、缩放、裁剪、缺列和衍生情况，全部明确“有/无/未知”。来源等级可为REAL_PLANT/PUBLIC_REAL_PROCESS/PUBLIC_EXPERIMENT/BENCHMARK_REAL/DERIVED_REAL；SYNTHETIC或UNKNOWN不得用于最终真实验收。

说明授权是否允许本地分析和再分发，两者分别记录。公开可下载不等于可再分发，作者声称工厂数据不等于独立认证。原始文件、SHA-256、证据和授权必须可对应到同一版本。

本场景template.data_provenance_required还明确列出：source_system、equipment_id、collection_period、instrument_traceability、usage_authorization。当前预检不逐一认证这些事实，须来源审核。

## 14. 文件格式

优先UTF-8 CSV（一行一个采样时刻，header唯一，单列单位一致，统一缺失值编码）；无合并单元格或隐藏说明充当数据。Parquet可作为原始交付容器，但当前预检没有read_parquet分支，统一场景入口存为source.csv；必须先有审计脚本导出CSV，不承诺直接上传Parquet。Excel .xlsx须指定sheet，预检支持读取指定sheet；进入统一CSV Pipeline前同样需可追溯导出。

原始表头保留；重命名、单位转换、时间解析、行过滤均用脚本，输出transformation_manifest.json（source_hash、output_hash、renames、unit_conversions、time_operations、inverse_transform、row_filters、dropped_columns、warnings）。不能人工静默改CSV。

## 15. 推荐交付目录

```text
dataset_package/
  SOURCE.md
  raw/original.csv
  metadata/fields.csv
  metadata/units.csv
  metadata/normalization.json
  metadata/sampling.json
  metadata/precheck_metadata.json
  optional/process_description.pdf
  optional/tag_dictionary.csv
  processed/                 # 仅发生转换时
    physical.csv
    transformation_manifest.json
    prepare.py
```

fields.csv逐字段写原名、canonical、设备/位置/通道/方向/含义和证据；units.csv保存源单位及目标单位；normalization.json即使未缩放也明确physical；sampling.json写时区、起始时刻、周期、依据、丢样与重复处理。元数据可合并为一个有相同信息的文件，目录不是程序硬约束。

## 16. Minimum Acceptable Dataset Package

- 一个可读取、未经静默修改的同源原始文件及SHA-256；不得跨生产线/不同实验拼接字段。
- 第2节全部required实际存在，主target为真实观测；至少150行，且具备足够有效真值（后续数值可用性另验）。
- 唯一可解析timestamp及可信sampling/timezone信息；仅行序不够。
- 每个required的单位、设备/物理位置、方向及适用通道说明，原列名与canonical对应证据。
- SOURCE.md或同等来源/许可/分析授权说明；数据等级及处理历史。
- 若normalized或发生任何转换，附完整可逆参数、原始文件和脚本/转换manifest；否则明确未缩放。

只有数据文件而无来源、单位和测点身份，不能作为可最终验收包。

## 17. 拒收/阻塞条件

缺required传感器；target不明确或为补造预测；匿名字段无metadata；normalized无可信inverse；不同实验拼字段；synthetic冒充real；位置/通道/方向冲突；单位不可验证；时间顺序不可恢复；许可/分析授权不明；哈希不符。直接拒绝进入真实Pipeline，不一定删除文件：可补证据者留REVIEW_BLOCKED/METADATA_LIMITED/NORMALIZATION_BLOCKED，物理字段不存在者留DATA_LIMITED；最终类别由预检返回，不能把review算matched。

## 18. 交付后验收流程

Source validation → 原文件Hash → Contract precheck（调用final_field_acceptance_gate）→ Unit validation → SceneContext → SKILL_MANIFEST_MODE=md → 现有统一12 Skill Pipeline。

来源和授权须人工/可信证据核验，预检声明provenance_authenticated_by_tool=false。真实预检当前要求metadata.source_type、source_hash、evidence_source、analysis_allowed=true、license、units（canonical字段键）、sampling_interval（秒）、sampling_evidence、normalization_status=physical或restored及transformation_manifest；Excel另有sheet。不能只填true就将不可信数据变真实。

运行预检示例（在A14根目录，文件路径替换成实际交付包）：

```sh
.venv/bin/python tools/precheck_real_dataset.py dataset_package/raw/original.csv --scene industrial_dryer --metadata dataset_package/metadata/precheck_metadata.json --output dataset_precheck.json
```

如发生转换，用processed/physical.csv及与其hash一致的预检元数据，保留raw/source关系。只有ELIGIBLE进入执行。Contract PASS需全部required匹配、review/missing/no_equivalent required为0、单位与身份可信。SceneContext由final_scene→selected_scene→agent_scene→detected_scene→标准化scenario选择Registry，读取inputs/target/units/constraints/defaults；project_context_scene不覆盖它。

Contract PASS不等于Pipeline PASS，更不等于Modeling PASS。完整执行须12节点真实executor_invoked回执、metrics/evidence/warnings/artifact provenance、无blocked/unavailable。合理read仅复用同一次Pipeline前置产物；不拿旧产物冒充。模型评价独立报告，不能为提高结果改test。

## 19. 12 Skill Pipeline

1. `time_axis_alignment_resampler`
2. `missing_anomaly_cleaner`
3. `signal_noise_ratio_estimator`
4. `steady_transient_state_detector`
5. `high_snr_dynamic_segment_extractor`
6. `segment_quality_scorer_ranker`
7. `time_delay_estimator_compensator`
8. `collinearity_detector_reducer`
9. `modeling_dataset_assembler`
10. `arx_structure_order_selector`
11. `system_identification_trainer`
12. `model_diagnostics_evaluator`

## 20. 因果与模型验收边界

chronological_60_20_20_v2：train训练，train+validation选型，冻结后单次test；禁止按test换窗口、lag、数据版本或参数。输入因果处理、输出缺失保留。strict_segment_score=80、snr_threshold_db=10为现有配置，不为接入数据降低。最终单列validation/test RMSE、persistence基线、AR/ARX、稳定性、多步预测、自由仿真和残差；无法检验的项目明确缺失。

## 21. 当前候选专项缺口

未找到满足全部 required 的真实数据。Pipeline=UNAVAILABLE；12 个数值 Executor 未启动；Modeling=NOT_EXECUTED。

DAISY 本轮重新读原始说明：867 点、10 秒采样；输入是燃料流量、排气风机转速、原料流量；输出是干球/湿球温度、原料含水率。源未标物理单位/偏置。风机转速不能当 Nm3/h；原料含水率不能当产品含水率；湿球温度不能当排气相对湿度。物理 GT coverage=0/7，属于 DATA_LIMITED/MISSING_METADATA，不是 Agent 训练问题。

新增实际文件 FL2409JJ9070-049.xlsx（Zenodo处理子集）800行9列。_time 为2024-09-26 00:45:19起的逐秒时间；出口含水率列 ZX_BBHS_OUTMATMOISTURE_PV。时间与出口水分有可解释来源依据，至多2/7物理候选，但这些不等于自动接受；当前 raw 自动0/7。其余列为入口含水率、累计物料、干燥实际/设定值、车间温湿度及 avg。累计物料≠湿进料流量，车间湿度≠排气湿度；板温/干燥设定也不能直接当热风温度，avg 未建立完整物理定义。

缺当前风量、湿进料流量、产品温度、排气湿度等证据；完整处理/缩放记录也不足。没有改字段 Agent 去接受它。原文件与逐字段人工复核记录：datasets/real_validation/tobacco_field_review.json；完整门禁结果：prechecks/tobacco_zenodo.json。

原论文描述完整原始工厂数据不公开，归档只含处理子集。许可详见 real_data_source_and_license_report.md。满足整套契约所需数据见 industrial_dryer_final_data_requirement.md。

本轮收尾复核：复用原文件并重新校验哈希/运行预检；结论未改变。最终收据见 three_scene_final_real_runtime.json；该场景 executions=[]，不把旧产物或规划节点当本次数值执行。

逐required核对：

| required | DAISY | 烟草800×9子集 |
| --- | --- | --- |
| timestamp | 只有10秒样本序列，缺本契约可信绝对时间 | _time有来源候选；未自动接受 |
| hot_air_temperature | 干球温度不能证明热风入口身份 | 干燥实际/设定值未证实为热风入口温度 |
| drying_air_flow | 风机转速不是风量 | 无可确认干燥风量 |
| wet_feed_rate | 原料流量仍缺湿料身份/单位证据 | 累计物料不是湿料质量流率 |
| product_moisture | 原料含水率不是出口产品水分 | 出口水分有来源候选；缩放/单位待复核 |
| product_temperature | 无可确认产品出口温度 | 无可确认产品出口温度 |
| exhaust_humidity | 湿球温度不是相对湿度 | 车间湿度不是尾气相对湿度 |

## 22. 交付签核

提供方确认：同源同设备同时间上下文、字段身份与单位可验证、真实target、来源授权及处理历史完整。A14接收方完成[快速检查表](real_data_acquisition_checklist.md)。缺证据保持UNAVAILABLE；本规范不承诺缺失测点可由训练补足。

## 23. 规范与代码一致性

本版required/unit/target/role/location及optional按当前配置逐项核对，推荐值已单独标记。Requirement Spec Validation: PASS。源文件SHA-256、具体函数和章节映射见[来源追踪](https://github.com/Estrella122/A14/blob/b0f3e360f0eecffb77c4a709e4275aed17dd9793/real_data_requirement_source_trace.md)。此PASS只指规范一致性，不代表本场景真实Pipeline完成。
