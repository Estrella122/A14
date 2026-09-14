# 三场景 Skill 迁移验收

基于当前工作区执行；基线提交 13443c0，包含尚未提交的第一、二阶段改动。没有推送 GitHub。

## 验收矩阵

| 项目 | 结论 | 证据/限制 |
|---|---|---|
| A blast_furnace 主链 | PARTIAL | 完成清洗至模型诊断；部分 SNR 为 null |
| B debutanizer_column 主链 | PARTIAL | 标准化门禁阻断，运行状态 unavailable；未执行数值链 |
| C industrial_dryer 主链 | PARTIAL | 已有合成验收数据；无严格优质段，未优于 persistence |
| D 同一 Skill Registry | PASS | 纯 MD 同一组 12 个 ID/manifest |
| E 同一核心算法 | PASS（代码复用） | 同一 executor_module；脱丁烷数值调用仍未验证 |
| F 配置解析字段 | PASS | 三份既有 Registry 配置解析 timestamp/input/target/unit |
| G 通用 Skill 无场景硬编码 | PASS | executor 与 stage_adapters AST 检查无三场景常量分支 |
| H 统一 SkillResult | PASS | 三场景成功/部分/阻断记录结构一致 |
| I 纯 MD 模式 | PASS（Runtime） | 无 catalog 注册依赖；不等于所有数值步骤成功 |
| J API/前端兼容 | PASS（自动与 HTTP） | Django 真 HTTP + 后端回归 + 前端测试/构建；未做新视觉验收 |

## 实际运行

按干燥器 → 脱丁烷塔 → 高炉顺序，以同一问题“分析当前场景的数据质量并判断是否适合 ARX 建模。”调用 run_scene_skill_pipeline。没有使用 mock 替代数值算法，也没有把干燥器合成数据称为实测。

| 场景 | run_id | 状态 | 总耗时 ms | 数据来源 |
|---|---|---|---:|---|
| industrial_dryer | scene_7482954bfe16 | partial | 868.118 | 仓库已有合成验收数据；不是工厂实测数据 |
| debutanizer_column | scene_5f6849ceda86 | unavailable | 212.775 | 仓库归一化字段样本；逆缩放信息不足，物理字段门禁不通过 |
| blast_furnace | scene_efaa6651222e | partial | 1506.005 | 仓库 Mendeley 衍生真实数据；化验值按既有因果对齐处理 |

运行结果完整记录于 [three_scene_runtime_acceptance.json](three_scene_runtime_acceptance.json)，包含原文件绝对路径、SHA256、SceneContext、计划、manifest 路径/hash、executor、参数、每步 audit、指标、产物、警告与耗时。

## 每步结果

| Skill | 干燥器 | 脱丁烷塔 | 高炉 |
|---|---|---|---|
| time_axis_alignment_resampler | success | blocked | success |
| missing_anomaly_cleaner | success | blocked | success |
| signal_noise_ratio_estimator | success | blocked | partial |
| steady_transient_state_detector | success | blocked | success |
| high_snr_dynamic_segment_extractor | partial | blocked | success |
| segment_quality_scorer_ranker | read | blocked | read |
| time_delay_estimator_compensator | success | blocked | success |
| collinearity_detector_reducer | success | blocked | success |
| modeling_dataset_assembler | read | blocked | read |
| arx_structure_order_selector | success | blocked | success |
| system_identification_trainer | success | blocked | success |
| model_diagnostics_evaluator | partial | blocked | success |

blocked 是原 Runtime 的安全终态，入口将标准化拒绝映射为 unavailable，同时保留 runtime_status=blocked，未填造缺失指标。read 表示复用排序/组装产物，不计为算法重新执行。

## 数值摘要

| 场景 | SNR 中位数 dB | 严格动态窗口 | 模型 | 测试 RMSE | 相对 persistence 改善 % |
|---|---:|---:|---|---:|---:|
| industrial_dryer | 24.4529 | 0 | AR | 0.039806 | -34.7550 |
| blast_furnace | 14.7900 | 12 | AR | 0.046431 | 3.9966 |

脱丁烷塔缺少标准字段：bottom_temperature_a, bottom_temperature_b, top_temperature, tray6_temperature。保持字段/单位门禁，未反向生成温度量纲。

## 测试与兼容

- 后端 275 项通过（15.671 秒）：core.tests、runtime_events、artifact_readiness_runtime、segmentation_optimization_executors、arx_response、skill_md_runtime、skill_execution_contracts、dedicated_skill_executors、skill_loader、skill_routing、skill_router_quality_gate、agent_skill_runtime_architecture、core_skill_executors、skill_refactor、validation、three_scene_skills、blast_furnace、industrial_dryer、scene_context_regression、scene_recognition_accuracy、pipeline_rejection。
- 新增 core/test_three_scene_skills.py 共 10 项：三场景 Context、同一 executor、无算法复制、三场景真实文件执行、结果契约、配置参数改变实际指标/保留 audit、纯 MD、API/解释边界。脱丁烷用例明确断言 unavailable，不能拿该测试 PASS 声称数值成功。
- 更新第一阶段测试数量为 12；联合 SNR/时滞/VIF/ARX 因新增组装节点变为 5。旧分类器专用测试显式使用 legacy；MD 路径由独立真实数值测试覆盖。
- 前端 npm test：30 项通过；npm run build 成功，有既有大于 500 kB 的 bundle 提示。
- git diff --check 通过。
- 独立启动本工作区 Django 127.0.0.1:18014，使用 security/session 的 CSRF cookie/token 实际调用：
  - GET /api/agent/skills/ → HTTP 200 application/json，12 Skills。
  - GET /api/agent/skills/system_identification_trainer/ → HTTP 200 application/json。
  - POST /api/agent/plans/ → HTTP 201 application/json，12 节点。
- HTTP 留痕：runtime/agent_skill_runs/three_scene_http_checks.json。用户原来的服务未停止或替换。

## 本阶段修改文件

- core/skills/context.py：扩展 SceneContext。
- 三个既有 standards/scenarios/*/template.json：角色、约束、参数、展示元数据。
- 八个新增迁移的 SKILL.md/executor.py，四个第一阶段 Skill 的依赖/输入/证据适配。
- core/skills/stage_adapters.py：共用阶段适配。
- core/services/scene_skill_pipeline.py：通用原文件入口。
- core/services/segmentation_service.py：提取原选窗函数共用，不改规则。
- core/skills/core_executors.py：使用显式场景角色和真实采样周期。
- core/skills/md_adapter.py、runtime.py：参数优先级与阻断 audit 完整留痕。
- core/skills/registry.py、loader.py、md_planning.py：已有产物依赖剪枝、可选召回约束、知识边界、entities 兼容。
- core/services/agent_chat.py：无数值执行时保留已有专家证据说明。
- core/test_three_scene_skills.py、core/test_skill_md_runtime.py、core/tests.py、core/test_skill_routing.py、core/test_core_skill_executors.py、core/test_segmentation_optimization_executors.py。
- 本次 5 份 three_scene_* 交付文件。

第一阶段遗留未提交改动（API、启动加载、requirements、前端 runtimeObservability 等）仍在工作区；本阶段未重做这些模块。

## 结论

架构已经共用，两个数据文件完成数值主链；脱丁烷塔缺少合格数据，干燥器缺实测验证。完整三场景数值验收仍为 PARTIAL。参见 [three_scene_remaining_gaps.md](three_scene_remaining_gaps.md)。
