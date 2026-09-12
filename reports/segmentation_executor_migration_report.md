# Segmentation Executor 迁移报告

## 结果

`segmentation` 已从 `reader_only` 升级为 `executable`。调用链为：

```text
TaskSpec → minimal ExecutionPlan → SegmentationExecutor
→ run_segmentation_stage → DataCleaningSelectionAgent.select_dynamic_segments
→ SkillExecutionResult
```

## 职责拆分

- Cleaning Executor 固定以 `include_segmentation=False` 调用清洗 stage，只执行时间对齐、缺失/异常治理、重采样、数据质量与 60/20/20 frozen split。
- Segmentation Executor 读取明确的 train partition 和 split contract，执行 SNR、动态窗口提取、评分、排序与建模行选择。
- Pipeline 完整工作流继续以 `include_segmentation=True` 运行，但内部也调用同一个 `run_segmentation_stage()`。
- `_select_modeling_rows()` 已委托给 segmentation service，避免 Pipeline 和 Executor 各保留一套选择逻辑。

## 前置条件

缺少 cleaned training data、DatetimeIndex、足够数值过程字段、frozen split、有效窗口长度或步长时返回 blocked。Executor 不会自行重跑 cleaning 或 standardization。

## Artifacts 与 provenance

- `snr_estimates.csv`
- `selected_dynamic_segments.csv`
- `segment_scores.csv`
- `modeling_dataset.csv`
- `segmentation_report.json`

provenance 保存 upstream cleaning run、split version、policy、window、step、source columns、时间、Executor version，以及 `selection_scope=training_only`、`validation_rows_read=0`、`test_rows_read=0`。

## 真实数据验收

使用运行 `20260912_125129_8ad7214b` 的 xinan 训练分区直接调用共享 service：

- status：success
- candidate windows：287
- dynamic windows：287 中 2 个达到严格优质门槛
- selected modeling rows：45
- validation rows read：0
- test rows read：0
- 五类产物全部生成

SNR 仍是稳健二阶差分白噪声假设下的代理估计；重叠窗口不解释为独立激励次数。
