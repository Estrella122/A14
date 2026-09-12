# Segmentation 与 Optimization 迁移前现状

审计基线：`daa4257`，代码同步状态：`HEAD == origin/main`。

## Segmentation

- 实际算法：`integrations/data_cleaning/src/data_cleaning_agent.py::DataCleaningSelectionAgent.select_dynamic_segments()`。
- 调用位置：`core/services/pipeline.py::_clean()` 仅在 chronological 60/20/20 的 train 分区调用。
- SNR：`snr_details()` 使用稳健二阶差分白噪声代理；窗口证据写入 `agent.snr_evidence`。
- 动态评分：输入变化、输出响应、完整性、异常、平滑度组合为 `segment_score`；`score >= 80 && snr >= 10 dB` 标为优质动态段。
- 排序：`segment_score` 降序。
- 建模行：`_select_modeling_rows()` 从优质段或降级候选段取时间切片。
- 当前 artifacts：`snr_estimates.csv`、`selected_dynamic_segments.csv`、`modeling_dataset.csv`；由 cleaning stage 写在 `03_cleaning`。
- 耦合点：时间对齐、缺失/异常处理、分区冻结、SNR、窗口评分、建模行选择和质量报告位于一个 `_clean()` 调用中。
- 泄漏边界：当前选择只读取 train；validation/test 分别清洗并写盘，没有传给 `select_dynamic_segments()`。这一点正确，但缺少独立 provenance 合同。
- Registry：`segmentation=reader_only`。

## Optimization

- 真实搜索：`core/services/pipeline.py::_optimize_real_data()`。
- 搜索变量：`top_k` 和 `max_lag`；初始 6 组候选，随后围绕验证集最优候选精搜，最多 16 轮。
- 数据输入：cleaned train frame、segments、dictionary、baseline model、主输出和 max lag；validation/test 通过固定运行目录读取。
- 候选执行：每轮由 `_select_modeling_rows()` 选择 train 行，再调用共享 `_model()`；评分只读 `metrics.validation`。
- 一致性保护：所有成功候选的 `evaluation_target_hash` 必须一致。
- test：赢家和超参数冻结后调用 `finalize_test()`；主模型记录 `test_evaluations=1`。多输出分支会对每个独立输出各评估一次，因此“每个输出一次”与“全局一次”需要在独立 Executor 合同中明确。
- synthetic：`core/services/optimization.py` 是独立 deterministic benchmark API；真实 Pipeline 搜索没有自动调用它。当前 shell Executor 也明确禁止 fallback。
- 当前 Executor：只检查 `objective/model/bounds/constraints/real_data`，完整时仍返回 partial，没有执行 `_optimize_real_data()`。
- 当前 artifacts：`05_optimization/optimization_report.json` 与赢家模型 artifacts。

## 风险与可抽取点

| 项目 | 可共享算法 | 当前风险 | 迁移方案 |
|---|---|---|---|
| segmentation | `select_dynamic_segments`、SNR 与 `_select_modeling_rows` | 与 cleaning 生命周期和目录耦合 | 建立只接收 train 的 service，Pipeline 与 Executor 共用 |
| cleaning | align/missing/anomaly/frozen split | 可隐式顺带分段 | 固定为只做治理与 split |
| optimization | `_optimize_real_data` + `_model` | 目录猜测、输入合同未显式化 | 增加显式 validation/test/artifact contract，并由 Executor 准备工作区 |
| test safety | winner 后 `finalize_test` | 多输出统计口径不清 | 独立 Executor 仅评估本次目标输出一次并写 evidence |
| artifacts | snapshot 字符串路径 | Executor 猜目录 | 引入 `RuntimeArtifactRef` resolver |

结论：两项算法都可直接复用。迁移不需要改写 SNR、窗口评分、建模或候选搜索算法，重点是拆出生命周期、输入合同、artifact resolver 和依赖失败传播。
