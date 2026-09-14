"""Render the decision/evaluation reports from frozen evidence; does not train."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'datasets/field_ground_truth'
def read(p): return json.loads(p.read_text())
def write(name, body): (ROOT / name).write_text(body.strip() + '\n')
def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(str(x).replace('|', '/') for x in r) + ' |' for r in rows])
def percent(x): return 'N/A（无样本）' if x is None else f'{x:.2%}'
gt=read(ROOT/'real_field_ground_truth.json'); coverage=read(P/'coverage.json'); metrics=read(P/'field_metrics.json'); manifest=read(P/'dataset_manifest.json'); scenes=read(P/'scene_evaluation.json'); clean=read(P/'cleaning_evaluation.json'); runtime=read(ROOT/'three_scene_post_training_runtime.json'); bf=runtime['scenes'][0]['receipt']
chosen=[coverage[i] for i in [0,4,10]]
coverage_table=table(['数据集','required','MATCH','REVIEW','MISSING','NO_EQUIVALENT源列','optional coverage','分类'],[[r['name'],r['required_field_count'],r['matched_required_count'],r['review_required_count'],r['missing_required_count'],r['no_equivalent_count'],percent(r['optional_field_coverage']),r['classification']] for r in coverage])
write('contract_coverage_audit.md',f'''# 真实数据契约覆盖审计

基于 evidence-v1 Ground Truth；先标注源文档，再调用当前 Agent 对照。共 {len(gt['datasets'])} 个候选来源记录、{len(gt['fields'])} 行真值（含缺失标准字段占位）。不是 30 份独立完整真实数据。

{coverage_table}

MATCH/REVIEW/MISSING 按 required canonical 去重，三者之和等于 required。NO_EQUIVALENT 按源列计数，不与 required 相加。覆盖率是可核验物理契约覆盖，不是模型字符串命中率。

没有原文件的来源均为 SOURCE_UNAVAILABLE：全契约待复核；不能断言该工厂没有这些传感器。合成和来源未核实记录仅作库存，排除真实字段评估与真实训练样本。

代表数据：高炉 6/6；LostRunes 脱丁烷塔 2/9（4 待复核、3 缺对应测点）；DAISY 干燥机 0/7（3 待复核、4 缺对应测点）。脱丁烷塔另有一个已确认时间列 Unnamed: 0 未被 Agent 接纳，因此准确分类为 MIXED_LIMITATION；这是元数据预处理缺口，不是可训练的通用空表头别名。

来源与逐字段证据见 real_field_ground_truth.json；契约原件为 integrations/standardization/standards/scenarios/*/{{fields.csv,template.json}}。未删 required、未改变单位或测点。
''')
write('training_need_decision.md', '''# 训练必要性门禁

结论：本轮不训练字段、场景或清洗模型。所有可取得源文件中，没有确认“学习字段名称即可补齐 required 契约”的缺口。此结论只针对当前可核验候选，不代表 Agent 已达到工业泛化目标。

| 来源 | 诊断 | 训练决定 |
| --- | --- | --- |
| 高炉固定真实衍生数据 | 6/6，当前 Agent 正确映射 | NOT_NEEDED |
| LostRunes | 2/9；空表头时间列存在但未识别，另有 4 项待复核、3 项缺失 | MIXED_LIMITATION；无明确可学习映射，不训练 |
| Fortuna 及镜像 | 缺绝对物理单位、inverse metadata、采样语义 | DATA_LIMITED，不训练 |
| DAISY | 工业干燥设备，但测点不等于本项目契约 | DATA_LIMITED，不训练 |
| 只有论文或不可得源文件 | 实际列与单位无法核验 | STILL_REVIEW_REQUIRED |

training_cannot_solve：missing physical sensor；missing unit；missing normalization metadata；unknown sampling semantics；incompatible process location。

Unnamed: 0 只能由该文件的 Date/Time 元数据行作有来源记录的预处理，不能训练成任意文件空表头=timestamp。本轮保留该集成缺口；即便补上仍不能满足完整契约。

模型候选 confidence 不构成测点证明。现有归一化列被 alias 接受的基线缺陷、DAISY 错候选和 OOD uncertain 均需继续治理；没有使用测试集调阈值，也没有用训练掩盖这些结果。
''')
write('field_training_dataset_report.md',f'''# 字段训练/评测语料

已建立可复现语料，未拟合模型。文件：datasets/field_ground_truth/field_examples.jsonl。

{table(['split','样本数'],manifest['splits'].items())}

总数 {sum(manifest['splits'].values())}。label 为 MATCH / NO_MATCH / REVIEW_REQUIRED；HARD_NEGATIVE 是独立 sample_type（含跨场景反例），不是与 NO_MATCH 冲突的第四预测类别。来源包含三场景 canonical/alias、physical_semantics、证据真值、固定错测点测试。没有生成新物理测量值。

字段包含 source/candidate 的 unit、quantity_type、role、location、direction、equipment、scenario、reason_codes、source_type、scenario_split_group。未知属性保持 null，不猜测。

按 canonical semantic group 和 source dataset 分组，以标准化 source 字符串传播最强 holdout，避免轻微格式别名同时进入 train/test。固定哈希划分，无随机调参（seed=null）。real_unseen_test 只表示本语料构建时留出；原有预训练模型是否见过这些公开数据未知，不能称为经证明的全新分布。

GT SHA256：{manifest['source_gt_sha256']}
语料 SHA256：{manifest['dataset_sha256']}

合成或未核实工业数据没有当作真实训练标签；反例字符串属于人工测试输入。原文件授权不明的缓存未发布到 GitHub。
''')
write('field_agent_training_report.md', '''# 字段 Agent 训练记录

training_performed=false。字段 Agent 最终标签：NO_MATERIAL_GAIN（仅基线评估，没有实施训练或宣称训练收益）。对当前物理契约缺口的训练决定是 NOT_NEEDED，二者含义不同。

复用已有 StandardizationAgent / semantic_model.predict 生成候选，复用现有 physical_semantics.evaluate 检查最终安全门禁；没有引入新模型，没有调整 threshold、alias、单位、required 或模型权重。

没有训练，故不生成伪造的 train_metrics、validation_metrics、test_metrics 或 model config。dataset_manifest.json 记录语料版本、哈希、schema 和 training_performed；field_metrics.json 记录冻结基线。

当前结构中规则物理门禁仍存在；本轮未新增 learned physical classifier。评测不等于完成了一个新的学习分类器。后续若取得可靠单位、同测点定义和独立标签，再按训练门禁启动增量训练。
''')
metric_rows=[]
for scene,m in metrics['before'].items():
    metric_rows.append([scene,m['n'],m['match_support'],percent(m['top1_accuracy']),percent(m['top3_recall']),percent(m['top5_recall']),percent(m['match_precision']),percent(m['match_recall']),m['false_auto_accept_count'],percent(m['false_auto_accept_rate']),percent(m['review_recall']),percent(m['hard_negative_rejection'])])
metric_table=table(['场景','源列n','MATCH支持','Top1','Top3','Top5','MATCH precision','MATCH recall','false accept数','false accept/n','review recall','源列硬负例拒绝'],metric_rows)
write('field_agent_evaluation.md',f'''# 字段 Agent 基线评测

{metric_table}

Top-K 是当前规则候选加已有 semantic_model 的组合召回，并非纯神经检索模型准确率。只在 Ground Truth=MATCH 的源列上计算 Top-K；干燥机没有正例支持，必须 N/A。高炉已是标准化衍生列，因此不能据此声称陌生字段泛化 100%。

precision=正确接受/所有接受；recall=正确接受/GT MATCH；false accept rate=错误接受/所有源列；review recall=返回 review/GT REVIEW。镜像源不是独立抽样，不能给统计总体保证。

脱丁烷塔原始列级错误接受 24/43，含应等待归一化元数据的字段；不能称为 Critical False Accept=0。现有数据集 provenance/normalization gate 会阻止其进入真实完整 Pipeline，但不抹去列级缺陷。干燥机 review recall 很低：未匹配不等于正确提出 review。

固定物理硬负例 {len(metrics['hard_negative_probes'])}/{len(metrics['hard_negative_probes'])} 拒绝，使用候选 confidence=0.999 与单位相容条件，仍按设备/位置/方向阻断。原始已记录 reboiler outlet、feed flow 也保持 NO_EQUIVALENT。有限样本不证明所有未知设备安全。

目标 Review Recall>95% 未达标；Top3 仅有限正例满足，不能外推。before/after 是同一个冻结评估结果的对照，因没有训练或字段代码变更，增量 false accept=0；不是新训练模型通过安全验收。

完整映射 trace：datasets/field_ground_truth/evaluation.json；安全门禁 trace：field_metrics.json。
''')
scene_rows=[]
for s in scenes:
    r=s['result']; a=r['auto_selected']; candidate=a.get('scenario_id') if isinstance(a,dict) else a
    scene_rows.append([s['expected'],candidate,r['final_scene'],r['status'],r['confidence']])
write('scene_recognition_evaluation.md',f'''# 场景识别与 OOD 基线

{table(['期望','候选','final_scene','status','confidence'],scene_rows)}

三份已知源 schema 的候选分类准确率 2/3；要求 confirmed 且正确时只有 1/3。DAISY 返回脱丁烷塔候选，是已知缺陷，未当成功。

三个 OOD 中严格 unknown 2/3（66.7%）；医疗列返回 uncertain，因此不满足严格 UNKNOWN。错误 confirmed 已知场景率 0/3，但有候选绝不等于已拒识。均保留 final_scene=null。

场景 Agent：NO_MATERIAL_GAIN（仅评测、未训练）。没有在这 6 个测试 schema 上改阈值或加规则，避免用测试集调参。要增强需要独立真实 OOD/已知场景训练语料及保留测试集；本次未伪称具备足够训练证据。

检测调用 StandardizationAgent.detect_scenario，不用 project UI 场景覆盖；完整结果与候选保存在 datasets/field_ground_truth/scene_evaluation.json。
''')
write('cleaning_strategy_evaluation.md',f'''# 清洗策略评测

复用 DataCleaningSelectionAgent.process_missing_values，没有训练黑盒清洗器。

{table(['安全检查','结果'],[(k,'PASS' if v else 'FAIL') for k,v in clean['checks'].items()])}

输入故障样本、实际清洗日志见 datasets/field_ground_truth/cleaning_evaluation.json。输入 u 仅向前填充最多 6 点，9 点长缺口尾部保持 missing；输出 y 缺失保持为空。改变最后一个未来值不改变此前结果；单独处理 test 不从 train 带入填充值。

这些是明确标为合成的故障评测，不是工业真实测量数据。另有固定高炉实际 Pipeline 的分区清洗 artifact 可追溯。

Cleaning Strategy：NOT_NEEDED（本轮六项因果安全用例）；通用选择器覆盖仍 PARTIAL。未新建可学习 selector，也未覆盖所有 quantity/sampling/outlier/constant 场景。不能把六项通过解释为完整策略空间已验收。
''')
comparison=[]
for r in chosen:
    m=metrics['before'][r['scenario']]
    comparison.append([r['scenario'],f"{r['matched_required_count']}/{r['required_field_count']}",f"{r['matched_required_count']}/{r['required_field_count']}",percent(m['top3_recall']),percent(m['match_precision']),percent(m['match_recall']),m['false_auto_accept_count'],percent(m['hard_negative_rejection']),percent(m['review_recall'])])
comparison_table=table(['场景','Before契约','After契约','Top3前=后','precision前=后','recall前=后','false accept前=后','hard-negative拒绝前=后','review recall前=后'],comparison)
write('before_after_field_mapping.md',f'''# 字段前后对照

未训练、未改字段决策代码，前后基线相同。没有 SOLVED_BY_TRAINING。

{comparison_table}

高炉保持可用；LostRunes 的 3 项缺测点、DAISY 的 4 项缺对应变量是 STILL_DATA_LIMITED；各 4/3 项单位、位置或时间语义待核验为 STILL_REVIEW_REQUIRED。LostRunes 时间元数据列未自动识别也是剩余集成缺口，不可训练空表头通用别名。

NEW_REGRESSION：字段评测没有新增错误接受。GitHub 合并后 MD 路径缺 knowledge_retrieval 的两项集成回归已修复，详见 github_sync_compatibility.md。已有列级 false accept 仍是风险，不被“新增为零”掩盖。
''')
write('post_training_contract_coverage.md',f'''# 诊断后契约复核（本轮未训练）

{comparison_table}

“post_training” 沿用要求的交付文件名，不代表实际发生训练。全来源矩阵见 contract_coverage_audit.md。

场景识别 → 字段候选/当前门禁 → 单位与 provenance 证据 → 契约检查。只有高炉合格，继续实际因果清洗与 12 Skill 执行；脱丁烷塔和干燥机在契约前停止，不对未知单位进行反归一化、不补造 target。三个场景尚未全部通过真实数据验收。
''')
exec_rows=[[e.get('skill_id'),e.get('status'),e['audit'].get('executor_invoked'),e['audit'].get('executor_module')] for e in bf['executions']]
write('three_scene_post_training_pipeline.md',f'''# 三场景真实 Pipeline

{table(['场景','Pipeline','Modeling'],[(r['scene'],r['pipeline'],r['modeling']) for r in runtime['scenes']])}

高炉实际 run_id：{bf['run_id']}；skill_run_id：{bf['skill_run_id']}。
数据 SHA256：{bf['dataset_sha256']}。
SKILL_MANIFEST_MODE=md；统一 12 个 MD Skill、统一 Executor。运行的固定 720h 数据未根据 test 重新挑选。

{table(['Skill','状态','实际调用','模块'],exec_rows)}

对照上次固定真实运行：{json.dumps(bf['comparison'],ensure_ascii=False)}。

Pipeline PASS 是真实契约满足、12 Executor 实际调用、无 blocked/unavailable/failed、有 metrics/audit。部分指标可返回 partial（如未校准 SNR），不等于没执行。Modeling 另标 PARTIAL，不能把运行完成当模型投产证明；baseline、稳定性、多步、自由仿真和残差证据保存在 MODEL_ARTIFACT / MODEL_DIAGNOSTICS。

高炉最终选择 AR 模型；test 单步 R²=0.4898566、RMSE=0.0464308，较同样本 persistence RMSE 改善 3.9966%；AR poles 稳定。10 步 test R²=-0.4246312；自由仿真 R²=-0.5909183（未发散）；残差 ACF 最大 0.2582 超过启发式界限 0.1913，未执行白噪声统计检验。因此 Modeling 只能 PARTIAL。

完整执行收据、模块、参数、metrics、artifact 路径与哈希均在 three_scene_post_training_runtime.json。另两场景 run_id=null，明确 NOT_EXECUTED，不伪造 12 Executor 收据，也不以 synthetic 代替真实运行。

图中第 2 项：PARTIAL。已完成可执行源的复跑与不能执行源的证据门禁，未完成三场景全部真实 Pipeline。
''')
write('remaining_real_data_gaps.md', '''# 剩余真实数据缺口与最终决策

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
''')
print('Rendered decision/evaluation reports from frozen evidence.')
