# 现状扫描：A14 Skill 清单（初始状态）

本次仅做结构化扫描，不改动执行逻辑。

## A. 工程级核心知识
- `industrial_intent_parser`：承接用户目标理解与模式化解析。
- `skill_capability_matcher`：把意图映射到能力集合。
- `workflow_dag_planner`：能力链路组装。
- `execution_supervisor_replanner`：执行门控与重规划。

## B. 工程级 workflow
- 上述 orchestration 类 Skills 均参与任务编排。
- 与 `agent_chat/chat`、`skills/routing.py`、`skills/runtime.py`耦合。

## C. 通用工业分析能力（当前已具备的可复用能力）
- `dataset_scenario_profiler`（场景画像）
- `semantic_field_unit_standardizer`（字段/单位标准化）
- `time_axis_alignment_resampler`、`missing_anomaly_cleaner`（数据治理）
- `steady_transient_state_detector`、`signal_noise_ratio_estimator`、`high_snr_dynamic_segment_extractor`
- `time_delay_estimator_compensator`、`collinearity_detector_reducer`
- `modeling_dataset_assembler`、`arx_structure_order_selector`、`system_identification_trainer`
- `multi_model_benchmark`、`model_diagnostics_evaluator`、`closed_loop_preprocessing_optimizer`

## D. 通用基础能力
- `csv_asset_manager`、`industrial_simulation_generator`、`evidence_audit_reproducer`
- `engineering_result_interpreter`、`engineering_visualization_builder`
- `expert_report_writer`、`final_artifact_exporter`、`experiment_tracker_comparator`

## E. 重复内容
- 未发现同名重复；未发现与现有30个技能重复实现的同义技能。

## F. 场景专属知识
- `equipment_entity_resolver`、`dataset_scenario_profiler`对场景/设备有明显硬编码倾向；
- `agent_chat._scenario_family` 也有场景名映射。

## G. 可废弃内容
- 暂未识别可直接废弃的 Skill；当前“可观测能力”与“业务逻辑”已较好解耦，适合逐步重构。

## 技能文件位置、用途、模块调用、输入/输出、引用关系（静态扫描）

- `core/skills/catalog.py`
  - 用途：30个 skill 注册与分类。
  - 输入：`id/name/category/description/triggers/depends_on/...`
  - 输出：`list_skills()` 暴露 `public()` 结构。
  - 被调用：`runtime.py`, `routing.py`, `services/agent_chat.py`, `agent_api.py`, `tests`。
  - 场景/字段硬编码：`dataset_scenario_profiler` 与 `equipment_entity_resolver` 文案中带场景关键词。

- `core/skills/routing.py`
  - 用途：执行/分析模式路由、候选 skill 选择。
  - 输入：用户 `message`。
  - 输出：`direct`/`mode`/`decisions`/`source`。
  - 被调用：`runtime.py`。
  - 无场景硬编码。

- `core/skills/runtime.py`
  - 用途：实体抽取、参数提取、能力选择、依赖补齐、计划产物、Skill执行。
  - 输入：`message`、`run_id`/`snapshot`。
  - 输出：`analysis`/`entities`/`parameters`/`steps`/`executions`。
  - 被调用：`agent_chat.py`、`agent_api.py`。
  - 场景硬编码：`_entities` 里有场景/设备关键词与 `if/else`。

- `core/services/agent_chat.py`
  - 用途：用户对话意图判定 + 与 pipeline 重跑门禁。
  - 场景硬编码：`_scenario_family`。

- `core/agent_api.py`
  - 用途：对外公开 `/api/agent/*` 路径。

## 重构风险边界
- 现有 API 契约（`api/agent/skills`、`api/agent/plans`、`/api/agent/skill-runs`）强约束 30 个 Skill 与场景广告字段，因此改造应只增量增加 metadata 与计划元数据，不能直接变更既有公开字段。
