# Agent Skill Runtime Acceptance

## 指定自然语言链路

输入：`最近设备的数据老是忽高忽低，帮我看看是不是越来越不稳定。`

得到 TaskSpec：

```json
{
  "objective": "识别异常波动并评估过程稳定性并分析变化趋势",
  "task_kind": "data_analysis",
  "semantic_intents": ["anomaly_detection", "process_stability", "trend_analysis"],
  "requested_capabilities": ["ANOMALY_DETECTION", "PROCESS_STABILITY", "TREND_ANALYSIS"],
  "execution_mode": "analyze",
  "confidence": 0.82,
  "provider": "legacy_rule"
}
```

在 120 行、2 个数值字段、规则时间轴、confirmed 锅炉场景的验收数据上：

- SkillResolution：`industrial-analysis`
- selected capabilities：`ANOMALY_DETECTION`、`DATA_PROFILING`、`DATA_QUALITY_ANALYSIS`、`PROCESS_STABILITY`、`TREND_ANALYSIS`
- blocked：0
- 按需读取：`SKILL.md`、上述 5 个 capability 文档、`generic-analysis` workflow、evidence/confidence references
- Executor invocation：1
- capability executions：5，全部 success
- anomaly：`absolute_zscore`，阈值 3.0，检出 1 点
- stability：相对波动最大字段 `pressure`
- trend：绝对趋势最大字段 `temperature`
- 结果包含 `analysis_plan/facts/findings/hypotheses/limitations`

验收数据通过 DataFrame 直接交给独立 Executor，没有读取旧分析 Snapshot 伪装执行，也没有调用 `stop_after` 或 `rerun_pipeline()`。

## 最近真实 Pipeline Snapshot

最近运行 `20260912_125352_10174e21` 状态为 `needs_review`。Resolver 因映射/时间前置条件不足阻断 anomaly、stability、trend，只执行安全的 `DATA_PROFILING` 和 `DATA_QUALITY_ANALYSIS`。这证明 blocked capability 没有被关键词强制执行。

## 自动化测试

架构测试覆盖：口语化无固定按钮词、多目标、否定、explain/execute、多轮追问、未知场景、blocked、skipped、真 Executor、executed > 0、结果契约、SKILL policy 生效、legacy 回归、hybrid fallback、skill_runtime 禁止 Pipeline rerun。

最终验证：Django 全量 `150` 项通过、`1` 项按原条件跳过；前端 `7` 项通过；Vite 生产构建通过；`git diff --check` 通过。
