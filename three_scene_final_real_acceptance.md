# 第2项最终真实验收

| Scene | Source | Confidence | Contract | Pipeline | Modeling |
| --- | --- | --- | --- | --- | --- |
| blast_furnace | Mendeley固定720h | DERIVED_REAL | PASS 6/6 | PASS | PARTIAL |
| debutanizer_column | LostRunes / Fortuna | UNKNOWN / BENCHMARK_REAL | FAIL，最佳物理2/9、自动1/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer | DAISY / 烟草800×9子集 | PUBLIC_REAL_PROCESS / DERIVED_REAL | FAIL，物理0/7或至多2/7候选、自动0/7 | UNAVAILABLE | NOT_EXECUTED |

通用Skill架构 PASS；统一字段安全门禁 PASS（当前验收范围）；三场景真实契约 PARTIAL；三场景12 Skill Pipeline PARTIAL。图中第2项最终 PARTIAL。

高炉本轮专门固定回归仅一次：scene_8f53099c7ed4 / skillrun_a058328053a7，manifest_mode=md。

| 基线核对 | 一致 |
| --- | --- |
| dataset_sha256 | True |
| skill_ids | True |
| executor_modules | True |
| metrics | True |

| Skill | status | executor_invoked |
| --- | --- | --- |
| time_axis_alignment_resampler | success | True |
| missing_anomaly_cleaner | success | True |
| signal_noise_ratio_estimator | partial | True |
| steady_transient_state_detector | success | True |
| high_snr_dynamic_segment_extractor | success | True |
| segment_quality_scorer_ranker | read | True |
| time_delay_estimator_compensator | success | True |
| collinearity_detector_reducer | success | True |
| modeling_dataset_assembler | read | True |
| arx_structure_order_selector | success | True |
| system_identification_trainer | success | True |
| model_diagnostics_evaluator | success | True |

read节点有本次executor调用和本次run内artifact来源；没有拿旧回执冒充本次执行。完整manifest、modules、metrics、evidence、warnings、source_execution_id见JSON。

Modeling：validation RMSE=0.06441828005591495，test RMSE=0.04643078209424044，test persistence=0.048363701461402016，改善=3.996632409750933%；模型AR，稳定=True；10-step test R²=-0.42463116575769266，free simulation R²=-0.5909183181066882，残差={"acf_max_abs": 0.2581643800853005, "heuristic_95pct_bound": 0.1912764142979125, "whiteness_test": "not_performed; ACF is diagnostic only"}。因此Modeling保持PARTIAL，不否定工程Pipeline已执行。

冻结60/20/20分区，train/validation选择后单次test；未按test修改任何参数/数据版本/窗口/lag。新测试校验本次来源哈希、12回执、MD模块、同源artifact与guard，不通过新增skip掩盖两场景UNAVAILABLE。
