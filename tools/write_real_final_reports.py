"""Generate final real-data acceptance documents from stored evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def write(p,s):(ROOT/p).write_text(s.strip()+'\n')
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows])
records=load('datasets/real_validation/real_dataset_candidates_final.json');gt=load('real_field_ground_truth.json');run=load('three_scene_real_pipeline_runtime.json');bf=run['scenes'][0]['receipt']
paths=(ROOT/'datasets/real_validation/local_file_inventory.txt').read_text().splitlines()
write('local_real_data_inventory.md',f'''# 本地真实数据库存

使用 rg --files --hidden --no-ignore 搜索，排除 .git/.venv/node_modules/__pycache__；扫描 datasets、training、演示数据、runtime、reports、docs、integrations 及来源/manifest/历史候选文档。检索命中 {len(paths)} 个数据或来源相关路径，包含大量历史运行衍生产物，不是 {len(paths)} 份独立实测数据。

完整路径清单：datasets/real_validation/local_file_inventory.txt。历史 30 个来源逐项核对实际文件是否存在与 SHA256，8 个代表数据文件本轮运行 precheck；新增烟草 subset 有独立原文件记录。

{table(['来源','文件状态','可信分类','SHA256'],[(r['dataset_name'],r['status'],r['source_type'],r['sha256']) for r in records])}

没有重新下载已有 Fortuna、LostRunes、DAISY、coffee 或镜像。重新读取 DAISY 原说明、Fortuna archive 目录、既有 SOURCE/转换元数据及固定高炉 manifest。runtime 内各次标准化 CSV/模型 artifact 是来源的衍生缓存，不当作新真实数据。没有原文件的条目全部 SOURCE_REFERENCE_ONLY。
''')
write('real_dataset_candidates_final.md',f'''# 最终真实候选记录

{table(['scene','dataset','source type','file status','物理契约覆盖','usable','主要阻塞'],[(r['scene'],r['dataset_name'],r['source_type'],r['status'],r['contract_coverage'],r['usable'],r['reject_reason']) for r in records])}

完整逐来源记录（publisher、URL、paper、license、原名、SHA256、rows、columns、时间、采样、单位、文档、target、normalization、inverse、coverage 和 reject reason）：datasets/real_validation/real_dataset_candidates_final.json。字段缺失保留 null，不能用论文样本数冒充已取得文件行数；current_file_rows 是本轮实际读取的表格行数。

有限搜索覆盖：大学基准源、Mendeley、Zenodo、论文数据可用性声明及研究 GitHub。新取得 [Zenodo 归档](https://doi.org/10.5281/zenodo.19334140)中的 FL2409JJ9070-049.xlsx，800×9；完整工业原始数据依论文声明为私有，公开部分是处理后子集。[原论文](https://www.nature.com/articles/s41598-026-49347-9)

[Mendeley Tobacco Primary Processing data2](https://data.mendeley.com/datasets/v3bvdmccmm/1) 仍只有来源描述；本轮文件 API 返回 403，未取得可核验原文件，故保留 SOURCE_REFERENCE_ONLY，而不是标记 REAL_PLANT 成功。

脱丁烷补充文献仍指向 Fortuna 2394 样本基准或不同工厂/不同 target；[公开研究的变量表](https://pmc.ncbi.nlm.nih.gov/articles/PMC9118388/)支持变量描述，但没有补齐当前缓存的单位、采样和逐字段 inverse 参数。[Aalto 文献](https://aaltodoc.aalto.fi/bitstreams/88c37aa9-be5f-45ab-b0a8-d512cb60fce6/download)相关试验为 simulator 且测点不同，不作真实验收。

达到合理来源覆盖后停止搜索。没有用单位范围猜字段、没有拼接不同实验，也没有把 OWS/CAD/图片/模拟文件当完整过程表。新文件不足以改变 ELIGIBLE 数量。
''')
write('real_data_source_and_license_report.md','''# 来源与许可

高炉：Vladimir Trofimov / Mendeley，DOI 10.17632/6d7jbc7tb5.1，CC BY 4.0；使用已有可追溯 720h DERIVED_REAL 文件，转换 manifest 保留因果化验对齐证据。

Fortuna/MAT/研究镜像：BENCHMARK_REAL 表示有公开基准来源，不表示可随意再分发；当前原始数据许可未充分核实。LostRunes 的工厂来源是作者声明，未独立核实，因此降为 UNKNOWN，不再把它写作已认证 REAL_PLANT。

DAISY：大学贡献、Cambridge Control 工业干燥器文档支持 PUBLIC_REAL_PROCESS；公开下载不等于数据再分发许可已核实。原说明给 10 秒/867 点和物理变量名称，没有当前所需单位/测点。

Coffee：既有 Zenodo 实验温度工作簿，来源标注 CC BY 4.0；PUBLIC_EXPERIMENT，但温度试验不能生成连续产品含水率目标。

新烟草子集：Zenodo concept DOI 10.5281/zenodo.19334140 当前解析归档记录 19334481，归档声明 Apache-2.0。原论文说明完整工厂数据为专有，只公开去标识处理子集。按 DERIVED_REAL 记录；原文件保留 runtime/data_validation/final_search，不将完整工厂数据许可推断为开放。[来源声明](https://www.nature.com/articles/s41598-026-49347-9)

Tobacco Primary Processing data2 来源页 CC BY-NC-ND 4.0；本轮未取得原文件，未进行转换、分发或发布。仅凭描述不能构造数据。

本轮没有推送原始候选，也没有联系作者/工厂。授权不清的数据维持本地审阅缓存，预检明确 LICENSE_BLOCKED（待许可证据），并非断言作者永久禁止任何使用。数据来源真实性不能由一段 metadata 自动证明。
''')
write('debutanizer_real_dataset_acceptance.md','''# 脱丁烷塔最终真实验收

未找到合格真实数据。Pipeline=UNAVAILABLE；12 个数值 Executor 未启动；Modeling=NOT_EXECUTED。

最可信物理候选 LostRunes DB DATA-B 原文件本轮读得 11399 行，SHA 与库存一致。文档支持时间和回流流量，物理 GT coverage=2/9；自动门禁仅 1/9。剩余 4 required 待单位/位置复核，3 required 无对应变量。工厂来源是作者声明而非独立认证，许可未核实。

Fortuna 及镜像有 2394×8 基准数据，但匿名 U/y 缺可信物理单位、采样和 inverse metadata；物理契约0/9。变量名称表不能代替原始缩放参数。Reboiler outlet≠bottom B；feed≠downstream flow；C4H6/C4H8≠butane。

预检：datasets/real_validation/prechecks/dataset_01.json、dataset_03.json、dataset_04.json、dataset_23.json。没有为了通过而改 alias、required、安全 gate、阈值或算法。没有合格源，因此无需准备转换 CSV，更不生成虚假 transformation manifest。

继续所需数据见 debutanizer_real_dataset_requirement.md。
''')
write('industrial_dryer_real_dataset_acceptance.md','''# 工业干燥器最终真实验收

未找到满足全部 required 的真实数据。Pipeline=UNAVAILABLE；12 个数值 Executor 未启动；Modeling=NOT_EXECUTED。

DAISY 本轮重新读原始说明：867 点、10 秒采样；输入是燃料流量、排气风机转速、原料流量；输出是干球/湿球温度、原料含水率。源未标物理单位/偏置。风机转速不能当 Nm3/h；原料含水率不能当产品含水率；湿球温度不能当排气相对湿度。物理 GT coverage=0/7，属于 DATA_LIMITED/MISSING_METADATA，不是 Agent 训练问题。

新增实际文件 FL2409JJ9070-049.xlsx（Zenodo处理子集）800行9列。_time 为2024-09-26 00:45:19起的逐秒时间；出口含水率列 ZX_BBHS_OUTMATMOISTURE_PV。时间与出口水分有可解释来源依据，至多2/7物理候选，但这些不等于自动接受；当前 raw 自动0/7。其余列为入口含水率、累计物料、干燥实际/设定值、车间温湿度及 avg。累计物料≠湿进料流量，车间湿度≠排气湿度；板温/干燥设定也不能直接当热风温度，avg 未建立完整物理定义。

缺当前风量、湿进料流量、产品温度、排气湿度等证据；完整处理/缩放记录也不足。没有改字段 Agent 去接受它。原文件与逐字段人工复核记录：datasets/real_validation/tobacco_field_review.json；完整门禁结果：prechecks/tobacco_zenodo.json。

原论文描述完整原始工厂数据不公开，归档只含处理子集。许可详见 real_data_source_and_license_report.md。满足整套契约所需数据见 industrial_dryer_real_dataset_requirement.md。
''')
model=load(Path(next(a['path'] for a in bf['artifacts'] if a['artifact_type']=='MODEL_ARTIFACT')));diag=model['diagnostics'];test=diag.get('test',{});m=bf['metrics']['system_identification_trainer']
modelrows=[['validation RMSE',m.get('validation',{}).get('rmse')],['test RMSE',m.get('test',{}).get('rmse')],['test persistence RMSE',test.get('persistence',{}).get('rmse')],['test improvement %',test.get('rmse_improvement_over_persistence_pct')],['model family',bf['metrics']['model_diagnostics_evaluator'].get('model_family')],['stable AR poles',diag.get('stable_ar_poles')],['10-step test',json.dumps(test.get('multi_step',{}).get('metrics',{}))],['free simulation test',json.dumps(test.get('free_simulation',{}))],['residual',json.dumps(test.get('residual',{}))]]
matrix='''| Scene | Source | Confidence | Contract | 12 Skill Pipeline | Modeling |
| --- | --- | --- | --- | --- | --- |
| blast_furnace | Mendeley固定720h | DERIVED_REAL | PASS 6/6 | PASS | PARTIAL |
| debutanizer_column | LostRunes / Fortuna候选 | UNKNOWN / BENCHMARK_REAL | FAIL，最佳物理2/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer | DAISY / 新烟草子集 | PUBLIC_REAL_PROCESS / DERIVED_REAL | FAIL，分别0/7与至多2/7候选 | UNAVAILABLE | NOT_EXECUTED |'''
write('three_scene_real_pipeline_final_acceptance.md',f'''# 三场景最终验收

{matrix}

高炉只做一次本轮专门固定回归：{bf['run_id']} / {bf['skill_run_id']}；SKILL_MANIFEST_MODE=md。数据 hash={bf['dataset_sha256']}。

{table(['固定基线比较','一致'],bf['comparison'].items())}

{table(['Skill','状态','executor_invoked'],[(e['skill_id'],e['status'],e['audit']['executor_invoked']) for e in bf['executions']])}

{table(['Modeling 项','实测结果'],modelrows)}

Test leakage guard：沿用原有 chronological 60/20/20，结构选择依据 train/validation，冻结模型后单次 test；没有按 test 换数据/模型/参数。guard 与 evaluation_target_hash 见 MODEL_ARTIFACT，完整指标与调用 audit 见 three_scene_real_pipeline_runtime.json。

Pipeline PASS 与 Modeling 分开：高炉执行链完成；多步/自由仿真及残差限制使 Modeling 保持 PARTIAL，不做投产背书。另两场景未满足预检，run_id=null，不伪造执行记录。

通用 Skill 架构 PASS；统一字段安全门禁 PASS（当前回归范围）；三场景真实数据 PARTIAL；三场景12 Skill Pipeline PARTIAL。图中第2项仍 PARTIAL。
''')
for scene,name in [('debutanizer_column','debutanizer_real_dataset_requirement.md'),('industrial_dryer','industrial_dryer_real_dataset_requirement.md')]:
 c=gt['contracts'][scene];config=c['template'];sec=config['sampling_seconds'];fields=[(k,v) for k,v in c['fields'].items() if v['required']=='true']
 write(name,f'''# {scene} 数据交付规范

按当前仓库 integrations/standardization/standards/scenarios/{scene}/fields.csv 与 template.json 生成，不修改契约。

{table(['required field','单位','角色','物理说明'],[(k,v['unit'],v['role'],v['description']) for k,v in fields])}

目标：{config['field_roles']['target']}。输入：{', '.join(config['field_roles']['inputs'])}。optional：{', '.join(k for k,v in c['fields'].items() if v['required']!='true') or '无'}。

采样：模板处理默认 {sec} 秒；请交付原生采样周期、时区、时间戳精度、数据缺口/停机/换批标识。实际周期必须与记录一致，模板默认值不能当源数据采样证明。允许可核验的真实起始时刻+原生采样索引，由独立转换脚本构造时间轴；不得编造日历时间。

最低规模：现有入口至少150行，对应规则采样下至少{149*sec}秒时间跨度；这是工程入口下限，不保证模型有效或全部阶段可执行。数据量还须覆盖冻结分区、guard、滞后和有效动态片段。建议提供多批次/多个稳态与过渡、数日连续原始数据；脱丁烷应覆盖30–75分钟化验滞后及多次工况变化。

缺失：每个required必须有真实测量记录；时间必须可解析、顺序明确；target不能全缺失，不得把补值当实测标签。请给逐字段missing/quality flags、连续缺口长度。现有清洗最多向前补6个输入采样点，target缺失保留；没有新增统一百分比阈值，是否足够由原有分区和数值门禁判断。

元数据：厂/实验编号、同一设备与时段证明、采集系统/校准记录、完整点表、位置/通道/流向、单位/基准状态、target测量方式/湿干基或浓度基准、化验采样与结果可用时间、原文件SHA256、可使用与再分发许可。

归一化：优先原始物理量。若只有缩放数据，需原公式（min-max/z-score或有文档自定义）、每字段参数、source_column身份、单位、源hash与变换/移位记录；缺任一项不能inverse。不得用上下限估计参数。

同一原文件来自同一过程/实验/时间上下文。不能拼接不同工厂列。rename/单位换算/时间解析需保留原文件，脚本输出source/output hash、renames、unit_conversions、time_operations、inverse_transform、dropped_columns、warnings；完整final gate与预检ELIGIBLE后才执行12 Skill。

特定禁止：重沸器出口替代第二塔底测点、进料替代下游流量、风机转速替代体积风量、车间湿度替代排气湿度、原料含水率替代产品含水率。
''')
write('remaining_real_data_gaps_final_v2.md',f'''# 最终结论与后续数据需求

{matrix}

1. 未找到满足契约的脱丁烷塔真实数据。LostRunes物理2/9、自动1/9；Fortuna物理0/9。许可与现场来源核验不足；12 Skill未全部执行。
2. 未找到满足契约的工业干燥器真实数据。DAISY物理0/7；新增800×9烟草处理子集至多2/7物理候选、自动0/7。归档声明Apache-2.0，完整厂数据专有；12 Skill未执行。
3. 高炉固定回归保持一致，12 Executor实际调用，Pipeline PASS / Modeling PARTIAL。
4. 三场景真实Pipeline未全部完成；字段Agent仍NOT_NEEDED_CURRENTLY，不训练。
5. 图中第2项最终 PARTIAL。

阻塞分类：MISSING_REQUIRED_SENSORS、MISSING_METADATA；部分源缺inverse，部分只剩 MISSING_RAW_FILE / DATA_NOT_PUBLIC；未核实授权为LICENSE_BLOCKED（待证据），不是随意推断许可允许。模拟/CAD/不同测点来源为INCOMPATIBLE_PROCESS，出处不足为UNKNOWN。

已完成合理范围本地库存与有限公开搜索，不继续循环搜索同一批镜像。下一步需要数据提供方按两份需求规范提供同源、同步、单位和测点可核验的数据，或取得受限原数据授权。不会发送未经授权的外部联系，也不会改变现有系统去适配不合格数据。

本轮只新增只读预检、库存/报告工具与3项预检测试；未修改工业算法、安全门禁、alias、required、阈值、Skill Runtime、SceneContext或高炉模型。新增openpyxl仅用于本地读取真实XLSX；没有新增训练依赖或运行外部仓库代码。
''')
print('Final real-data reports rendered.')
