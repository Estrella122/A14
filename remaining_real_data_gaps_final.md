# 最终结论与剩余缺口

1. 当前标准化引擎所有最终接受路径都进入 final_field_acceptance_gate；人工覆盖和离线逆变换也已接入，去重不能复活失败候选。
2. alias 不再无条件绕过物理冲突；正确显式别名继续采用可信 Registry 身份/单位依据。
3. normalization mapping 需要场景绑定的身份、单位、缩放证据，离线恢复还校验源哈希与公式；不能凭列序或范围接受。
4. 历史脱丁烷 24/43 错误接受剩余 0/43；原 25 个接受变为 1 个正确接受、38 review、4 reject。
5. Critical False Auto Accept=0（限定已评测真实 GT 样本，非无限范围保你现在继续处理当前 A14 项目。

这是图中第 2 项的“最终收尾任务”。

当前目标只有两个：

1. 找到并接入满足当前物理字段契约的真实/可信公开脱丁烷塔数据
2. 找到并接入满足当前物理字段契约的真实/可信公开工业干燥器数据

然后：

直接使用当前已经稳定的 12 Skill MD Pipeline 做最终真实数值验收。

==================================================
0. 当前已完成状态
==================================================

以下内容已经通过，不要重做：

- Markdown Skill Runtime
- Skill Loader
- Skill Registry
- Planner
- SceneContext
- 12 个核心 MD Skill
- 三场景同一 Registry
- 三场景同一 Executor
- 三场景同一核心算法
- final_field_acceptance_gate
- alias / normalization / model / deterministic mapping 安全收口
- Planner execute / evidence_only
- 后端完整回归 0 failures/errors
- 前端 test/lint/build PASS
- blast_furnace：
  - Contract PASS
  - 12 Skill Pipeline PASS
  - 固定真实/衍生真实数据回归稳定

当前未完成：

A. debutanizer_column
- Contract FAIL
- 当前最佳真实候选只有少量 required 字段匹配
- Pipeline UNAVAILABLE
- 12 Skill 未执行

B. industrial_dryer
- Contract FAIL
- 当前真实候选 required coverage 不足
- Pipeline UNAVAILABLE
- 当前真正可运行数据仍主要是 synthetic

==================================================
1. 本阶段最终目标
==================================================

最终必须尝试实现：

debutanizer_column:
REAL / PUBLIC_REAL_PROCESS / PUBLIC_EXPERIMENT
→ Contract PASS
→ 12 Skill Pipeline PASS

industrial_dryer:
REAL / PUBLIC_REAL_PROCESS / PUBLIC_EXPERIMENT
→ Contract PASS
→ 12 Skill Pipeline PASS

如果两者都成功：

图中第 2 项：
DONE

如果任一场景仍 UNAVAILABLE：

图中第 2 项：
PARTIAL

==================================================
2. 严禁事项
==================================================

不要修改：

- Runtime
- Loader
- Registry
- Planner
- SceneContext
- 12 个 Skill 算法
- 字段安全门禁
- required 字段
- alias
- 模型权重
- 阈值
- blast_furnace 逻辑
- 前端架构

禁止：

1. 用 synthetic 冒充真实工业数据
2. 把不同实验/不同时间源拼成一个数据集
3. 伪造缺失传感器
4. 用错误测点替代 required 字段
5. 根据数值范围猜字段身份
6. 根据列顺序猜字段
7. 没有 inverse metadata 就反归一化
8. 为了跑通把 required 改 optional
9. 为了模型好看修改 baseline
10. 根据 test 选择数据或参数
11. 训练模型强行补不存在的测点
12. 用 REVIEW_REQUIRED 字段冒充已确认字段

==================================================
3. 数据可信度分级
==================================================

所有候选必须标记：

REAL_PLANT
PUBLIC_REAL_PROCESS
PUBLIC_EXPERIMENT
BENCHMARK_REAL
DERIVED_REAL
SYNTHETIC
UNKNOWN

最终验收优先级：

REAL_PLANT
>
PUBLIC_REAL_PROCESS
>
PUBLIC_EXPERIMENT
>
BENCHMARK_REAL
>
DERIVED_REAL

SYNTHETIC 不得作为最终第 2 项 DONE 的依据。

==================================================
4. 先读取当前真实数据需求
==================================================

先从仓库当前配置真实读取：

integrations/standardization/standards/scenarios/debutanizer_column/
integrations/standardization/standards/scenarios/industrial_dryer/

不要根据本提示词自行假设。

