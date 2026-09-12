# 核心 Skill Executor 迁移现状审计

审计基线：`daec2e3`。本报告在 Executor 迁移代码之前生成，结论来自 `core/skills/catalog.py`、`core/skills/runtime.py`、`core/skills/executor.py` 与 `core/services/pipeline.py` 的真实调用链。

## 总体现状

当前唯一注册的真实 Executor 是 `industrial-analysis`。其余核心 Skill 在 `execute_skill_plan()` 中主要读取既有 Pipeline snapshot；需要执行时，`agent_chat.py` 仍通过 `skill_id → stop_after → rerun_pipeline() → run_pipeline()` 触发整束 Pipeline。`pipeline.py` 内已有经过验证的阶段函数，但它们仍是 Pipeline 私有函数，尚未作为稳定 service 接口提供给 Skill Runtime。

| Skill | 当前执行方式 | 真 Executor | Pipeline 依赖 | 迁移难度 |
|---|---|---:|---|---|
| `dataset_scenario_profiler` / `semantic_field_unit_standardizer` | `_standardize()` | 否 | 输入 CSV、Registry、point semantics、运行目录 | 中 |
| `time_axis_alignment_resampler` / `missing_anomaly_cleaner` | `_clean()` | 否 | 标准化 DataFrame、dictionary、切分目录 | 中高 |
| `steady_transient_state_detector` / `signal_noise_ratio_estimator` / `high_snr_dynamic_segment_extractor` / `segment_quality_scorer_ranker` | `_clean()` 内合并执行 | 否 | 清洗后的训练分区、窗口参数 | 高 |
| `modeling_dataset_assembler` / `arx_structure_order_selector` / `system_identification_trainer` / `multi_model_benchmark` / `model_diagnostics_evaluator` | `_model()` | 否 | cleaning artifacts、dictionary、切分清单 | 高 |
| `closed_loop_preprocessing_optimizer` | `_optimize_real_data()` | 否 | 真实清洗数据、segments、目标、模型边界 | 很高 |
| `engineering_result_interpreter` | `_review()` | 否 | 标准化、清洗、模型证据 | 中 |
| `expert_report_writer` | `_analysis_report()` | 否 | 前序结果与 optimization；写 Markdown | 中 |
| `final_artifact_exporter` | snapshot artifact 读取 | 否（reader） | 既有 artifact | 低 |

## 逐项审计

### 标准化

- Skill ID：`dataset_scenario_profiler`、`semantic_field_unit_standardizer`
- capability：场景识别、字段语义映射、单位处理。
- 当前入口 / stage：`core.services.pipeline._standardize()` / `standardization`。
- 输入：源 CSV 路径、`scenario_id`、instruction、overrides、运行目录。
- 输出：标准化 DataFrame、scenario/detection/mapping/conversions/issues/data decision/dictionary/runtime trace。
- artifacts：`02_standardization/standardized.csv`、`mapping_report.csv`、`standardization_report.json`。
- 独立 service：底层已有 `StandardizationAgent.standardize()`；Pipeline glue 尚未抽离。
- 副作用：创建目录并写三个产物。
- snapshot：算法不依赖既有 snapshot；Pipeline 负责把结果写回 snapshot。
- stop_after / rerun：当前独立执行依赖 `stop_after=standardization` 和 `rerun_pipeline()`。
- 可抽取性：高。应直接封装现有 Agent，并保持 Registry、point semantics 与自动场景参数不变。
- 风险：场景上下文污染、路径和 artifact 相对路径、DataFrame 与文件双输入的一致性。

### 数据清洗

- Skill ID：`time_axis_alignment_resampler`、`missing_anomaly_cleaner`
- capability：时间对齐、缺失/异常处理、按时间冻结 60/20/20 分区。
- 当前入口 / stage：`core.services.pipeline._clean()` / `cleaning`。
- 输入：标准化 DataFrame、dictionary、重采样周期、最大时滞、主输出及窗口参数。
- 输出：建模 DataFrame、segments DataFrame、质量报告。
- artifacts：train/validation/test/cleaned/modeling CSV、SNR、segments、split manifest、quality report。
- 独立 service：底层已有 `DataCleaningSelectionAgent`；Pipeline glue 尚未抽离。
- 副作用：写 `03_cleaning` 全套产物。
- snapshot：不要求 snapshot，但要求标准化结果与 dictionary。
- stop_after / rerun：当前执行依赖 `stop_after=cleaning`；会先重跑标准化。
- 可抽取性：中。清洗与分段目前耦合在同一函数。
- 风险：不得改变因果切分、不得跨分区填充、短数据门禁、原始采样周期保护。

### 动态/工况分段

