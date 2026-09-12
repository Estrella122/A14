# Runtime Scene Context Regression Report

- 检查日期：2026-09-12（Asia/Shanghai）
- 工程：A14 / ProcessPilot
- 浏览器项目上下文：`debutanizer_column`（页面选择器显示“脱丁烷塔 · 塔底C4浓度”）
- 结论：上传请求没有回归为项目场景，始终为 `scenario_id=auto`。实际回归是 Registry 场景资产被删除，自动解析器只能在剩余场景中选出 `debutanizer_column`。Skill Runtime 不在 CSV 上传执行链中，没有写入或覆盖 Pipeline scene。

## 根因与修复

提交 `717781713b915a57d7d47f99dabd65a18efc4a6e`（`fix: consolidate the three official scenarios`）删除了：

- `integrations/standardization/knowledge/point_semantics.csv`
- `thermal_power_boiler_long_tail` Registry 模板
- `vapor_pressure_soft_sensor` Registry 模板
- `steel_industry_energy` Registry 模板

因此当前运行的 `ScenarioRepository` 只加载 `blast_furnace`、`debutanizer_column`、`industrial_dryer`。`detect_scenario()` 对候选排序后在 `integrations/standardization/standard_agent/engine.py:430` 首次把 `debutanizer_column` 写为 `auto_selected`；并非前端、HTTP 或 Skill Runtime 把它作为显式场景传入。

修复恢复了上述三个可复用 Registry 场景及点位语义表。没有恢复已删除的其他非目标场景，也没有修改映射阈值、required fields、场景约束或字段别名。

另一个被错误场景门禁遮住的既有接线问题也已修复：`run_pipeline()` 已经把 `selection_window` / `selection_step` 传给 `_clean()`，但 `_clean()` 的签名和 `DataCleaningSelectionAgent` 构造尚未接收它们。现已按场景模板把两个参数原样传递，保证 xinan 通过标准化后能完成完整流水线。

## 请求链追踪

| 步骤 | project / request scene | 自动识别与最终场景 | 模板、点位语义与门禁 |
|---|---|---|---|
| `DataAssetsView.vue` | `project.scenarioId=debutanizer_column`；上传参数固定 `scenarioId='auto'` | 不在前端选择数据场景 | 另传只读诊断字段 `projectSceneId`，不参与选择 |
| `AgentWorkflowView.vue` | 同上，上传参数固定 `scenarioId='auto'` | 不在前端选择数据场景 | 同上 |
| `pipeline.js` | form-data：`scenario_id=auto`；`project_scene=debutanizer_column` | 两个字段独立 | `project_scene` 仅用于运行快照审计 |
| `pipeline_api.py` | `request.POST.scenario_id=auto` | 原样传入 `run_pipeline` | `project_scene` 单独传递 |
| `run_pipeline` | 快照记录 `scenario_request=auto`、`project_scene=debutanizer_column` | 不以 project scene 覆盖 request scene | 原样调用 `_standardize` |
| `_standardize` | 传给 Agent 的 scene 为 `auto` | xinan：`thermal_power_boiler_long_tail`；vapor：`vapor_pressure_soft_sensor` | 从实际检测场景重新取得 Registry template |
| `StandardizationAgent` / resolver | 无项目场景输入 | `auto_selected == selected`；xinan final 为锅炉；vapor 因 1 个 review，final 为 null | 按所有已加载 Registry 候选评分 |
| point semantics | xinan 命中场景 `thermal_power_boiler_long_tail` | `PT_8313A.AV_0#` 规范化为 `PT_8313A.AV_0` | `standard_field=upper_furnace_pressure_a`，`equipment=boiler`，`process_module=furnace` |
| Registry template | 使用 detected scene | `registry_scene_id` 与 detected scene 一致 | xinan / vapor 分别读取各自 `template.json` 和 `fields.csv` |
| modeling gate | 不读取 project scene | gate scene 与 detected scene 一致 | required fields 来自对应 `fields.csv#required=true` |
| API snapshot / 页面 | 同时保留 project 与 request scene | 页面按标准化结果显示 31/31 或 29/30 | 不再显示脱丁烷塔 required fields（除真实脱丁烷塔样本） |

## 真实运行 Registry

浏览器对应的 Django 进程使用当前工作区 Registry，实测加载六个场景：

- `blast_furnace`
- `debutanizer_column`
- `industrial_dryer`
- `steel_industry_energy`
- `thermal_power_boiler_long_tail`
- `vapor_pressure_soft_sensor`

要求检查的四个场景均在其中。运行快照新增 `runtime_trace.loaded_scenes` 和 `runtime_trace.point_semantics_scenes`，便于今后直接定位 Registry 缺失。

## PT_8313A.AV_0# 点位语义

恢复后的精确记录为：

| point_id | scene | standard_field | equipment | process_module | confidence |
|---|---|---|---|---|---:|
| `PT_8313A.AV_0` | `thermal_power_boiler_long_tail` | `upper_furnace_pressure_a` | `boiler` | `furnace` | 0.99 |

修复前返回 `opaque_tag_requires_dictionary` 的原因是 `point_semantics.csv` 已被提交 `7177817` 删除，且锅炉 Registry 模板也不存在。不是 scene 约束过严。修复后真实运行的 mapping method 为 `point_dictionary`，`status=matched`。