对每个场景列出：

- required fields
- optional fields
- target
- input roles
- units
- physical semantics
- sampling requirements
- constraints
- aliases
- accepted metadata

生成：

final_real_data_contracts.md

==================================================
5. Phase A：本地资源最终盘点
==================================================

搜索：

- datasets/
- datasets/real_validation/
- training/
- 演示数据/
- runtime/
- runtime/data_validation/
- reports/
- docs/
- integrations/
- SOURCE.md
- transformation_manifest.json
- 之前所有下载缓存
- 之前所有候选报告
- LostRunes / Fortuna / DAISY / 烟草数据相关文件

建立：

final_local_data_inventory.md

避免重复下载和重复搜索。

==================================================
6. Phase B：联网搜索真实数据
==================================================

如果当前环境允许联网：

优先搜索完整原始数据，而不是只看论文描述。

--------------------------------------------------
6.1 脱丁烷塔搜索
--------------------------------------------------

搜索方向：

- debutanizer column raw dataset
- debutanizer real plant process data
- debutanizer refinery process dataset
- debutanizer soft sensor raw data
- debutanizer temperature pressure reflux dataset
- debutanizer column industrial benchmark raw variables
- debutanizer process historian data
- debutanizer university raw dataset
- debutanizer process identification dataset

优先来源：

- university repository
- Zenodo
- Figshare
- Mendeley Data
- institutional repository
- IEEE DataPort
- ScienceDirect supplementary
- paper companion GitHub
- official research lab
- process control benchmark repository

--------------------------------------------------
6.2 工业干燥器搜索
--------------------------------------------------

搜索方向：

- industrial dryer raw process dataset
- rotary dryer real plant data
- industrial drying real process dataset
- dryer moisture control raw data
- industrial drying temperature humidity air flow dataset
- rotary dryer product moisture dataset
- tobacco drying production line dataset
- industrial dryer soft sensor dataset
- drying process system identification dataset

同样优先：

- research institution
- university
- official project page
- paper supplementary
- public scientific repository

==================================================
7. 不要把“论文里提到数据”当成实际数据
==================================================

一个候选只有满足：

- 原始文件实际取得
- 文件可读取
- hash 可记录
- header 可读取
- source 可追溯
- 字段说明可验证

才算：

EXECUTABLE_CANDIDATE

如果只有论文描述但没有文件：

SOURCE_REFERENCE_ONLY

不能进入 Pipeline。

==================================================
8. 对每个候选建立来源档案
==================================================

记录：

scene
dataset_name
source_url
publisher
paper/project
license
source_type
download_date
original_filename
sha256
rows
columns
time coverage
sampling interval
field descriptions
units
target
normalization status
inverse metadata
source confidence

生成：

final_real_dataset_candidates.md

==================================================
9. 自动预检
==================================================

新增或复用：

tools/precheck_real_dataset.py

对每个候选自动检查：

1. 文件可读取
2. 行数
3. 列数
4. 时间字段
5. sampling interval
6. target
7. required fields
8. units
9. physical semantics
10. missing ratio
11. constant ratio
12. duplicate timestamps
13. normalization state
14. inverse metadata
15. field acceptance gate
16. contract coverage

输出：

dataset_precheck.json

==================================================
10. 候选分类
==================================================

每个候选最终分类：

ELIGIBLE
REVIEW_BLOCKED
DATA_LIMITED
METADATA_LIMITED
NORMALIZATION_BLOCKED
SOURCE_ONLY
UNUSABLE

只有：

ELIGIBLE

才允许进入 12 Skill Pipeline。

==================================================
11. 脱丁烷塔特别要求
==================================================

必须严格使用当前仓库实际契约。

重点确认：

- timestamp
- target
- 两处塔底温度
- 塔顶温度
- 第六塔板温度
- 压力
- 回流变量
- 流量变量
- sampling information
- units

不能：

Reboiler outlet temp
→ bottom column temp

不能：

Feed flow
→ downstream/product flow

所有映射必须经过：

final_field_acceptance_gate

==================================================
12. 脱丁烷归一化候选
==================================================

如果数据是 normalized：

只有存在：

- field identity
- normalization method
- per-field scaling parameters
- original units
- source hash
- source documentation

才允许 inverse transform。

否则：

NORMALIZATION_BLOCKED

==================================================
13. 工业干燥器特别要求
==================================================

读取实际当前契约。

优先真实变量可能包括：

- timestamp
- inlet temperature
- outlet temperature
- humidity
- air flow
- feed rate
- heater power / energy
- pressure
- product moisture / outlet moisture

