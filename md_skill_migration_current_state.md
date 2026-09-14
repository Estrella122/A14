# Skill 迁移现状审计

## 修改前

1. 定义：catalog.SkillDefinition / SKILLS 提供 30 个业务 Skill 的 id、name、category、description、triggers、depends_on、handler、version、场景/任务分类、workflow_scope、scope、references 等；contracts.SKILL_CONTRACTS 另行定义执行器和 artifact 契约。
2. 注册：catalog.SKILL_MAP 静态构造。skill_loader 发现说明文档，但大多数文档只有 name/business_skill_id/executor 等轻量字段，不能独立注册并执行。
3. 选择：agent_api → services.agent_chat → runtime.plan_skills → TaskSpec、routing 召回、Skill/Capability Resolver；工业分析文档及 business Skill 文档随后注入 agent_context。
4. 执行：execute_skill_plan 调 industrial-analysis 或 execution_plan 分组后的 core executor。不同展示 Skill 可能共享一个阶段；不能把所有成功展示行都理解成独立算法执行。
5. 算法：分段/SNR 在 integrations/data_cleaning；时滞、共线性及 ARX 在 integrations/identification；core/services/pipeline 和 core_executors 提供阶段适配。
6. evidence read：CSV 资产、导出、审计通常读已有结果；其他 compute Skill 在 analyze 路径也可能只读 snapshot。execution_state/activity/algorithm_invoked 已用于区分。

## 修改后

- Loader + Registry 以四个新版 SKILL.md 为注册事实来源；同 ID 的旧定义仅作为 legacy 兼容资料。其余 26 项尚未迁移。
- YAML 管理注册、requires/produces、依赖、参数、执行器和质量边界；正文参与相关度评分并注入 Agent。
- 四项可在纯 md 模式规划和调用；动态 import 使用已验证的 manifest module/function。算法不复制。
- catalog 未删除；全流程和混合未迁移工作流保留原执行路径并明确 fallback。

## 不可破坏的接口

保留 /api/agent/skills/、/plans/、/skill-runs/、/skill-runs/<id>/、/events/、/chat/、/chat/live/；新增 /skills/<skill_id>/。
保留 plan_id/run_id/objective/mode/steps/direct_skill_ids/analysis，以及 executions 的 status/activity/execution_state/metrics/artifacts/evidence/warnings，保留 summary 和 live event 协议。
MD 候选补齐 candidate/final_score/status 等前端可观测性字段；前端仅优先显示 API display_name。

## 30 项清单

下表“原执行模式”来自原 contract，表示具有何种执行入口，不表示每次请求均会计算。共享阶段和只读路径仍由 execution_state 显式区分。

| Skill | 原执行器 | 原执行模式 | 本次注册来源 |
|---|---|---|---|
| industrial_intent_parser | task_understanding | orchestrate | legacy catalog |
| equipment_entity_resolver | task_understanding | orchestrate | legacy catalog |
| constraint_parameter_extractor | task_understanding | orchestrate | legacy catalog |
| skill_capability_matcher | routing | orchestrate | legacy catalog |
| workflow_dag_planner | planning | orchestrate | legacy catalog |
| execution_supervisor_replanner | supervision | compute | legacy catalog |
| csv_asset_manager | asset | evidence | legacy catalog |
| industrial_simulation_generator | simulation | compute | legacy catalog |
| dataset_scenario_profiler | standardization | compute | legacy catalog |
| semantic_field_unit_standardizer | standardization | compute | legacy catalog |
| time_axis_alignment_resampler | cleaning | compute | legacy catalog |
| missing_anomaly_cleaner | missing_anomaly_cleaner | compute | legacy catalog |
| steady_transient_state_detector | segmentation | compute | legacy catalog |
| signal_noise_ratio_estimator | segmentation | compute | SKILL.md |
| high_snr_dynamic_segment_extractor | high_snr_dynamic_segment_extractor | compute | legacy catalog |
| segment_quality_scorer_ranker | segmentation | compute | legacy catalog |
| time_delay_estimator_compensator | time_delay_estimator_compensator | compute | SKILL.md |
| collinearity_detector_reducer | industrial-analysis | compute | SKILL.md |
| modeling_dataset_assembler | modeling | compute | legacy catalog |
| arx_structure_order_selector | modeling | compute | SKILL.md |
| system_identification_trainer | system_identification_trainer | compute | legacy catalog |
| multi_model_benchmark | modeling | compute | legacy catalog |
| model_diagnostics_evaluator | model_diagnostics_evaluator | compute | legacy catalog |
| closed_loop_preprocessing_optimizer | closed_loop_preprocessing_optimizer | compute | legacy catalog |
| engineering_result_interpreter | review | evidence | legacy catalog |
| engineering_visualization_builder | visualization | compute | legacy catalog |
| expert_report_writer | report | compute | legacy catalog |
| final_artifact_exporter | artifact | evidence | legacy catalog |
| experiment_tracker_comparator | experiment | compute | legacy catalog |
| evidence_audit_reproducer | audit | evidence | legacy catalog |

## 本次新增核心文件

core/skills/loader.py、registry.py、md_planning.py、md_adapter.py、md_response.py；四个 Skill 目录的 SKILL.md 与 executor.py；core/test_skill_md_runtime.py。

## 最小修改现有文件

core/apps.py（启动校验）、runtime.py（MD 优先/兼容分支/审计）、skill_loader.py（兼容发现新文档）、contracts.py（轮次收据接口）、agent_api.py/urls.py（详情 API）、services/agent_chat.py（绑定本次结果）、integrations/identification/validated_modeling.py（抽取共享搜索循环）、frontend/src/utils/runtimeObservability.js（API 名称）、requirements.txt/.env.example。

新增 PyYAML 6.x 安全解析 YAML。没有改动工业场景 Registry、字段统一、3D 场景或外部 SkillOS。
