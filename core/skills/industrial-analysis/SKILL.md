---
name: industrial-analysis
description: 对调用方提供的标准字段、设备、工艺、质量与限值上下文执行可复用工业数据分析。用于画像、质量、趋势、时序、异常、相关、稳定性、能耗、设备健康、质量、工况、瓶颈、缺失和根因候选分析；不负责宿主工程代码、Pipeline、前端或 Registry 管理。
---

<!-- skill-runtime-manifest
{
  "triggers": ["工业数据", "能耗", "能源", "异常", "趋势", "时序", "相关", "稳定性", "设备健康", "工况", "瓶颈", "根因", "数据质量", "缺失", "高炉", "锅炉", "精馏塔", "干燥器", "软测量"],
  "capabilities": {
    "DATA_PROFILING": {"path": "capabilities/data-profiling.md", "triggers": ["画像", "概览", "数据概况"]},
    "DATA_QUALITY_ANALYSIS": {"path": "capabilities/data-quality-analysis.md", "triggers": ["数据质量", "完整性", "可用性"]},
    "TREND_ANALYSIS": {"path": "capabilities/trend-analysis.md", "triggers": ["趋势", "走势", "变化"]},
    "TIME_SERIES_ANALYSIS": {"path": "capabilities/time-series-analysis.md", "triggers": ["时序", "周期", "预测", "滞后"]},
    "ANOMALY_DETECTION": {"path": "capabilities/anomaly-detection.md", "triggers": ["异常", "离群", "异常点"]},
    "CORRELATION_ANALYSIS": {"path": "capabilities/correlation-analysis.md", "triggers": ["相关", "关联", "共线"]},
    "PROCESS_STABILITY": {"path": "capabilities/process-stability.md", "triggers": ["稳定性", "稳定", "波动"]},
    "ENERGY_ANALYSIS": {"path": "capabilities/energy-analysis.md", "triggers": ["能耗", "能源", "电量", "功率", "燃料"]},
    "EQUIPMENT_HEALTH": {"path": "capabilities/equipment-health.md", "triggers": ["设备健康", "设备故障", "劣化", "振动"]},
    "QUALITY_ANALYSIS": {"path": "capabilities/quality-analysis.md", "triggers": ["质量分析", "产品质量", "合格率", "硅含量", "水分"]},
    "OPERATING_STATE": {"path": "capabilities/operating-state.md", "triggers": ["工况", "运行状态", "动态段"]},
    "BOTTLENECK_ANALYSIS": {"path": "capabilities/bottleneck-analysis.md", "triggers": ["瓶颈", "产能", "卡点"]},
    "MISSING_DATA_ANALYSIS": {"path": "capabilities/missing-data-analysis.md", "triggers": ["缺失", "空值"]},
    "ROOT_CAUSE_CANDIDATES": {"path": "capabilities/root-cause-candidates.md", "triggers": ["根因", "原因", "为什么"]}
  },
  "workflows": {
    "generic-analysis": {"path": "workflows/generic-analysis.md", "when": "capability_selected"},
    "unknown-scene": {"path": "workflows/unknown-scene.md", "when": "unknown_scene"},
    "validation": {"path": "workflows/validation.md", "triggers": ["验证", "审计", "测试"]}
  },
  "references": {
    "industrial-semantics": {"path": "references/industrial-semantics.md", "when": "semantic_analysis"},
    "evidence-rules": {"path": "references/evidence-rules.md", "when": "capability_selected"},
    "confidence-rules": {"path": "references/confidence-rules.md", "when": "capability_selected"},
    "capability-routing": {"path": "references/capability-routing.md", "when": "debug"}
  },
  "scripts": {
    "build-analysis-plan": {"path": "scripts/build_analysis_plan.py", "purpose": "ANALYSIS_PLAN"},
    "execute-analysis": {"path": "executor.py", "purpose": "CAPABILITY_EXECUTOR"}
  },
  "input_requirements": ["objective", "data_or_dataset_ref"],
  "output_contract": "contracts/analysis-result.schema.json",
  "execution_policy": {
    "minimum_samples": 30,
    "anomaly_zscore_threshold": 3.0,
    "max_preview_findings": 8,
    "root_cause_requires_causal_evidence": true
  },
  "evidence_policy": {
    "require_reproducible_statistics": true,
    "correlation_is_not_causation": true,
    "single_anomaly_is_not_equipment_failure": true
  }
}
-->

# Industrial Analysis

本 Skill 是项目 Agent 可独立加载的通用工业分析能力包。它不导入宿主工程模块，也不保存任何项目的场景注册表。

## 输入边界

接收数据或数据引用，以及调用方按需提供的 `scene`、`fields`、`equipment_context`、`process_context`、`units`、`engineering_limits`、`data_quality`、`mapping_confidence`、`scene_confidence`。这些上下文是证据，不是让 Skill 重新猜字段的提示。

解释标准语义时按需读取 [references/industrial-semantics.md](references/industrial-semantics.md)；涉及因果、故障或限值结论时读取 [references/evidence-rules.md](references/evidence-rules.md)；计算结论置信度时读取 [references/confidence-rules.md](references/confidence-rules.md)。

## 先规划后执行

任何分析前必须生成 `analysis_plan`。只选择 `requires` 已满足的 capability；请求了但证据不足的能力放入 `skipped_capabilities` 并给出原因。可调用 `scripts/build_analysis_plan.py` 生成确定性计划。

单项请求只加载对应 `capabilities/` 文件。综合分析读取 [workflows/generic-analysis.md](workflows/generic-analysis.md) 后动态加载多个 capability；`scene=unknown` 读取 [workflows/unknown-scene.md](workflows/unknown-scene.md)；验证或审计读取 [workflows/validation.md](workflows/validation.md)。完整路由表见 [references/capability-routing.md](references/capability-routing.md)。

Runtime 按 manifest 中的 `execution_policy` 调用 `executor.py`。`selected_capabilities` 必须执行，`blocked_capabilities` 与 `skipped_capabilities` 禁止进入 Executor；统计阈值、输出契约和证据约束均来自当前 Skill manifest。

## 输出边界

输出必须符合 `contracts/analysis-plan.schema.json` 与 `contracts/analysis-result.schema.json`。结果分为 `facts`、`findings`、`hypotheses`、`limitations`，重要结论携带 confidence 与 evidence。相关性不得写成因果；没有明确因果证据时，`ROOT_CAUSE_CANDIDATES` 只能输出候选因素。

未知场景允许数据画像、数据质量、趋势、相关、异常和缺失分析。除非调用方提供明确工业知识，否则禁止生成具体设备故障、具体工艺故障、确定根因或具体安全超限结论。
