# 真实页面场景模板错配修复报告

## 结论

运行时错误发生在前端上传请求。`DataAssetsView.vue` 和 `AgentWorkflowView.vue` 把当前项目的 `project.scenarioId` 作为显式场景传给上传 API；默认项目场景是 `blast_furnace`。因此 Agent 虽然自动识别出了正确候选，显式选择仍把 `selected` 和后续标准化模板固定为高炉场景。

Pipeline 和 modeling gate 没有自行回退到 Registry 的第一个场景，也没有在 Agent 输出后使用缓存覆盖场景。它们只是继续使用了前端已经传错并由 Agent 作为显式选择接受的场景。

## 完整请求链路

1. `frontend/src/views/DataAssetsView.vue` / `frontend/src/views/AgentWorkflowView.vue` 读取用户 CSV。
2. `frontend/src/api/pipeline.js` 把 `scenarioId` 写入表单字段 `scenario_id`。
3. `core/pipeline_api.py` 读取 `scenario_id` 并传给 `core/services/pipeline.py::run_pipeline`。
4. `run_pipeline` 调用 `_standardize`，后者把场景参数传给 `StandardizationAgent.standardize`。
5. Agent 同时生成自动候选 `auto_selected`，并把显式请求场景写入 `selected`。
6. 标准化使用 `selected` 对应的 Registry 模板，生成 `scenario`、字段映射和 `data_decision`。
7. Pipeline 的 modeling gate 使用标准化结果中的场景、该场景 `fields.csv` 里 `required=true` 的字段以及映射缺失项决定是否进入下游。
8. API 返回 snapshot；前端按 `data_decision` 显示通过或待复核提示。

修复后，真实 CSV 上传固定请求 `scenario_id=auto`；项目场景只保留为页面所属项目信息，不再覆盖上传数据的业务场景。最近运行也不再按项目场景过滤，避免刷新后隐藏刚识别出的其他场景运行。

## 第一次改错的位置和原因

- 第一次错误赋值：`frontend/src/views/DataAssetsView.vue::runPipelineFile`（Agent 工作流页存在同样问题）。
- 修复前参数：`scenarioId: props.project.scenarioId ?? 'auto'`。
- 默认项目配置：`frontend/src/data/projectData.js` 中 `scenarioId: 'blast_furnace'`。
- 结果：请求中的 `scenario_id=blast_furnace` 被视为人工指定场景，覆盖自动候选。
- 修复后参数：`scenarioId: 'auto'`。

## 修复前真实运行

### Steel_industry_data.csv

- run_id：`20260911_134142_09295b6b`
- 请求场景：`blast_furnace`
- Agent 自动候选：`steel_industry_energy`
- 被显式选择覆盖后的场景：`blast_furnace`
- 自动候选置信度：`0.947`
- 旧的“领先差”：`-0.622`
- modeling gate 使用：高炉模板
- 错误必填字段：`blast_flow_rate`、`hot_blast_temperature`、`hot_metal_si`、`ore_coke_ratio`、`oxygen_flow_rate`、`timestamp`
- 决策：`reject`

### vapor-pressure.csv

- run_id：`20260911_133900_7e590328`
- 请求场景：`blast_furnace`
- Agent 自动候选：`vapor_pressure_soft_sensor`
- 被显式选择覆盖后的场景：`blast_furnace`
- 自动候选置信度：`0.928`
- 旧的“领先差”：`-0.928`
- modeling gate 使用：高炉模板
- 错误必填字段：同上
- 决策：`reject`

## 修复后真实页面上传

### Steel_industry_data.csv

- run_id：`20260911_135843_cfd1eb5c`
- `scene_id`（请求）：`auto`
- `agent_scene`：`steel_industry_energy`
- `selected_scene`：`steel_industry_energy`
- `final_scene`：`steel_industry_energy`
- `status`：`confirmed`
- `confidence`：`0.947`
- `confidence_margin`：`0.499`（同步后的 Registry 候选集合下 top1-top2）
- 字段验收：`11/11`
- `decision`：`ready`
- 页面：显示“验收结果 通过”“11 / 11”“场景：钢铁工业能源监测”
- 模板：`integrations/standardization/standards/scenarios/steel_industry_energy/template.json`
- modeling gate 必填字段来源：同目录 `fields.csv#required=true`
- modeling gate 必填字段：`timestamp`、`energy_usage`、`lagging_reactive_energy`、`leading_reactive_energy`

