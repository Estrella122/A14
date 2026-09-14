# 三场景真实 Pipeline

| 场景 | Pipeline | Modeling |
| --- | --- | --- |
| blast_furnace | PASS | PARTIAL |
| debutanizer_column | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer | UNAVAILABLE | NOT_EXECUTED |

高炉实际 run_id：scene_ed1c2a6475c3；skill_run_id：skillrun_52647467c364。
数据 SHA256：337389aab42fa898d018d432dd5383fd2b48c4780890b9e3a9cb61d00dbfdaa2。
SKILL_MANIFEST_MODE=md；统一 12 个 MD Skill、统一 Executor。运行的固定 720h 数据未根据 test 重新挑选。

| Skill | 状态 | 实际调用 | 模块 |
| --- | --- | --- | --- |
| time_axis_alignment_resampler | success | True | core.skills.time-axis-alignment-resampler.executor |
| missing_anomaly_cleaner | success | True | core.skills.missing-anomaly-cleaner.executor |
| signal_noise_ratio_estimator | partial | True | core.skills.signal-noise-ratio-estimator.executor |
| steady_transient_state_detector | success | True | core.skills.steady-transient-state-detector.executor |
| high_snr_dynamic_segment_extractor | success | True | core.skills.high-snr-dynamic-segment-extractor.executor |
| segment_quality_scorer_ranker | read | True | core.skills.segment-quality-scorer-ranker.executor |
| time_delay_estimator_compensator | success | True | core.skills.time-delay-estimator-compensator.executor |
| collinearity_detector_reducer | success | True | core.skills.collinearity-detector-reducer.executor |
| modeling_dataset_assembler | read | True | core.skills.modeling-dataset-assembler.executor |
| arx_structure_order_selector | success | True | core.skills.arx-structure-order-selector.executor |
| system_identification_trainer | success | True | core.skills.system-identification-trainer.executor |
| model_diagnostics_evaluator | success | True | core.skills.model-diagnostics-evaluator.executor |

对照上次固定真实运行：{"dataset_sha256": true, "skill_ids": true, "executor_modules": true, "metrics": true}。

Pipeline PASS 是真实契约满足、12 Executor 实际调用、无 blocked/unavailable/failed、有 metrics/audit。部分指标可返回 partial（如未校准 SNR），不等于没执行。Modeling 另标 PARTIAL，不能把运行完成当模型投产证明；baseline、稳定性、多步、自由仿真和残差证据保存在 MODEL_ARTIFACT / MODEL_DIAGNOSTICS。

高炉最终选择 AR 模型；test 单步 R²=0.4898566、RMSE=0.0464308，较同样本 persistence RMSE 改善 3.9966%；AR poles 稳定。10 步 test R²=-0.4246312；自由仿真 R²=-0.5909183（未发散）；残差 ACF 最大 0.2582 超过启发式界限 0.1913，未执行白噪声统计检验。因此 Modeling 只能 PARTIAL。

完整执行收据、模块、参数、metrics、artifact 路径与哈希均在 three_scene_post_training_runtime.json。另两场景 run_id=null，明确 NOT_EXECUTED，不伪造 12 Executor 收据，也不以 synthetic 代替真实运行。

图中第 2 项：PARTIAL。已完成可执行源的复跑与不能执行源的证据门禁，未完成三场景全部真实 Pipeline。
