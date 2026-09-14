# 脱丁烷塔 43 列逐列复审

| 指标 | 结果 |
| --- | --- |
| source_column_count | 43 |
| previous_auto_accept_count | 25 |
| previous_wrong_accept_count | 24 |
| new_auto_accept_count | 1 |
| new_wrong_accept_count | 0 |
| review_count | 38 |
| reject_count | 4 |
| new_false_rejects | [] |
| critical_wrong_accepts | [] |

| dataset | source_column | previous_candidate | previous_method | previous_status | Ground Truth | new_candidate | new_decision | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dataset_01 | u1 | top_temperature | alias | MATCH | REVIEW_REQUIRED | top_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u2 | top_pressure | alias | MATCH | REVIEW_REQUIRED | top_pressure | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u3 | reflux_flow | alias | MATCH | REVIEW_REQUIRED | reflux_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u4 | next_process_flow | alias | MATCH | REVIEW_REQUIRED | next_process_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u5 | tray6_temperature | alias | MATCH | REVIEW_REQUIRED | tray6_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u6 | bottom_temperature_a | alias | MATCH | REVIEW_REQUIRED | bottom_temperature_a | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | u7 | bottom_temperature_b | alias | MATCH | REVIEW_REQUIRED | bottom_temperature_b | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_01 | y | bottom_butane_content | alias | MATCH | REVIEW_REQUIRED | bottom_butane_content | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u1 | top_temperature | alias | MATCH | REVIEW_REQUIRED | top_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u2 | top_pressure | alias | MATCH | REVIEW_REQUIRED | top_pressure | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u3 | reflux_flow | alias | MATCH | REVIEW_REQUIRED | reflux_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u4 | next_process_flow | alias | MATCH | REVIEW_REQUIRED | next_process_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u5 | tray6_temperature | alias | MATCH | REVIEW_REQUIRED | tray6_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u6 | bottom_temperature_a | alias | MATCH | REVIEW_REQUIRED | bottom_temperature_a | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | u7 | bottom_temperature_b | alias | MATCH | REVIEW_REQUIRED | bottom_temperature_b | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_02 | y | bottom_butane_content | alias | MATCH | REVIEW_REQUIRED | bottom_butane_content | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_03 | U1 | top_temperature | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | top_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_03 | U2 | top_pressure | alias | MATCH | REVIEW_REQUIRED | top_pressure | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_03 | U3 | reflux_flow | alias | MATCH | REVIEW_REQUIRED | reflux_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_03 | U4 | next_process_flow | alias | MATCH | REVIEW_REQUIRED | next_process_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_03 | U5 | tray6_temperature | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | tray6_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_03 | U6 | bottom_temperature_a | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | bottom_temperature_a | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_03 | U7 | bottom_temperature_b | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | bottom_temperature_b | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_03 | U8 | bottom_butane_content | alias | MATCH | REVIEW_REQUIRED | bottom_butane_content | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_04 | Unnamed: 0 | None | opaque_tag_requires_dictionary | NO_MATCH | MATCH | None | REJECT | final gate requires review: candidate_exists, identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | Feed Flow to DB | next_process_flow | trained_model_auto | REVIEW_REQUIRED | NO_EQUIVALENT | next_process_flow | REVIEW_REQUIRED | final gate requires review: unit, physical_semantics |
| dataset_04 | Reboiler o/l Temp | bottom_temperature_b | trained_model_auto | REVIEW_REQUIRED | NO_EQUIVALENT | bottom_temperature_b | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | Column top Temp | top_temperature | trained_model_auto | REVIEW_REQUIRED | REVIEW_REQUIRED | top_temperature | REVIEW_REQUIRED | final gate requires review: unit, physical_semantics |
| dataset_04 | Reboiling steam flow | None | semantic | NO_MATCH | NO_EQUIVALENT | None | REJECT | final gate requires review: candidate_exists, identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | Reflux flow | reflux_flow | alias | MATCH | MATCH | reflux_flow | AUTO_ACCEPT | final gate passed |
| dataset_04 | Column Top pressure | top_pressure | semantic | REVIEW_REQUIRED | REVIEW_REQUIRED | top_pressure | REVIEW_REQUIRED | final gate requires review: unit, physical_semantics |
| dataset_04 | Column bottom temp | bottom_temperature_a | trained_model | REVIEW_REQUIRED | REVIEW_REQUIRED | bottom_temperature_a | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | Control tay temp | tray6_temperature | trained_model | REVIEW_REQUIRED | REVIEW_REQUIRED | tray6_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | C4H6 in DB bottom | bottom_temperature_a | trained_model | NO_MATCH | NO_EQUIVALENT | bottom_temperature_a | REJECT | final gate requires review: identity_basis, unit, physical_semantics, source_confidence |
| dataset_04 | C4H8 in DB bottom | bottom_temperature_a | trained_model | NO_MATCH | NO_EQUIVALENT | bottom_temperature_a | REJECT | final gate requires review: identity_basis, unit, physical_semantics, source_confidence |
| dataset_23 | u1 | top_temperature | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | top_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_23 | u2 | top_pressure | alias | MATCH | REVIEW_REQUIRED | top_pressure | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_23 | u3 | reflux_flow | alias | MATCH | REVIEW_REQUIRED | reflux_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_23 | u4 | next_process_flow | alias | MATCH | REVIEW_REQUIRED | next_process_flow | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |
| dataset_23 | u5 | tray6_temperature | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | tray6_temperature | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_23 | u6 | bottom_temperature_a | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | bottom_temperature_a | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_23 | u7 | bottom_temperature_b | alias | REVIEW_REQUIRED | REVIEW_REQUIRED | bottom_temperature_b | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, physical_semantics, source_confidence, provenance, normalization_metadata |
| dataset_23 | y | bottom_butane_content | alias | MATCH | REVIEW_REQUIRED | bottom_butane_content | REVIEW_REQUIRED | final gate requires review: identity_basis, unit, provenance, normalization_metadata |

43 是多个公开候选/镜像的列记录合计，不是单个 43 列工厂文件。24 个历史错误接受全部来自匿名 U/y 别名，现为复核；GT MATCH 的 Reflux flow 仍接受。元数据时间列仍未自动识别。critical false accept=0 仅指这一冻结真值集，不能外推为任意工业 CSV 的保证。
