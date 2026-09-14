# 三场景最终验收

| Scene | Source | Confidence | Contract | 12 Skill Pipeline | Modeling |
| --- | --- | --- | --- | --- | --- |
| blast_furnace | Mendeley固定720h | DERIVED_REAL | PASS 6/6 | PASS | PARTIAL |
| debutanizer_column | LostRunes / Fortuna候选 | UNKNOWN / BENCHMARK_REAL | FAIL，最佳物理2/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer | DAISY / 新烟草子集 | PUBLIC_REAL_PROCESS / DERIVED_REAL | FAIL，分别0/7与至多2/7候选 | UNAVAILABLE | NOT_EXECUTED |

高炉只做一次本轮专门固定回归：scene_7f50c10fdde5 / skillrun_57913b8d3816；SKILL_MANIFEST_MODE=md。数据 hash=337389aab42fa898d018d432dd5383fd2b48c4780890b9e3a9cb61d00dbfdaa2。

| 固定基线比较 | 一致 |
| --- | --- |
| dataset_sha256 | True |
| skill_ids | True |
| executor_modules | True |
| metrics | True |

| Skill | 状态 | executor_invoked |
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

| Modeling 项 | 实测结果 |
| --- | --- |
| validation RMSE | 0.06441828005591495 |
| test RMSE | 0.04643078209424044 |
| test persistence RMSE | 0.048363701461402016 |
| test improvement % | 3.996632409750933 |
| model family | AR |
| stable AR poles | True |
| 10-step test | {"n_samples": 92.0, "num_params": 2.0, "r2": -0.42463116575769266, "adjusted_r2": -0.4566453492578655, "rmse": 0.08094748571209436, "mae": 0.06798810361149131, "mse": 0.00655249544310972, "sse": 0.6028295807660943, "fpe": 0.006843717462803486, "aic": -458.56765727531615, "bic": -453.52408012121805} |
| free simulation test | {"conditional_on_observed_inputs": true, "diverged": false, "metrics": {"n_samples": 105.0, "num_params": 2.0, "r2": -0.5909183181066882, "adjusted_r2": -0.6221127949323095, "rmse": 0.0819943247809784, "mae": 0.06575011251525816, "mse": 0.006723069296288569, "sse": 0.7059222761102998, "fpe": 0.006984159366047349, "aic": -521.2321012612256, "bic": -515.9241805609105}} |
| residual | {"acf_max_abs": 0.2581643800853005, "heuristic_95pct_bound": 0.1912764142979125, "whiteness_test": "not_performed; ACF is diagnostic only"} |

Test leakage guard：沿用原有 chronological 60/20/20，结构选择依据 train/validation，冻结模型后单次 test；没有按 test 换数据/模型/参数。guard 与 evaluation_target_hash 见 MODEL_ARTIFACT，完整指标与调用 audit 见 three_scene_real_pipeline_runtime.json。

Pipeline PASS 与 Modeling 分开：高炉执行链完成；多步/自由仿真及残差限制使 Modeling 保持 PARTIAL，不做投产背书。另两场景未满足预检，run_id=null，不伪造执行记录。

通用 Skill 架构 PASS；统一字段安全门禁 PASS（当前回归范围）；三场景真实数据 PARTIAL；三场景12 Skill Pipeline PARTIAL。图中第2项仍 PARTIAL。
