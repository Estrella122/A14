"""Render post-safety reports from recorded evaluations and pipeline receipts."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'datasets/field_acceptance_safety'
def load(path):return json.loads(path.read_text())
def write(name,text):(ROOT/name).write_text(text.strip()+'\n')
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows])
after=load(P/'after.json');before=load(P/'before.json');metrics=load(P/'metrics.json');coverage=load(P/'coverage.json');gt=load(ROOT/'real_field_ground_truth.json');runtime=load(ROOT/'three_scene_final_runtime.json');bf=runtime['scenes'][0]['receipt']
write('field_acceptance_path_audit.md','''# 字段接受路径审计

修复前：_match_one 中仅配置 physical_semantics 的场景调用 evaluate；trusted alias 把标准物理属性复制为源属性并直接通过物理维度。map_columns 对无 physical_gate_pass 的行默认放行；manual override 写 matched，duplicate resolver 又允许 manual 忽略门禁。匿名 U/y 列因 alias 被当作物理量接受。

| path | method | 原 physical/location/direction | 原 unit | 原直接 matched 风险 | 修复后 |
| --- | --- | --- | --- | --- | --- |
| 显式别名 | alias | trusted 跳过冲突 | 冲突可阻断，缺失继承 | 有 | final gate，源冲突优先 |
| 格式归一别名 | normalized_alias | 同上 | 同上 | 有 | final gate，保留位置/通道 |
| 学习记忆别名 | learned_alias | 同上 | 同上 | 有 | final gate |
| 厂商核心规则 | vendor_core_alias | 有合同才检查 | 有 | 无合同可放行 | final gate，无无条件 fallback |
| 模糊语义 | semantic | 有合同才检查 | 有 | 无合同可放行 | final gate |
| 模型候选 | trained_model / trained_model_auto | 有合同才检查 | 有 | 无合同可放行 | final gate，confidence 不证明身份 |
| 点位词典 | point_dictionary | 信任词典复制 | 部分 | 有 | final gate + scene/field/source/unit 绑定 |
| 匿名/缩放列 | alias U1…U8/y | 无身份元数据检查 | 继承合同单位 | 有 | 必须 field/scenario/unit/scale 元数据 |
| 人工映射 | manual | 跳过 | 仅记录冲突 | 有 | 重新 final gate，无豁免 |
| 离线逆变换 | normalization_mapping | 未统一接入 | 检查参数 | 元数据绑定可能错测点 | dataset_evidence 中统一 gate |
| 去重 | duplicate resolution | manual 可绕过 | 不重验 | 有 | gate pass 优先；失败不能恢复 matched |

```mermaid
flowchart TD
  A[源列与源元数据] --> B[alias / point / semantic / model 候选]
  B --> C[候选 method 与 confidence]
  C --> D[单位检查与数值否决]
  D --> E[final_field_acceptance_gate]
  E --> F[身份 / 物理维度 / 单位 / 来源 / 场景 / 缩放证据]
  F --> G[AUTO_ACCEPT / REVIEW_REQUIRED / REJECT]
  G --> H[去重：不允许恢复失败候选]
  H --> I[最终 mapping 与审计]
  J[人工 override] --> E
  K[离线 inverse transform binding] --> E
```

数字范围只用于否决/降低候选置信度；不构成字段身份。所有运行时返回 matched 的候选先过 final gate，人工更新中的临时状态不会绕过最终检查。
''')
write('unified_field_acceptance_design.md','''# 统一 Final Acceptance Gate

入口：integrations/standardization/standard_agent/physical_semantics.py::final_field_acceptance_gate。
调用处：engine.map_columns；engine.standardize 人工覆盖后；core/services/dataset_evidence.py 离线逆缩放字段绑定。

保留候选召回和现有阈值；门禁是唯一最终接受决策。检查 candidate、identity_basis、unit、quantity_type、physical_role、equipment、measurement_location、channel、flow_direction、source_confidence、provenance、scenario_compatibility、required-field criticality；缺省维度明确依赖 registry identity，不能谎称有源实测证据。

显式/格式别名可作为高可信身份；解析到的源物理冲突优先于合同默认值。bottom_temp_a、tray_6_temperature 保持通过；reboiler、feed、错误通道/塔板不能通过高分或坏 alias 恢复。

U1…U8/y、normalized_N/scaled_N 等匿名候选没有自动物理单位假设。需要场景绑定的 standard_field、evidence_source、unit，以及 normalized=false 或 inverse_metadata+transform_applied。数值范围不参与身份判定。已声明 metadata 与合同的单位/设备/方向等冲突也会阻断。

field_metadata 是受信任调用方提交的来源证据，不是自动鉴真服务；其真伪仍需文档/人工核验。离线 restore_normalized_fields 额外要求源 SHA256、文件名、公式和有限逆变换参数，拒绝缺失 scenario_id；错测点即便公式有效仍会失败。没有新增自动反归一化 Runtime hook。

所有行有 final_acceptance_audit：method、source_column、candidate、scenario、criticality、identity/provenance/unit basis、checks、physical_checks、physical_evidence、metadata_checks、decision/reason。去重补充 final_status/post_duplicate_decision；不把排序胜出当物理通过。

没有完整物理合同的场景仍进入该入口；可信 registry identity 检查可观察冲突；不明的非可信语义/人工候选保守复核。未知属性没有被补造成已验证的设备/测点。
''')
old={(r['dataset_id'],r['source']):r for r in before}
rows=[]
for r in after:
 if r['scenario']=='debutanizer_column' and r['real_evaluation_eligible']:
  b=old[(r['dataset_id'],r['source'])];m=r['mapping'];rows.append([r['dataset_id'],r['source'],b['predicted_field'],b['mapping']['method'],b['prediction'],r['expected'],r['predicted_field'],m['decision'],m.get('final_acceptance_audit',{}).get('reason')])
write('debutanizer_column_level_reaudit.md',f'''# 脱丁烷塔 43 列逐列复审

{table(['指标','结果'],metrics['debutanizer_column'].items())}

{table(['dataset','source_column','previous_candidate','previous_method','previous_status','Ground Truth','new_candidate','new_decision','reason'],rows)}

43 是多个公开候选/镜像的列记录合计，不是单个 43 列工厂文件。24 个历史错误接受全部来自匿名 U/y 别名，现为复核；GT MATCH 的 Reflux flow 仍接受。元数据时间列仍未自动识别。critical false accept=0 仅指这一冻结真值集，不能外推为任意工业 CSV 的保证。
''')
write('field_acceptance_safety_acceptance.md',f'''# 字段接受安全验收

{table(['场景','列数','旧接受','旧错接受','新接受','新错接受','review','reject','新增 false reject'],[[s,m['source_column_count'],m['previous_auto_accept_count'],m['previous_wrong_accept_count'],m['new_auto_accept_count'],m['new_wrong_accept_count'],m['review_count'],m['reject_count'],len(m['new_false_rejects'])] for s,m in metrics.items()])}

三场景 GT 集新增 false reject=0；指定 bottom_temp_a、top temp [degC]、tray_6_temperature 正例通过。Reboiler o/l Temp、Feed Flow to DB 维持 review/reject；高置信坏 alias、错通道、错误方向、未知关键单位、人工去重恢复、跨场景元数据、错误 inverse binding 均有专项测试。

core/test_final_field_acceptance.py 新增 13 项测试；既有 trained_model_auto 门禁与 Ground Truth、OOD、清洗安全测试保留。没有删除失败用例或新增 skip。4 条旧断言原本要求匿名 U 字段被接受，已改为精确验证 8 个字段受阻及场景不能 confirmed；不是削弱安全标准。

既有三项数据许可/真实文件缺口 skip 保留。没有训练新模型，没有调整阈值或 alias/required；现有 safety gate 对未知源仍不是事实鉴定器。完整 trace 位于 datasets/field_acceptance_safety/after.json。
''')
actual={}
for r in after:
 if r['prediction']=='MATCH':actual.setdefault(r['dataset_id'],set()).add(r['predicted_field'])
ct=[]
for c in coverage:
 req={k for k,v in gt['contracts'][c['scenario']]['fields'].items() if v['required']=='true'}
 ct.append([c['name'],c['required_field_count'],c['matched_required_count'],c['review_required_count'],c['missing_required_count'],c['no_equivalent_count'],f"{c['matched_required_count']}/{c['required_field_count']}",len(actual.get(c['dataset_id'],set())&req),c['classification']])
write('contract_coverage_post_safety.md',f'''# 安全修复后契约覆盖

GT 保持 evidence-v1、不重新让模型生成标签。matched_required 是有来源证据的物理匹配，不是自动接受数；最后单列当前实际自动接受，防止把候选当契约通过。

{table(['数据集','required','GT MATCH','GT REVIEW','GT MISSING','NO_EQUIVALENT','物理coverage','实际自动required','分类'],ct)}

高炉 6/6；LostRunes 2/9 可信物理字段但实际自动 required=1（时间元数据未接入），4 待复核、3 缺对应变量；DAISY 0/7，3 待复核、4 缺对应变量。未取得源文件的论文条目是 SOURCE_UNAVAILABLE，而不是断言该设备不存在传感器。

安全收紧不改变物理存在性。Fortuna 匿名 normalized 列不再因 alias 虚增 coverage。完整来源、列、单位、采样、来源可信程度沿用 real_field_ground_truth.json 的 source_metadata；合成与未核实源不进入真实数值验收。
''')
write('field_training_need_reassessment.md','''# 字段训练重新判断

结论：NOT_NEEDED_CURRENTLY。

高炉 CAN_RUN_NOW；LostRunes 是 MIXED_LIMITATION，但唯一明确存在而未自动识别的 Date/Time 元数据列属于有来源依据的预处理接入问题，不应学习成任意 Unnamed: 0=timestamp。没有确认的高价值可学习同测点映射缺口。

两份代表文件仍有 7 个 required 缺对应测点、7 个 required 待单位/位置/采样证据复核；其他只有论文的来源不能计为真实完整源。训练不能补齐传感器、inverse metadata 或现场单位。历史 24 个错误接受由统一安全逻辑修复，无需训练扩大接受范围。

本轮未训练 Retriever / Classifier，未用测试集调参，无新模型权重与伪造训练指标。后续若取得可信原始数据及独立标签，并确认真实等价映射仍无法召回，再进入 TRAIN_NOW。
''')
write('real_dataset_candidates_post_safety.md',f'''# 安全修复后的真实候选预检

沿用 30 个已登记来源的完整 GT/来源元数据，重新运行映射；不是重新下载并独立认证 30 份数据。完整 schema、来源、单位与已有原文件 SHA 见 real_field_ground_truth.json；当前接受 trace 见 datasets/field_acceptance_safety/after.json。

{table(['scene','dataset','source type','GT coverage','contract','usable','reject reason'],[[c['scenario'],c['name'],gt['datasets'][i]['source_type'],f"{c['matched_required_count']}/{c['required_field_count']}",c['classification'],'yes' if c['classification']=='CAN_RUN_NOW' else 'no','—' if c['classification']=='CAN_RUN_NOW' else '缺物理变量/单位/采样/源文件，详见逐字段GT'] for i,c in enumerate(coverage)])}

本次有限联网补充：

| scene | dataset | source | coverage | usable | 原因 |
| --- | --- | --- | --- | --- | --- |
| debutanizer | Ujjwal-1267 镜像 | research GitHub | 0/9 可核验物理契约 | no | 2394×8，U1…U7/y，文件声明 y 已移 8 样本；无可信单位/inverse/绝对时间证据 |
| dryer | HPD TF1 v3 | university Mendeley，CC BY 4.0 | 未提供可核验过程表 | no | 设备硬件资料，不能当连续测量数据 |
| dryer | HPD TF3+ v2 | university Mendeley，CC BY 4.0 | 未提供可核验过程表 | no | CAD/设备设计条目，不能证明 required 测点 |

[Ujjwal 源文件](https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor/blob/main/data/debutanizer_data.txt)已下载到 runtime/data_validation/post_safety，原文头部明确时间移位；不二次移位、不推断采样秒数。授权再分发未核验，未推送原文件。

[HPD TF1](https://data.mendeley.com/datasets/g9w6ct4cgk/3)描述实验干燥器硬件；[HPD TF3+](https://data.mendeley.com/datasets/vg7c8dh365/2)归类为 CAD。页面没有提供本任务所需的同步过程列、rows、target、缺失/常数率、采样时间与 inverse metadata，因此这些指标为未知，不能填零，也不能当合格数据进入 Pipeline。

下载镜像的数值规模/缺失/常数统计记录在 datasets/field_acceptance_safety/new_candidate_preflight.json；范围仅作数据尺度记录，不作为身份或可逆性证明。没有跨实验拼接，也没有用 synthetic 替代。
''')
for name,scene,detail in [('debutanizer_real_pipeline_post_safety.md','debutanizer_column','LostRunes 物理契约 2/9，实际自动 required=1；Fortuna 缺单位和 inverse，补充镜像没有解决。'),('dryer_real_pipeline_post_safety.md','industrial_dryer','DAISY 物理契约 0/7，工艺输入/输出不满足当前 required；新硬件资料不是测量表。')]:
 write(name,f'''# {scene} 真实 Pipeline

Pipeline=UNAVAILABLE；Modeling=NOT_EXECUTED；run_id=null。

{detail}

安全映射和候选预检已运行；数据不满足完整物理契约，因此没有启动 12 个数值 Executor。无 mock/假字段/跨来源拼接。保留现有统一 Skill 架构，不删 required、不改场景模板、不训练把不同测点学成等价。

只有同来源、同实验、同步时间上下文且字段与单位/采样可追溯的数据，才能解锁真实数值验收。
''')
write('three_scene_final_pipeline_acceptance.md',f'''# 三场景最终 Pipeline 验收

| Scene | Physical coverage | Pipeline | Modeling |
| --- | --- | --- | --- |
| blast_furnace | 6/6 | PASS | PARTIAL |
| debutanizer_column（LostRunes） | 2/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer（DAISY） | 0/7 | UNAVAILABLE | NOT_EXECUTED |

高炉本轮只做一次专门固定回归：run_id={bf['run_id']}，skill_run_id={bf['skill_run_id']}，mode=md。
数据 SHA256：{bf['dataset_sha256']}。

{table(['比较项','与固定基线一致'],bf['comparison'].items())}

{table(['Skill','状态','executor invoked'],[(e['skill_id'],e['status'],e['audit']['executor_invoked']) for e in bf['executions']])}

各节点的 manifest、executor module、parameters、metrics、evidence、audit 与 artifact 哈希见 three_scene_final_runtime.json。read 状态的组件也有实际调用 audit，不把规划当执行；SNR 部分指标为 partial。Modeling 独立保持 PARTIAL，不等于模型可投产。

第 2 项 PARTIAL：架构同 Registry/Executor/算法已通过，但两场景真实数据未满足契约，三场景真实 12 Skill Pipeline 尚未全部完成。
''')
write('remaining_real_data_gaps_final.md','''# 最终结论与剩余缺口

1. 当前标准化引擎所有最终接受路径都进入 final_field_acceptance_gate；人工覆盖和离线逆变换也已接入，去重不能复活失败候选。
2. alias 不再无条件绕过物理冲突；正确显式别名继续采用可信 Registry 身份/单位依据。
3. normalization mapping 需要场景绑定的身份、单位、缩放证据，离线恢复还校验源哈希与公式；不能凭列序或范围接受。
4. 历史脱丁烷 24/43 错误接受剩余 0/43；原 25 个接受变为 1 个正确接受、38 review、4 reject。
5. Critical False Auto Accept=0（限定已评测真实 GT 样本，非无限范围保证）。
6. 现有已正确接受 GT 字段新增 false reject=0；三个指定别名正例保留，高炉 32/32 列仍正确接受。未知非可信字段会更保守，不保证所有未知场景无过度复核。
7. 当前两个代表源合计 7 个物理测点缺口、7 个证据待复核项；1 个有证据时间元数据列未自动接入。高价值可学习识别缺口 0。LostRunes=MIXED_LIMITATION，DAISY=DATA_LIMITED。只有文献而没有原文件的记录不计成缺传感器事实。
8. 字段训练 NOT_NEEDED_CURRENTLY；本轮不训练、不调阈值。
9. 脱丁烷塔 Pipeline UNAVAILABLE。
10. 工业干燥机 Pipeline UNAVAILABLE。
11. 高炉 Pipeline PASS，Modeling PARTIAL。
12. 三场景真实 Pipeline 尚未全部完成。
13. 图中第 2 项 PARTIAL。

剩余风险：可信 alias 和点位词典仍需要配置治理；自然语言词义检查无法证明所有现场物理事实；caller metadata 的来源真实性不是程序自动认证；没有物理合同的场景保留显式的 Registry 信任依据；真实源不足不能用训练解决。保护门禁与泛化准确率不可混为一谈。

修改业务文件仅 engine.py、physical_semantics.py、dataset_evidence.py；新增 final acceptance 专项测试、评测/报告脚本；更新 4 条与新安全要求冲突的旧断言。未改 Skill Runtime、Loader、Registry、Planner、SceneContext、12 算法、前端架构、字段 alias/required 或阈值。

GitHub 已 fetch 核对，基线 eb240e8 与 origin/main 一致；本轮未提交推送，既有本地修改保留。详见 full_regression_acceptance.md。
''')
print('Post-safety reports rendered.')