- Skill ID：`steady_transient_state_detector`、`signal_noise_ratio_estimator`、`high_snr_dynamic_segment_extractor`、`segment_quality_scorer_ranker`
- capability：稳动态识别、SNR 代理估计、窗口筛选与排序。
- 当前入口 / stage：`_clean()` 内 `select_dynamic_segments()` / Pipeline `selection` 仅复用 cleaning 结果。
- 输入：训练分区、variable spec、窗口长度与步长。
- 输出：segments、等级、分数、SNR 证据、建模行集合。
- artifacts：`selected_dynamic_segments.csv`、`snr_estimates.csv`、`modeling_dataset.csv`。
- 独立 service：无单独 stage service；算法存在于 `DataCleaningSelectionAgent`。
- 副作用：由 `_clean()` 一并写盘。
- snapshot：需要清洗/标准化上下文，不要求完整 Pipeline snapshot。
- stop_after / rerun：当前只能通过 cleaning/selection stop_after 路径获得。
- 可抽取性：中低。应先把清洗结果和分段结果契约拆开，算法仍复用同一 Agent。
- 风险：窗口重叠解释、SNR 未标定边界、分区泄漏。

### 建模

- Skill ID：`modeling_dataset_assembler`、`arx_structure_order_selector`、`system_identification_trainer`、`multi_model_benchmark`、`model_diagnostics_evaluator`
- capability：组装数据、时滞/共线性、结构选择、训练、基线和诊断。
- 当前入口 / stage：`core.services.pipeline._model()` / `modeling`；全流程时也由 optimization 对候选调用。
- 输入：建模 DataFrame、dictionary、split manifest、validation CSV、max lag、主输出。
- 输出：模型配置、输入输出、训练/验证/测试指标、阶次搜索、诊断、响应分析、基线比较。
- artifacts：pipeline summary、VIF、diagnostics、response analysis、order search、fitted state、metrics、delays。
- 独立 service：底层已有 `run_validated_modeling()`；Pipeline glue 尚未抽离。
- 副作用：写 `04_modeling` 或候选目录。
- snapshot：需要 cleaning artifacts；可由显式输入替代。
- stop_after / rerun：当前单独训练依赖 `stop_after=modeling`，并重跑标准化和清洗。
- 可抽取性：中高。
- 风险：训练/验证/测试泄漏、基线比较缺失、输入角色与主输出选择、相对路径。

### 优化

- Skill ID：`closed_loop_preprocessing_optimizer`
- capability：在真实数据上搜索 top-k 与 max-lag 候选，以共同验证集评分，最终测试一次。
- 当前入口 / stage：`_optimize_real_data()` / `optimization`。
- 输入：真实 cleaned frame、segments、dictionary、初始模型信息、目标输出、搜索边界。
- 输出：iterations、最佳轮次、参数、验证分数、训练覆盖与最终模型。
- artifacts：optimization JSON、最佳候选模型产物。
- 独立 service：已有 `core/services/optimization.py` 提供搜索辅助；总流程仍在 Pipeline。
- 副作用：多候选目录与最终模型复制/写盘。
- snapshot：依赖真实前序 artifacts，但不应把 UI 项目场景当数据场景。
- stop_after / rerun：当前依赖全 Pipeline 到 optimization。
- 可抽取性：低，本次可先注册为带严格前置条件的 partial/blocked executor。
- 风险：绝不能在缺 objective/model/bounds/constraints 时生成 synthetic fallback；测试集只能评估一次。

### 评审

- Skill ID：`engineering_result_interpreter`
- capability：将已产生证据转为离线模型、软测量与闭环准入门判断。
- 当前入口 / stage：`_review()` / `review`。
- 输入：standardization、cleaning、modeling 结果。
- 输出：passed、conclusion、blockers、warnings、evidence、deployment readiness。
- artifact：`06_review/agent_review.json`。
- 独立 service：无；逻辑为确定性 Python 评审。
- 副作用：写 JSON。
- snapshot：只需前序结构化结果，不需重跑算法。
- stop_after / rerun：当前执行仍随 Pipeline 重跑。
- 可抽取性：高。
- 风险：必须保持 reader/reviewer 边界，不能重算模型或伪造缺失证据。

### 报告与导出

- Skill ID：`expert_report_writer`；`final_artifact_exporter` 为 reader/exporter。
- capability：把既有结果、证据和限制格式化为 Markdown；列出现有产物。
- 当前入口 / stage：`_analysis_report()` / `report`；导出器由 snapshot artifact 读取。
- 输入：snapshot 及标准化、清洗、建模、优化、评审结果。
- 输出：报告元数据或 artifact 列表。
- artifact：`07_delivery/analysis_report.md` 及已有产物引用。
- 独立 service：无。
- 副作用：报告写盘；导出读取无算法副作用。
- snapshot：强依赖既有执行结果。
- stop_after / rerun：报告生成当前随完整 Pipeline；导出不重跑。
- 可抽取性：高。
- 风险：缺少前序结果时必须 blocked；不得为写报告重新计算分析。

## 迁移边界

1. 保留 Catalog 的现有 Skill ID，不新建同义 Skill。
2. 先建立共享 stage service，让 Pipeline 与 Executor 调用同一实现。
3. Executor 只执行 ExecutionPlan 指定的最小 DAG；reader、review、report 不触发前序重算。
4. `hybrid` 仅对未迁移能力使用 Pipeline fallback，并记录原因；`skill_runtime` 对无 Executor 能力返回 unavailable。
5. `executed` 只统计真实 Executor 调用，snapshot 读取计为 read，规划节点计为 planned。
