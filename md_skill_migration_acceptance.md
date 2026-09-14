# Markdown Skill 第一阶段验收

验收日期：2026-09-14。范围：四个核心 Skill 的 MD 注册、规划、真实算法执行、运行审计及现有 API 兼容。不是全部三十项迁移完成。

## 验收矩阵

| 项目 | 状态 | 证据 |
|---|---|---|
| A 自动扫描 SKILL.md | PASS | loader.scan_manifests / registry.get_registry，四个严格 manifest |
| B 新增 Skill 无需改 catalog | PASS | test_new_md_id_executes_without_catalog_registration：新 ID 真实计算 |
| C Agent 从 MD 发现能力 | PASS | search 使用 name/description/正文；body-only 无 trigger 测试 |
| D depends_on 构成 DAG | PASS | 时滞 → 共线性 → ARX；SNR → ARX；缺失和循环依赖拒绝 |
| E 动态调用 executor | PASS | MarkdownExecutor 按 manifest module/function import，执行 audit 留痕 |
| F 使用原算法 | PASS | SNR/时滞/共线性复用；ARX 搜索抽成共享函数，旧流水线也使用 |
| G 四个核心 Skill 迁移 | PASS | 四个目录均有 YAML SKILL.md 与 executor.py |
| H 纯 md 模式 | PASS | 清空 catalog 注册定义仍执行；纯 md 模式实际四项联合成功 |
| I 现有 API/前端兼容 | PASS | 后端 244 项、前端 30 项测试通过；实际 HTTP 与 live events；构建通过 |
| J 执行溯源 | PASS | manifest hash、module/function、输入、参数、依赖、指标和时间审计 |
| 第二批十二项 | PARTIAL | 本阶段尚未迁移，详见 remaining_gaps |
| 完整闭环 Skill orchestration | PARTIAL | 仅 SkillRoundRecord 兼容接口，旧 optimizer 保留 |
| 完整浏览器点击流程 | 未执行 | 实测为真实 HTTP，而非浏览器自动化；不冒充浏览器验收 |

## 真实 HTTP 验收

使用本次代码启动临时 Django：127.0.0.1:18014，保留 CSRF cookie/token 机制。没有修改既有 8000 服务或前端代理。所有响应 Content-Type 为 application/json。

- /api/agent/skills/ → HTTP 200，application/json
- /api/agent/skills/signal_noise_ratio_estimator/ → HTTP 200，application/json
- /api/agent/plans/ → HTTP 201，application/json
- /api/agent/skill-runs/ → HTTP 201，application/json
- /api/agent/chat/live/ → HTTP 202，application/json
- /api/agent/skill-runs/skillrun_94062ecab083/events/?after=0 → HTTP 200，application/json
- /api/agent/skill-runs/skillrun_94062ecab083/events/?after=0 → HTTP 200，application/json
- /api/agent/skill-runs/skillrun_7eaf17556d54/ → HTTP 200，application/json

输入：xinan_completed_data.csv 的已有运行 `20260912_201706_016603b6`。问题：“当前数据的信噪比是多少？”

- route：md_registry；只选择 signal_noise_ratio_estimator。
- SkillRun：`skillrun_7eaf17556d54`，状态 completed。
- 数据范围：CLEANED_TRAIN，4321 行，30 个数值字段均得到真实 SNR。
- upper_furnace_pressure_a：16.689474 dB。不是旧分窗中位数。
- manifest hash：`62da9604e4c3e7c3d46b5c8b64e6c91aeb705871c9b713ce05003815e761108d`。实测与详情 API 返回 hash 一致。
- live run：`skillrun_94062ecab083`，13 条事件，最终 completed。聊天直接输出本次计算的 dB 值。

## 四项联合执行

问题：“检查信噪比、时滞和共线性，并判断数据是否适合 ARX 建模。”

配置 SKILL_MANIFEST_MODE=md。使用已有工业干燥器运行 `20260913_133420_f1f6e999`，原始文件名称明确为合成验收数据；不是工厂实测。没有 mock 指标，没有随机生成结果。

SkillRun：`skillrun_ddb9082ba86b`。

| Skill | 状态 | 算法用时 ms |
|---|---|---|
| signal_noise_ratio_estimator | success | 7.44 |
| time_delay_estimator_compensator | success | 10.542 |
| collinearity_detector_reducer | success | 16.119 |
| arx_structure_order_selector | success | 292.167 |

ARX 比较 12 个候选，选择 ARX 1 阶；验证 R²=0.971554788、RMSE=0.044447656。未读取测试集。不把结构选择成功当作生产准入。

## 测试结果

- 后端 244 项测试通过（本次相关回归 + 原 core.tests API/聊天测试），用时 7.420 秒。不是声称全仓所有场景验收均重跑。
- 新增 core/test_skill_md_runtime.py：18 项，覆盖 YAML/必要字段/列表/重复 key/重复 ID、Registry、正文召回、依赖 DAG/缺失/循环、坏 executor、新 ID、纯 MD SNR、四项真实算法、知识解释、缺输入、常量/短样本/非数值、时间轴、旧 manifest、API、混合回退与聊天新结果绑定。
- 旧 core.tests 中“每次规划必须大于四个节点”的断言更新：MD 独立计划验证非空且每步来自 SKILL.md；legacy 路径保留原断言。不为凑节点数加入额外执行。
- 前端 npm test：30/30；npm run build：通过。保留既有大于 500 kB chunk 提示。
- git diff --check：通过。

后端复现命令：

```sh
.venv/bin/python manage.py test core.tests core.test_runtime_events core.test_artifact_readiness_runtime core.test_segmentation_optimization_executors core.test_arx_response core.test_skill_md_runtime core.test_skill_execution_contracts core.test_dedicated_skill_executors core.test_skill_loader core.test_skill_routing core.test_skill_router_quality_gate core.test_agent_skill_runtime_architecture core.test_core_skill_executors core.test_skill_refactor core.test_validation --noinput
```

## 本地原始证据

- runtime/agent_skill_runs/md-migration/md_migration_http_acceptance.json
- runtime/agent_skill_runs/md-migration/md_migration_multi_acceptance.json
- runtime/agent_skill_runs/skillrun_7eaf17556d54.json
- runtime/agent_skill_runs/skillrun_ddb9082ba86b.json

原始执行记录保存在已有 runtime 忽略目录，不把大份运行数据加入源码。模块关系见 md_skill_runtime_architecture.md；完整未完成项见 md_skill_migration_remaining_gaps.md。
