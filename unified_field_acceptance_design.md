# 统一 Final Acceptance Gate

入口：integrations/standardization/standard_agent/physical_semantics.py::final_field_acceptance_gate。
调用处：engine.map_columns；engine.standardize 人工覆盖后；core/services/dataset_evidence.py 离线逆缩放字段绑定。

保留候选召回和现有阈值；门禁是唯一最终接受决策。检查 candidate、identity_basis、unit、quantity_type、physical_role、equipment、measurement_location、channel、flow_direction、source_confidence、provenance、scenario_compatibility、required-field criticality；缺省维度明确依赖 registry identity，不能谎称有源实测证据。

显式/格式别名可作为高可信身份；解析到的源物理冲突优先于合同默认值。bottom_temp_a、tray_6_temperature 保持通过；reboiler、feed、错误通道/塔板不能通过高分或坏 alias 恢复。

U1…U8/y、normalized_N/scaled_N 等匿名候选没有自动物理单位假设。需要场景绑定的 standard_field、evidence_source、unit，以及 normalized=false 或 inverse_metadata+transform_applied。数值范围不参与身份判定。已声明 metadata 与合同的单位/设备/方向等冲突也会阻断。

field_metadata 是受信任调用方提交的来源证据，不是自动鉴真服务；其真伪仍需文档/人工核验。离线 restore_normalized_fields 额外要求源 SHA256、文件名、公式和有限逆变换参数，拒绝缺失 scenario_id；错测点即便公式有效仍会失败。没有新增自动反归一化 Runtime hook。

所有行有 final_acceptance_audit：method、source_column、candidate、scenario、criticality、identity/provenance/unit basis、checks、physical_checks、physical_evidence、metadata_checks、decision/reason。去重补充 final_status/post_duplicate_decision；不把排序胜出当物理通过。

没有完整物理合同的场景仍进入该入口；可信 registry identity 检查可观察冲突；不明的非可信语义/人工候选保守复核。未知属性没有被补造成已验证的设备/测点。
