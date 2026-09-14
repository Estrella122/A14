# 三场景最终 Pipeline 验收

| Scene | Physical coverage | Pipeline | Modeling |
| --- | --- | --- | --- |
| blast_furnace | 6/6 | PASS | PARTIAL |
| debutanizer_column（LostRunes） | 2/9 | UNAVAILABLE | NOT_EXECUTED |
| industrial_dryer（DAISY） | 0/7 | UNAVAILABLE | NOT_EXECUTED |

高炉本轮只做一次专门固定回归：run_id=scene_2b56a168095e，skill_run_id=skillrun_6e3f474725e3，mode=md。
数据 SHA256：337389aab42fa898d018d432dd5383fd2b48c4780890b9e3a9cb61d00dbfdaa2。

| 比较项 | 与固定基线一致 |
| --- | --- |
| dataset_sha256 | True |
| skill_ids | True |
| executor_modules | True |
| metrics | True |

| Skill | 状态 | executor invoked |
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

各节点的 manifest、executor module、parameters、metrics、evidence、audit 与 artifact 哈希见 three_scene_final_runtime.json。read 状态的组件也有实际调用 audit，不把规划当执行；SNR 部分指标为 partial。Modeling 独立保持 PARTIAL，不等于模型可投产。

第 2 项 PARTIAL：架构同 Registry/Executor/算法已通过，但两场景真实数据未满足契约，三场景真实 12 Skill Pipeline 尚未全部完成。
