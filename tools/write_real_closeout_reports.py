"""Closeout documentation; source evidence is reused, never relabeled as a new acquisition."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def write(p,s):(ROOT/p).write_text(s.strip()+'\n')
def table(h,rows):return '\n'.join(['| '+' | '.join(h)+' |','| '+' | '.join(['---']*len(h))+' |']+['| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows])
contracts=read('datasets/real_validation/closeout/contracts.json');candidates=read('datasets/real_validation/closeout/candidates.json');runtime=read('three_scene_final_real_runtime.json');bf=runtime['scenes'][0]['receipt']
text=['# 最终真实物理契约','直接读取本轮仓库 fields.csv/template.json；哈希冻结在 datasets/real_validation/closeout/contracts.json。没有修改任何契约。']
for scene,c in contracts.items():
 text += ['## '+scene, table(['field','required','unit','role','description','accepted aliases'],[(f['standard_name'],f['required'],f['unit'],f['role'],f['description'],f['aliases']) for f in c['fields']]),'当前模板（包含 target、inputs、physical_semantics、sampling、constraints/defaults）：','```json',json.dumps(c['template'],ensure_ascii=False,indent=2),'```']
text += ['## 已接受的来源元数据','final gate 的 field-scoped metadata：standard_field、scenario_id、evidence_source、unit；匿名/归一化列还需要 normalized=false 或 inverse_metadata+transform_applied。离线 inverse helper 额外检查 source_file、source_hash、normalization_method、inverse_transform_parameters。这些必须来自可靠原文件/文档，不是自行填写即真实。点位还需 scene/standard_field/source/unit 对应。','required 字段只有全部通过门禁且证据可信才 Contract PASS。Registry 单位默认和采样默认不是源设备的实测证明；缺少证据仍停留 review。']
write('final_real_data_contracts.md','\n\n'.join(text))
paths=(ROOT/'datasets/real_validation/closeout/local_files.txt').read_text().splitlines()
write('final_local_data_inventory.md',f'''# 最终本地盘点

rg --files --hidden --no-ignore 覆盖 datasets、datasets/real_validation、training、演示数据、runtime、runtime/data_validation、reports、docs、integrations、SOURCE 与下载/转换 manifest；排除 .git、venv、node_modules。命中 {len(paths)} 条路径，包含历史衍生产物，不是同等数量独立真实数据。

当前可取得的12个源文件逐一重新计算hash，全部与既有库存相符。31个来源记录沿用已有来源证据，只有原文件实际存在的条目带 hash_revalidated=true。未重下 Fortuna/LostRunes/DAISY/烟草文件。

{table(['dataset','type','file status','hash revalidated','local file'],[(r['dataset_name'],r['source_type'],r['status'],r.get('hash_revalidated',False),r.get('local_path')) for r in candidates])}

全路径：datasets/real_validation/closeout/local_files.txt；完整来源档案：closeout/candidates.json。重用原始DAISY说明、烟草字段复核与逐字段gate结果；没有把runtime中多次生成的同源CSV计为新数据。
''')
write('final_real_dataset_candidates.md',f'''# 最终候选与来源档案

{table(['scene','dataset','source type','file status','classification','physical coverage','license'],[(r['scene'],r['dataset_name'],r['source_type'],r['status'],r['candidate_classification'],r['contract_coverage'],r.get('license')) for r in candidates])}

完整记录：datasets/real_validation/closeout/candidates.json，包含source_url/publisher/paper_or_project/license/source_type/download_date/original_filename/sha256/rows/columns/time_coverage/sampling_interval/field_documentation_available/units_available/target/normalization_status/inverse_metadata_available/source_confidence。历史下载时间不明保留不明，不用本轮复核时间冒充下载日期。

8个代表原文件再次运行 tools/precheck_real_dataset.py，结果在 datasets/real_validation/prechecks/*。ELIGIBLE只有高炉；SOURCE_ONLY没有原文件，不送入预检/Pipeline；归一化源多重阻塞中仍记录NORMALIZATION_BLOCKED理由，即使主分类因许可为UNUSABLE。NO_EQUIVALENT来自既有人工证据，不让模型自标真值。

新一轮有限检索：

- [MIMOSA官方脱丁烷数据](https://www.mimosa.org/ogi-pilot/debutanizer-fractionator/)包含P&ID、仪表/管线清单与产品资料；未提供可验收的同步运行时序。它是SOURCE_REFERENCE_ONLY/INCOMPATIBLE_PROCESS（静态工程数据），不能当历史数据库。
- [工业批式干燥器排气研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC7519236/)记录排气温度/速度并推算流量与湿度，周期短且缺本契约产品水分、湿进料等同步测点；不能把估算湿度当实测required。此线索属于已登记工业洗涤排气研究，未重复下载。
- [hybrid debutanizer仓库](https://github.com/danny-taehyun-kim/debutanizer-hybrid-model)明确示范数据为synthetic，不作真实验收。

检索没有带来新的ELIGIBLE来源；不同实验的温度/湿度/target不得合并。停止理由见 real_data_search_stop_report.md。
''')
for old,new in [('debutanizer_real_dataset_acceptance.md','debutanizer_final_real_acceptance.md'),('industrial_dryer_real_dataset_acceptance.md','industrial_dryer_final_real_acceptance.md')]:
 body=(ROOT/old).read_text();body += '\n本轮收尾复核：复用原文件并重新校验哈希/运行预检；结论未改变。最终收据见 three_scene_final_real_runtime.json；该场景 executions=[]，不把旧产物或规划节点当本次数值执行。\n';write(new,body)
for scene,old,new in [('debutanizer_column','debutanizer_real_dataset_requirement.md','debutanizer_final_data_requirement.md'),('industrial_dryer','industrial_dryer_real_dataset_requirement.md','industrial_dryer_final_data_requirement.md')]:
 body=(ROOT/old).read_text();body+='\n## 当前配置可接受别名\n\n'+table(['canonical','aliases'],[(f['standard_name'],f['aliases']) for f in contracts[scene]['fields']])+'\n\n别名只作候选身份依据，不能替代单位、测点、方向、通道、缩放与来源检查。U/y匿名别名不能直接AUTO_ACCEPT；全部仍经过final gate。\n';write(new,body)
model=read(Path(next(a['path'] for a in bf['artifacts'] if a['artifact_type']=='MODEL_ARTIFACT')));diag=model['diagnostics'];d=diag['test'];metrics=bf['metrics']['system_identification_trainer']
matrix='''| Scene | Source | Confidence | Contract | Pipeline | Modeling |
| --- | --- | --- | --- | --- | --- |
| blast_furnace | Mendeley固定720h | DERIVED_REAL | PASS 6/6 | PASS | PARTIAL |
| debutanizer_column | LostRunes / Fortuna | UNKNOWN / BENCHMARK_REAL | FAIL，最佳物理2/9、自动1/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer | DAISY / 烟草800×9子集 | PUBLIC_REAL_PROCESS / DERIVED_REAL | FAIL，物理0/7或至多2/7候选、自动0/7 | UNAVAILABLE | NOT_EXECUTED |'''
write('three_scene_final_real_acceptance.md',f'''# 第2项最终真实验收

{matrix}

通用Skill架构 PASS；统一字段安全门禁 PASS（当前验收范围）；三场景真实契约 PARTIAL；三场景12 Skill Pipeline PARTIAL。图中第2项最终 PARTIAL。

高炉本轮专门固定回归仅一次：{bf['run_id']} / {bf['skill_run_id']}，manifest_mode=md。

{table(['基线核对','一致'],bf['comparison'].items())}

{table(['Skill','status','executor_invoked'],[(e['skill_id'],e['status'],e['audit']['executor_invoked']) for e in bf['executions']])}

read节点有本次executor调用和本次run内artifact来源；没有拿旧回执冒充本次执行。完整manifest、modules、metrics、evidence、warnings、source_execution_id见JSON。

Modeling：validation RMSE={metrics['validation']['rmse']}，test RMSE={metrics['test']['rmse']}，test persistence={d['persistence']['rmse']}，改善={d['rmse_improvement_over_persistence_pct']}%；模型AR，稳定={diag['stable_ar_poles']}；10-step test R²={d['multi_step']['metrics']['r2']}，free simulation R²={d['free_simulation']['metrics']['r2']}，残差={json.dumps(d['residual'],ensure_ascii=False)}。因此Modeling保持PARTIAL，不否定工程Pipeline已执行。

冻结60/20/20分区，train/validation选择后单次test；未按test修改任何参数/数据版本/窗口/lag。新测试校验本次来源哈希、12回执、MD模块、同源artifact与guard，不通过新增skip掩盖两场景UNAVAILABLE。
''')
write('real_data_search_stop_report.md','''# 公开数据检索停止报告

search_stop_reason：C + D。

C：较可信来源的完整原始数据、许可或必要元数据无法取得。Mendeley烟草条目只有来源描述，已记录API403；论文披露完整烟草厂原始数据为私有；Fortuna无逐字段inverse/单位/采样证据。

D：当前契约需要特定传感器组合。已取得文件缺对应测点，不能拼接多个数据源补齐。脱丁烷的两处塔底、tray6和下游flow不能由重沸器/进料替代；干燥器累计料重、车间湿度、原料水分不能当湿进料流率、排气湿度、产品水分。

范围：沿用已完成的本地31来源审阅以及大学、Zenodo、Mendeley、研究GitHub/论文补充材料搜索；本轮额外做Zenodo/Mendeley脱丁烷、Figshare干燥器和排气湿度方向检索，并核实官方MIMOSA工程数据条目。未把搜索无结果当作证明全球不存在数据，也不声称穷尽所有平台。

没有新增ELIGIBLE；因此不再循环下载相同基准镜像或重复训练。恢复任务需要新信息：符合两份需求规范的同源文件、可信点表/单位/采样、源哈希及使用许可，或受限原数据的合法授权。未来获得新公开源也可重新预检；无需先改代码。

本轮未发送邮件/联系工厂/购买数据/推送未核实许可原文件。到当前可取得证据为止，公开数据收尾结论是PARTIAL，不是DONE。
''')
write('final_remaining_gaps.md',f'''# 最终剩余缺口

{matrix}

1–6. 未最终找到合格脱丁烷真实数据。最佳物理文件LostRunes DB DATA-B，作者声明工厂源、数据许可未核实；required物理2/9，自动1/9，Contract FAIL，12 Skill未实际执行。Fortuna为基准来源，仍缺单位/inverse/采样，不能改善完整契约。

7–12. 未最终找到合格干燥器真实数据。DAISY公开工业过程文档支持来源，但数据再分发许可未核实，物理0/7；烟草Zenodo处理子集归档声明Apache-2.0，完整原厂数据专有，至多2/7有证据候选、自动0/7。Contract FAIL，12 Skill未执行。

13. 高炉本轮固定hash/Skill/modules/metrics全部与基线一致，12 Skill实际调用。
14. 字段Agent NOT_NEEDED_CURRENTLY；没有新高价值可学习映射缺口，主要缺物理变量和元数据。
15. 三场景真实Pipeline没有全部PASS。
16. 图中第2项最终PARTIAL。

通用Skill化和安全门禁保持通过；未修改Runtime、Loader、Registry、Planner、SceneContext、12算法、required、alias、阈值、模型权重、高炉或前端。新增最终验收测试验证UNAVAILABLE边界，不把测试绿灯当数值执行完成。

后续交付规范：debutanizer_final_data_requirement.md、industrial_dryer_final_data_requirement.md。搜索按C/D条件停止；新数据到位才重新打开真实接入任务。
''')
print('Closeout reports generated.')
