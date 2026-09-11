# Industrial Analysis Skill 迁移报告

## 原 Skill 位置与现状

原工业分析能力位于 `core/skills/analysis_plan.py`，并由 `core/skills/runtime.py::plan_skills` 调用。它没有 `SKILL.md`、独立目录、contracts 或可独立运行入口；通过 `core.skills` 包导入时会继续加载 Runtime 和 Django settings，因此无法作为独立能力包加载。

原实现输入为用户文本、旧 Skill 命中 ID 和可选 scene/evidence，输出附加在 Agent 计划的 `analysis.analysis_plan`。它依赖旧 30 Skill ID 作为兼容映射，但不直接执行分析算法。

## 原问题、场景硬编码与工程耦合

- 原模块属于 A14 Python 包，缺少独立 Skill 入口和加载说明。
- capability、选择规则、旧 Skill 映射集中在单文件，无法按需加载知识。
- A14 场景提示曾包含高炉、加热炉、锅炉、蒸汽压力等固定字符串。
- `runtime.py` 保留现网三场景执行白名单；它属于宿主 Pipeline 兼容层。
- Registry 固定字段位于 `integrations/standardization/standards/scenarios/`，前端 demo/mock 和个别 API 仍有高炉演示字段。
- 没有发现 `if field == "hot_blast_temperature"`；通用分析逻辑没有固定字段分支。

以上场景知识没有迁入独立 Skill。新 Skill 只认识调用方提供的标准语义，如 temperature、pressure、flow、energy、vibration、current 与 quality。

## 新目录树

```text
core/skills/industrial-analysis/
├── SKILL.md
├── capabilities/
│   ├── data-profiling.md
│   ├── data-quality-analysis.md
│   ├── trend-analysis.md
│   ├── time-series-analysis.md
│   ├── anomaly-detection.md
│   ├── correlation-analysis.md
│   ├── process-stability.md
│   ├── energy-analysis.md
│   ├── equipment-health.md
│   ├── quality-analysis.md
│   ├── operating-state.md
│   ├── bottleneck-analysis.md
│   ├── missing-data-analysis.md
│   └── root-cause-candidates.md
├── workflows/
│   ├── generic-analysis.md
│   ├── unknown-scene.md
│   └── validation.md
├── references/
│   ├── capability-routing.md
│   ├── industrial-semantics.md
│   ├── evidence-rules.md
│   └── confidence-rules.md
├── contracts/
│   ├── analysis-plan.schema.json
│   └── analysis-result.schema.json
├── scripts/build_analysis_plan.py
└── examples/energy-analysis-input.json
```

## 职责、capabilities 与 workflows

`SKILL.md` 只规定触发范围、输入边界、按需路由、输出契约与安全约束。14 个 capability 为：DATA_PROFILING、DATA_QUALITY_ANALYSIS、TREND_ANALYSIS、TIME_SERIES_ANALYSIS、ANOMALY_DETECTION、CORRELATION_ANALYSIS、PROCESS_STABILITY、ENERGY_ANALYSIS、EQUIPMENT_HEALTH、QUALITY_ANALYSIS、OPERATING_STATE、BOTTLENECK_ANALYSIS、MISSING_DATA_ANALYSIS、ROOT_CAUSE_CANDIDATES。

`generic-analysis` 负责综合分析顺序，`unknown-scene` 限制未知场景结论，`validation` 检查 requires、置信度传播、结果分层和安全边界。

## 输入与输出 contract

输入是数据或 `dataset_ref`，以及调用方可选提供的 `scene`、`fields`、`equipment_context`、`process_context`、`units`、`engineering_limits`、`data_quality`、`mapping_confidence`、`scene_confidence`、时间与样本信息。Skill 不导入宿主 Registry，也不重新猜字段。

计划输出包含 scene、data_quality、selected_capabilities、skipped_capabilities 和 result_contract。最终结果包含 analysis_plan、facts、findings、hypotheses、limitations；重要结论带 confidence 和 evidence。

## Lazy Loading

Agent 首先只读 `SKILL.md`。单项分析再加载一个对应 capability；综合分析加载 generic workflow 后选择若干 capability；未知场景额外加载 unknown workflow；因果、故障、限值或置信度问题才读取对应 reference。不会一次加载全部知识文件。

## 原工程兼容方式

原 `core/skills/analysis_plan.py` 现在是薄 adapter，通过文件路径加载独立脚本并继续导出 `CAPABILITIES`、`GENERIC_UNKNOWN_SAFE` 和 `build_analysis_plan`。`runtime.py`、Agent API、30 Skill ID、Pipeline 对外接口及返回字段保持不变。旧 Skill ID 仅由 adapter 传给独立规划器做执行能力映射，不成为独立包的工程 import。

## 五场景测试结果

同一 `build_analysis_plan.py` 对五类输入生成不同计划：

| 场景 | 代表性目标 | 代表性选中能力 |
|---|---|---|
| steel_industry_energy | 加热炉能耗与趋势 | ENERGY_ANALYSIS、TREND_ANALYSIS |
| thermal_power_boiler_long_tail | 锅炉长尾异常和稳定性 | ANOMALY_DETECTION、PROCESS_STABILITY |
| vapor_pressure_soft_sensor | 蒸汽压力软测量时序相关性 | TIME_SERIES_ANALYSIS、CORRELATION_ANALYSIS |
| blast_furnace | 铁水硅含量质量与工况 | QUALITY_ANALYSIS、OPERATING_STATE |
| unknown_scene | 未知数据趋势、相关和异常 | 仅通用安全能力 |

unknown 场景不会选择 EQUIPMENT_HEALTH、PROCESS_STABILITY、BOTTLENECK_ANALYSIS 或 ROOT_CAUSE_CANDIDATES，也不生成设备/工艺故障、确定根因或无依据限值结论。

## 剩余风险

独立包负责规划和分析规范，真实数值算法仍由宿主 Agent 选择可用工具执行。宿主必须把 StandardizationAgent 的完整语义和置信度传入，才能做数据级 requires 判断。A14 当前为兼容旧调用，在尚未取得数据上下文的规划阶段允许按目标生成候选计划；执行前仍应使用实际 evidence 再校验一次。

## 验证结果

- `quick_validate.py`：Skill 目录、frontmatter 和引用结构校验通过。
- 独立 CLI：使用 `examples/energy-analysis-input.json` 成功生成动态 analysis_plan。
- 解耦扫描：除示例输入外，没有项目绝对路径、宿主 `core` import、固定 scene 或固定工业字段。
- A14 兼容回归：94 项全部通过，Django system check 无告警。