### vapor-pressure.csv

- run_id：`20260911_135908_7aad9401`
- `scene_id`（请求）：`auto`
- `agent_scene`：`vapor_pressure_soft_sensor`
- `selected_scene`：`vapor_pressure_soft_sensor`
- `final_scene`：`null`（安全拒识机制保留）
- `status`：`uncertain`
- `confidence`：`0.928`
- `confidence_margin`：`0.440`（同步后的 Registry 候选集合下 top1-top2）
- 输入字段：`30/30` 均进入映射检查，其中 `29` 个 matched、`1` 个 review
- `decision`：`review`
- 页面：显示“待复核”“29 / 30”“场景：蒸气压力软测量实验”，提示领先差 `44.0%`
- 模板：`integrations/standardization/standards/scenarios/vapor_pressure_soft_sensor/template.json`
- modeling gate 必填字段来源：同目录 `fields.csv#required=true`
- modeling gate 必填字段：`timestamp`、`hours_elapsed`、`reboiler_temperature_average`、`condenser_pressure_inverse`、`antoine_pressure_estimate`、`current_pressure_estimate`、`vapour_pressure_kpa`
- 当前待复核原因仍是该场景自身的数据契约：缺少 `timestamp`、`vapour_pressure_kpa`，并有 1 个字段需要人工确认；不再包含任何高炉字段。

## “领先差”计算 Bug

Bug 存在。旧字段 `confidence_margin` 实际使用“被显式选择场景分数减去最佳其他候选分数”，所以错误强制选择高炉场景后出现 `-62.2%`、`-92.8%` 等负值，并可能把置信度差异误当成领先差。

现已统一为 `top1.score - top2.score`。同时保留 `selected_confidence_margin` 作为显式选择与候选排序不一致时的诊断值，页面“领先差”只显示自动候选的正向 top1-top2 差值。同步远端候选集合后，vapor 真实页面显示 `44.0%`，没有把 `confidence=0.928` 显示成 `-92.8%`。

## 修改文件

- `frontend/src/views/DataAssetsView.vue`：上传真实 CSV 时请求自动识别；不再按项目场景过滤最近运行。
- `frontend/src/views/AgentWorkflowView.vue`：同样修正 Agent 工作流页上传与最近运行读取。
- `integrations/standardization/standard_agent/engine.py`：修正领先差含义并保留显式选择差异诊断。
- `core/services/pipeline.py`：在 API snapshot 中记录实际场景、模板路径、识别必需特征和 modeling gate 必填字段来源。
- `core/test_scene_registry_coverage.py`：新增 top1-top2 领先差回归断言。
- `integrations/standardization/standard_agent/{repository.py,units.py,demo.py}`、`integrations/data_cleaning/src/data_cleaning_agent.py`、`integrations/standardization/standards/global_schema.json`：合并远端更新时保留本轮开始前已验收的 Agent 契约、点位字典、单位和清洗兼容能力；没有新增或修改场景判断规则。

本次没有修改字段识别算法、场景阈值或 Registry 内容。

## 验证结果

- 本任务定向后端回归：3 项通过，覆盖四份真实数据、领先差公式和拒识短路。
- 合并远端后的全量后端套件：110 项中 106 项通过、1 项跳过；其余 3 项是远端新增测试与既有基线的接口/样例期待不一致（debutanizer 摘要字段、演示数据列名、远端新场景的 conflicting_features），与本次场景传递修复无关。
- 前端生产构建：通过。
- 真实浏览器上传：Steel 与 vapor 两份 CSV 均完成；请求、API snapshot、页面结果三者一致。
- 修复后的两次运行均未加载 `blast_furnace` 模板，也未把任何高炉必填字段交给 modeling gate。
