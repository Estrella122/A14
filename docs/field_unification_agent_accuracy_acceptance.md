# 字段统一 Agent 场景识别优化与验收

验收日期：2026-09-11

## 实现位置与处理链路

- Agent：`integrations/standardization/standard_agent/engine.py` 中的 `StandardizationAgent`
- 场景与字段 Registry：`integrations/standardization/standards/scenarios/*/template.json` 与 `fields.csv`
- Registry 加载和校验：`integrations/standardization/standard_agent/repository.py`
- 后端调用链：`core/services/pipeline.py`
- 页面入口：`frontend/src/views/DataAssetsView.vue`、`frontend/src/views/AgentWorkflowView.vue`

当前远端 Registry 保留脱丁烷塔、工业干燥器和高炉三个场景。链路为：CSV 原始数据 → Registry/历史别名字段映射 → 单位与类型标准化 → 数据范围、缺失率和时序变化特征 → 候选场景评分 → 最终场景标签及状态 → 页面展示映射。

## 原因与修改

修改前的场景分数主要由字段名称映射覆盖率、字段映射平均置信度和少量页面指令关键词组成。数据值、单位冲突、设备和工艺上下文、缺失率、时序变化、冲突证据、最低证据数与最低必需字段覆盖率未进入最终选择。页面还会把当前项目场景写入上传指令，使页面状态可能影响业务识别。

本次保留原 Agent、字段字典、历史别名、模型和调用接口，在原链路中加入：

- 字段名称只用于产生候选；单位冲突和数据类型/范围不合理会降低字段置信度。
- 可换算单位先换算到标准单位后再做范围检查。
- 记录相邻字段、数值变化、缺失率、异常比例和历史别名来源。
- 每个场景从原模板读取 `required_features`、`supporting_features`、`conflicting_features`、优先级、最低证据数、最低置信度和最低必需字段覆盖率。
- 先生成带 `evidence` 和 `conflicts` 的候选列表，再做最终选择。
- 单一字段不能确认场景；关键字段不足、异常或单位冲突会降级。
- 第一、第二候选得分差小于 0.08 时返回 `ambiguous`，`final_scene` 为空。
- 输出兼容原 `selected/candidates/decision`，新增 `scene_candidates/final_scene/confidence/status`。
- 页面上传指令不再注入页面当前场景，业务识别结果再映射到页面。

工程中未发现“温度超过阈值就直接切换业务场景”的规则。原问题是字段名覆盖率可以在证据不足时确认场景，现已由多字段证据门槛和冲突机制替代。

## 自动测试

新增 `core/test_scene_recognition_accuracy.py`，覆盖：正常场景、单一异常、多字段联合异常、异名同义、同名不同设备、单位不同、关键字段缺失、异常值、相似场景和未知场景。测试由 Registry 和演示生成器构造，不针对固定行值硬编码。

- Django：101 项通过，1 项按原条件跳过。
- 前端：Vite 生产构建通过。
- 对照样本：在本次三场景 Registry 下，10 类识别行为测试全部通过。对照旧评分逻辑，缺少关键字段、通用列名和混合字段簇曾被 `accept/review`，现在分别进入 `uncertain/unknown` 或 `ambiguous`。

## 真实数据验收

| 文件 | 最终场景 | 状态 | 置信度 | 数据决策 | 结论 |
|---|---|---:|---:|---|---|
| `Steel_industry_data.csv` | 空 | ambiguous | 0.325 | reject | 远端最新 Registry 已移除钢铁能耗场景；安全拒识，恢复该模板后可接入 |
| `vapor-pressure.csv` | 空 | unknown | 0.239 | reject | 当前三场景均无足够字段证据，且目标列约 98.8% 缺失 |
| `xinan_completed_data.csv` | 空 | unknown | 0.269 | reject | 厂内 PT/TE/FT 点位编码缺少点位字典，证据不足 |
| `xinan_uncompleted_data.csv` | 空 | unknown | 0.269 | reject | 同上；不因文件名推断工艺语义 |

## 剩余风险

- 西南数据需要工厂提供点位号到测量含义、单位、设备和工艺模块的映射，经人工确认后可写入现有历史别名或场景字段表。
- `Steel_industry_data.csv` 需要把钢铁能耗模板重新登记到当前 Registry，才能进行业务识别；当前拒识是安全行为。
- `vapor-pressure.csv` 可能属于现有塔器的子任务，也可能是尚未登记的实验/软测量场景；需要来源说明和目标变量采样完整性才能确认。
- 当前数值范围来自模板通用物理边界，换装置或工况后仍需用现场工程限值校准。
- 候选评分已降低误判风险，但不能替代点位主数据、设备层级和工艺拓扑。