但最终以仓库当前 required contract 为准。

==================================================
14. DAISY / 烟草候选最终核查
==================================================

必须重新检查当前最可信候选：

DAISY
烟草生产线数据
公开实验数据

重点判断：

A. 字段真的存在，只是命名不同
→ 可以通过可信映射解决

B. 字段根本不存在
→ DATA_LIMITED

不能为了使用 DAISY 而修改当前工业干燥器契约。

==================================================
15. 不允许跨数据集补字段
==================================================

禁止：

dataset A 温度
+
dataset B 湿度
+
dataset C target

拼成一个“真实数据集”。

最终验收必须来自：

同一来源
同一过程
同一实验/生产线
同一时间上下文

==================================================
16. 可复现数据准备
==================================================

如果需要：

- rename
- unit conversion
- timestamp parse
- documented inverse transform
- filter unusable rows

必须写脚本。

例如：

tools/prepare_debutanizer_final_data.py
tools/prepare_dryer_final_data.py

输出：

transformation_manifest.json

至少记录：

source_hash
output_hash
renames
unit_conversions
time operations
inverse transform
row filters
dropped columns
warnings

==================================================
17. 禁止人工静默改 CSV
==================================================

不能通过 Excel 手动改完字段后直接使用。

所有改变都必须：

scripted
reproducible
auditable

==================================================
18. Contract PASS 标准
==================================================

Contract PASS 要求：

required_count == matched_required_count

且：

review_required = 0
missing_required = 0
no_equivalent_required = 0

关键字段不能只靠低证据映射。

==================================================
19. 找到 ELIGIBLE 数据后直接跑现有 Pipeline
==================================================

必须：

SKILL_MANIFEST_MODE=md

调用当前统一场景 Pipeline。

不能新增：

debutanizer_final_pipeline.py
dryer_final_pipeline.py

==================================================
20. 12 Skill 完整执行
==================================================

必须执行：

1. time_axis_alignment_resampler
2. missing_anomaly_cleaner
3. signal_noise_ratio_estimator
4. steady_transient_state_detector
5. high_snr_dynamic_segment_extractor
6. segment_quality_scorer_ranker
7. time_delay_estimator_compensator
8. collinearity_detector_reducer
9. modeling_dataset_assembler
10. arx_structure_order_selector
11. system_identification_trainer
12. model_diagnostics_evaluator

==================================================
21. Pipeline PASS 标准
==================================================

必须满足：

- Contract PASS
- SceneContext 成功
- 12 个节点全部有真实运行回执
- executor_invoked = true
- 不存在 blocked
- 不存在 unavailable
- metrics/evidence/warnings 可追溯
- 不使用 mock
- 不伪造字段
- 不回退到 legacy scene pipeline

==================================================
22. read 节点说明
==================================================

如果某个 Skill 合理复用当前同一次 Pipeline 内前置真实产物：

可以 status=read

但必须：

executor_invoked / artifact provenance 可审计

不能把旧历史产物冒充本次执行。

==================================================
23. Modeling Quality 独立评价
==================================================

Pipeline PASS 后，再单独评价：

Modeling:
PASS
PARTIAL
FAIL

至少包括：

validation RMSE
test RMSE
persistence baseline
relative improvement
AR vs ARX
stability
10-step prediction
free simulation
residual
whiteness if available

Pipeline PASS 不要求 Modeling PASS。

==================================================
24. Test leakage guard
==================================================

必须继续保持：

60/20/20 或当前固定协议

训练：
只读 train

模型选择：
train + validation

test：
冻结模型后单次执行

禁止根据 test：

- 换参数
- 换数据版本
- 换模型
- 换窗口
- 换 lag

==================================================
25. 高炉最终固定对照
==================================================

高炉不再改。

只运行一次固定回归。

核对：

dataset_sha256
skill_ids
executor_modules
metrics

必须和既有固定基线一致。

==================================================
26. 如果仍找不到合格脱丁烷数据
==================================================

停止继续无限搜索。

生成：

debutanizer_final_data_requirement.md

内容：

- required fields
- exact physical meaning
- units
- acceptable aliases
- sampling interval
- minimum duration
- minimum rows
- target
- allowed missingness
- required metadata
- normalization metadata requirements
- source evidence requirements

==================================================
27. 如果仍找不到合格干燥器数据
==================================================

同样生成：

industrial_dryer_final_data_requirement.md

让后续数据提供方可以直接按规格交付。