## 修复前后验证

### xinan_completed_data.csv

| 项目 | 修复前 `20260912_114638_e860eb11` | 修复后浏览器 `20260912_120655_05cef490` |
|---|---|---|
| project scene | 页面为 `debutanizer_column` | 快照 `debutanizer_column` |
| request scene | `auto` | `auto` |
| auto_selected / selected | `debutanizer_column` | `thermal_power_boiler_long_tail` |
| final_scene | null | `thermal_power_boiler_long_tail` |
| scene_status | `unknown` | `confirmed` |
| confidence | 0.285 | 0.948 |
| 字段覆盖 | 0 matched / 31 | 31 matched / 31 |
| review / unmapped | 2 / 29 | 0 / 0 |
| modeling gate scene | `debutanizer_column` | `thermal_power_boiler_long_tail` |
| required fields | `timestamp`, `top_temperature`, `top_pressure`, `reflux_flow`, `next_process_flow`, `tray6_temperature`, `bottom_temperature_a`, `bottom_temperature_b`, `bottom_butane_content` | `timestamp`, `upper_furnace_pressure_a`, `container_outlet_vapour_pressure`, `upper_furnace_temperature_right`, `primary_fan_outlet_flow`, `primary_desuperheating_water_flow`, `compensated_main_steam_flow`, `boiler_outlet_steam_temperature` |
| 流水线结果 | 标准化阻断 | `completed`，无 error |

### vapor-pressure.csv

| 项目 | 修复前 `20260912_114654_9bbbd6e4` | 修复后浏览器 `20260912_120635_db21ecd0` |
|---|---|---|
| project scene | 页面为 `debutanizer_column` | 快照 `debutanizer_column` |
| request scene | `auto` | `auto` |
| auto_selected / selected | `debutanizer_column` | `vapor_pressure_soft_sensor` |
| final_scene | null | null（保留 1 项人工 review） |
| scene_status | `uncertain` | `uncertain` |
| confidence | 0.358 | 0.928 |
| 字段覆盖 | 1 matched / 30 | 29 matched / 30，1 review |
| modeling gate scene | `debutanizer_column` | `vapor_pressure_soft_sensor` |
| required fields | 脱丁烷塔 9 字段 | `timestamp`, `hours_elapsed`, `reboiler_temperature_average`, `condenser_pressure_inverse`, `antoine_pressure_estimate`, `current_pressure_estimate`, `vapour_pressure_kpa` |

### 真正的 debutanizer 数据

浏览器上传 `integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv`，运行 `20260912_120759_c2766b9e`：

- `project_scene=debutanizer_column`
- `scenario_request=auto`
- `auto_selected=selected=final_scene=debutanizer_column`
- `confidence=0.623`

这证明修复没有禁用或压制脱丁烷塔场景。

## Skill Runtime 影响检查

Skill Discovery / Loader / Runtime 仅由 `core/agent_api.py` 的 Agent Skill API 调用。CSV 上传路径 `core/pipeline_api.py -> core/services/pipeline.py -> StandardizationAgent` 不导入、不调用 `core/skills/runtime.py`。Skill Runtime 的 scene 只是 Skill 规划上下文，不会成为 StandardizationAgent 的显式 scene。因此本次污染与近期两个 Skill 重构提交 `9f513ad`、`a92c47c` 无关。

## 修改文件

- `integrations/standardization/knowledge/point_semantics.csv`（恢复）
- `integrations/standardization/standards/scenarios/steel_industry_energy/{template.json,fields.csv}`（恢复）
- `integrations/standardization/standards/scenarios/thermal_power_boiler_long_tail/{template.json,fields.csv}`（恢复）
- `integrations/standardization/standards/scenarios/vapor_pressure_soft_sensor/{template.json,fields.csv}`（恢复）
- `core/services/pipeline.py`（场景追踪字段；清洗窗口参数接线）
- `core/pipeline_api.py`（独立记录 project scene）
- `frontend/src/api/pipeline.js`（独立 form-data 字段）
- `frontend/src/views/DataAssetsView.vue`（上传时传诊断 project scene，request scene 仍固定 auto）
- `frontend/src/views/AgentWorkflowView.vue`（同上）
- `core/test_scene_context_regression.py`（Registry、xinan 点位语义、vapor 场景回归）

未修改 `industrial-analysis` Skill、工业分析 capability、映射阈值、脱丁烷塔 alias、point semantics scene 约束或 required fields。

## 测试结果

- Django：`manage.py test core.test_scene_context_regression core.test_debutanizer core.test_multi_scenario core.test_pipeline_rejection core.test_skill_routing`：24 项通过，1 项因外部授权数据未落地而按既有规则跳过。
- 前端：`npm run build`：通过（650 modules transformed）。
- 真实浏览器：在 Vite `127.0.0.1:5176`、Django `127.0.0.1:8000` 的运行进程上完成三次上传验证；页面项目始终为脱丁烷塔，xinan 显示 31/31，vapor 显示 29/30，真实 debutanizer 仍识别为脱丁烷塔。
