# Optimization Executor 迁移报告

## 结果

Optimization Executor 已从 partial shell 接入真实工业数据搜索：

```text
TaskSpec → ExecutionPlan → OptimizationExecutor
→ run_optimization_stage / _optimize_real_data
→ validation candidate search → frozen winner → one test evaluation
→ SkillExecutionResult
```

Pipeline 与 Executor 共同调用同一 `_optimize_real_data()` 实现。Executor 不调用 `stop_after`、`rerun_pipeline()` 或完整 `run_pipeline()`。

## 输入合同

必须同时提供 objective、model artifact、frozen split、train/validation/test、segments、decision variables、bounds、constraints、search space、optimization policy、field dictionary 和 real-data 标志。缺少任一项返回 blocked。

在组合 DAG 中，当前轮 standardization/cleaning/segmentation/modeling Executor 可以填入数据与 artifact 槽位；objective、decision variables、bounds、constraints、search space 和 optimization policy 仍必须来自 snapshot/planner 的显式合同。Executor 不会根据已有数据自动猜测这些策略字段。

`optimization_policy.mode` 必须为 `real_data`。`synthetic_benchmark` 由独立显式 API 负责，工业 Executor 不会自动切换；所有路径记录 `synthetic_fallback=false`。

## Validation/Test 边界

- 每个候选只读取 training 和 validation。
- 候选评分使用 `metrics.validation`。
- 成功候选的 validation target hash 必须一致。
- winner 和全部超参数冻结后才调用 `finalize_test()`。
- 独立 Executor 限制为主输出，证据固定记录 `test_used_for_search=false`、`test_evaluation_count=1`。

## 可行性

候选越过显式 top-k/max-lag bounds 时标记 `infeasible`。成功建模的候选按显式 `min_r2`、`min_coverage` 记录 `feasible`。若搜索完成但没有可行候选，Executor 返回 partial，不把结果冒充为成功可行解。

## 真实数据验收

使用完成运行 `20260912_125129_8ad7214b` 的真实 train/validation/test、segments、dictionary 与模型证据独立运行：

- 评估候选：12
- 最优候选：top_k=5、max_lag=60
- validation R²：0.9989545
- test R²：0.9981521
- test evaluation count：1
- test used for search：false
- synthetic fallback：false
- status：partial，因为训练覆盖率 1.04% 未满足显式 5% 可行性约束

该 partial 是合同安全结果，不会降级为 synthetic success。