==================================================
28. 搜索停止条件
==================================================

不要无限搜索互联网。

达到以下任一情况停止：

A. 找到 ELIGIBLE 数据
B. 搜完主要科学数据平台且没有合格候选
C. 数据存在但许可/原文件无法获得
D. 当前契约本身需要特定企业传感器组合，公开数据几乎不存在

必须记录：

search_stop_reason

==================================================
29. 测试
==================================================

新增/更新：

1. test_final_debutanizer_real_contract
2. test_final_debutanizer_real_pipeline
3. test_final_dryer_real_contract
4. test_final_dryer_real_pipeline
5. test_source_manifest_integrity
6. test_real_data_hash
7. test_no_cross_dataset_splice
8. test_no_fake_required_fields
9. test_md_mode_only
10. test_no_legacy_fallback
11. test_12_executor_receipts
12. test_test_leakage_guard

==================================================
30. 全量回归
==================================================

最终运行：

manage.py test core

目标：

0 failures
0 errors

运行：

npm test
npm run lint
npm run build
git diff --check

不得新增 skip 掩盖数据问题。

数据不可得相关已有 skip 可以继续存在，但必须解释。

==================================================
31. 最终交付文件
==================================================

必须生成：

1. final_real_data_contracts.md
2. final_local_data_inventory.md
3. final_real_dataset_candidates.md
4. debutanizer_final_real_acceptance.md
5. industrial_dryer_final_real_acceptance.md
6. three_scene_final_real_acceptance.md
7. three_scene_final_real_runtime.json
8. real_data_search_stop_report.md
9. final_remaining_gaps.md
10. final_regression_report.md

如数据仍不足：

11. debutanizer_final_data_requirement.md
12. industrial_dryer_final_data_requirement.md

==================================================
32. 最终验收矩阵
==================================================

输出：

| Scene | Source | Confidence | Contract | Pipeline | Modeling |
|---|---|---|---|---|---|
| blast_furnace | ... | DERIVED_REAL/REAL | PASS | PASS | PARTIAL/PASS |
| debutanizer_column | ... | ... | PASS/FAIL | PASS/UNAVAILABLE | ... |
| industrial_dryer | ... | ... | PASS/FAIL | PASS/UNAVAILABLE | ... |

同时输出：

- 通用 Skill 架构：PASS/FAIL
- 统一字段安全门禁：PASS/FAIL
- 三场景真实数据契约：PASS/PARTIAL/FAIL
- 三场景 12 Skill Pipeline：PASS/PARTIAL/FAIL

==================================================
33. 图中第 2 项 DONE 规则
==================================================

图中：

“三个场景算法跑通（场景模块改成通用 Skill）”

只有满足：

1. 三场景都使用当前通用 Skill
2. 三场景同 Registry
3. 三场景同 Executor
4. 三场景同核心算法
5. 三场景都使用真实/可信公开实测数据
6. 三场景 Contract PASS
7. 三场景完整 12 Skill 数值 Pipeline PASS

才可以：

DONE

Modeling 可以 PARTIAL。

如果任一场景：

UNAVAILABLE

则：

PARTIAL

==================================================
34. 最终必须明确回答
==================================================

最后必须回答：

1. 是否最终找到合格脱丁烷真实数据？
2. 来源是什么？
3. license 是什么？
4. required coverage 是多少？
5. Contract 是否 PASS？
6. 12 Skill 是否全部实际执行？

7. 是否最终找到合格工业干燥器真实数据？
8. 来源是什么？
9. license 是什么？
10. required coverage 是多少？
11. Contract 是否 PASS？
12. 12 Skill 是否全部实际执行？

13. 高炉是否仍保持固定回归一致？

14. 是否需要训练字段 Agent？
   当前预期仍应是 NOT_NEEDED_CURRENTLY，除非新数据产生真实 AGENT_LIMITED 证据。

15. 三场景真实 Pipeline 是否全部 PASS？

16. 图中第 2 项：
DONE / PARTIAL / FAIL

==================================================
35. 最重要原则
==================================================

现在不是“把代码改到能吃下任何 CSV”。

而是：

找真正符合物理场景的真实数据，
让已经完成的 A14 通用 Skill 系统去处理它。

如果公开数据本身不具备 required 传感器：

必须保持 UNAVAILABLE。

不能修改系统去迁就错误数据。

如果最终公开数据确实无法满足：

如实输出数据需求规范。

这比伪造 DONE 更有工程价值。

开始执行。证）。
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
