# 字段匹配安全验收

本轮修复脱丁烷跨测点自动接受风险。原始模型分数不被人为压低，最终接受由独立物理门禁决定。

| 项目 | 状态 |
|---|---|
| explicit alias 正常 | PASS |
| model auto 多重安全门禁 | PASS |
| 测点位置冲突可拦截 | PASS |
| 流量方向冲突可拦截 | PASS |
| confidence 不覆盖物理冲突 | PASS |
| unknown 关键语义进入 review | PASS |
| audit 可解释 | PASS |
| 原脱丁烷 incomplete 数据仍 blocked | PASS |
| 无新增假 alias | PASS |

## 真实字段复现
| 原始字段 | 候选 | 方法 | confidence | 最终决策 |
|---|---|---|---:|---|
|Reboiler o/l Temp|bottom_temperature_b|trained_model_auto|0.879|REVIEW_REQUIRED|
|Feed Flow to DB|next_process_flow|trained_model_auto|0.883|REVIEW_REQUIRED|
|bottom_temp_a|bottom_temperature_a|alias|1.0|AUTO_ACCEPT|
|top temp [degC]|top_temperature|semantic|0.832|AUTO_ACCEPT|
|tray_6_temperature|tray6_temperature|normalized_alias|1.0|AUTO_ACCEPT|

## 判定与范围
1. Reboiler o/l Temp不再自动接受为bottom_temperature_b：位置/设备冲突，单位未声明。
2. Feed Flow to DB不再自动接受为next_process_flow：入口与下游方向冲突，位置/设备不兼容，单位未声明。
3. trained_model_auto必须同时通过既有置信阈值、单位、quantity、role、location（含equipment和底温A/B）、direction及source confidence。任一关键未知/冲突进入REVIEW_REQUIRED；低于候选保留阈值或不透明点号等情况仍可REJECT。
4. 明确alias、唯一格式规范化alias和点位字典有受信任身份依据；不绕过旧数值/单位门禁。top temp [degC]可AUTO_ACCEPT。模型候选正例用可控模型输出验证了同一最终接受链，不是禁用所有模型自动匹配。
5. 重复候选决策也检查physical_gate_pass；高分冲突候选不能重新变matched。

## 实际固定数据门禁
run_id：`scene_801f908b8ca2`；skill_run_id：`skillrun_8e00eb0df4d1`。
status：`unavailable`；dataset SHA256：`3679519020df3acf090047019a11c37b0e9f4fefb7747016660a68a7d2d9e629`。
原因：缺少必须的标准字段：bottom_temperature_a, bottom_temperature_b, top_temperature, tray6_temperature。
SKILL_MANIFEST_MODE=md；12规划节点的executor_invoked全部false。Pipeline UNAVAILABLE，Modeling NOT_EXECUTED，图中第2项PARTIAL。没有因为安全修复宣称数值链完成。

## 修改文件
- integrations/standardization/standard_agent/engine.py：优先级、最终接受和重复候选安全门禁、mapping解释字段。
- integrations/standardization/standard_agent/physical_semantics.py：独立物理属性提取和七维门禁。
- integrations/standardization/standards/scenarios/debutanizer_column/template.json：新增physical_semantics元数据。去掉新增块后与上轮完整契约严格相等；required/aliases/units/bounds未改。
- core/test_field_matching_safety.py：14项安全回归，包括真实两反例、同义正例、未知位置、角色/设备、单位、高置信、数值范围、重复处理。
- 四份field_matching报告及runtime/data_validation/field_matching_safety/acceptance.json。

未修改Runtime/Loader/Registry/Planner/SceneContext、12 Skill算法、高炉/干燥器场景文件。工作区已有其他阶段的修改保留，不属于本轮。

## 测试
要求范围专项回归61项：58通过、3跳过、0失败。包含当前字段安全、脱丁烷专项、three_scene、scene recognition、scene context、pipeline rejection、multi scenario。三个跳过保留缺合格数据的完整执行限制，不能计作数值PASS。
完整后端结果另附下方。字段匹配无关的阶段预测用例已隔离复现：StandardizationAgent.map_columns被设为调用即报错，调用次数仍为0，三个规划断言仍失败。日志保存在runtime验收目录。

## 映射证据（两个反例）
```json
{
  "physical_gate_pass": false,
  "physical_gates": {
    "semantic_similarity_pass": true,
    "unit_compatible": false,
    "quantity_type_compatible": true,
    "physical_role_compatible": true,
    "location_compatible": false,
    "direction_compatible": true,
    "source_confidence_pass": false
  },
  "source_confidence_evidence": {
    "pass": false,
    "basis": "explicit_source_tokens_and_candidate_score; not provenance verification"
  },
  "semantic_evidence": {
    "method": "trained_model_auto",
    "confidence": 0.8794719999999999,
    "identity_basis": "candidate_only; values are not identity evidence"
  },
  "unit_evidence": {
    "status": "not_declared",
    "compatible": false,
    "basis": "unknown"
  },
  "quantity_type_evidence": {
    "source": "temperature",
    "expected": "temperature",
    "compatible": true,
    "basis": "source_name_tokens"
  },
  "role_evidence": {
    "source": "process_measurement",
    "expected": "process_measurement",
    "compatible": true,
    "basis": "source_name_tokens"
  },
  "location_evidence": {
    "source": "reboiler_outlet",
    "expected": "column_bottom",
    "compatible": false,
    "basis": "source_name_tokens",
    "equipment": {
      "source": "reboiler",
      "expected": "column",
      "compatible": false,
      "basis": "source_name_tokens"
    },
    "channel": {
      "source": null,
      "expected": "b",
      "compatible": false,
      "basis": "source_name_tokens"
    }
  },
  "direction_evidence": {
    "source": null,
    "expected": null,
    "compatible": true,
    "basis": "source_name_tokens"
  },
  "physical_decision_reason": "physical gates require review: unit_compatible, location_compatible, source_confidence_pass",
  "source_column": "Reboiler o/l Temp",
  "candidate_field": "bottom_temperature_b",
  "mapping_method": "trained_model_auto",
  "raw": "Reboiler o/l Temp",
  "base_name": "Reboiler o/l Temp",
  "standard": "bottom_temperature_b",
  "display_name": "塔底温度B",
  "role": "state",
  "data_type": "float",
  "expected_unit": "degC",
  "detected_unit": null,
  "unit_status": "not_declared",
  "unit_action": null,
  "confidence": 0.879,
  "method": "trained_model_auto",
  "value_profile": {
    "available": false,
    "plausibility": 0.5,
    "missing_ratio": 0.0,
    "anomaly_ratio": 0.0
  },
  "neighbor_fields": [],
  "point_resolution": {
    "status": "not_a_point",
    "point_id": "REBOILER O/L TEMP",
    "missing_knowledge": []
  },
  "status": "review",
  "need_level": "uncertain",
  "is_needed": null,
  "decision": "REVIEW_REQUIRED",
  "decision_reason": "physical gates require review: unit_compatible, location_compatible, source_confidence_pass; final status: review"
}
```
```json
{
  "physical_gate_pass": false,
  "physical_gates": {
    "semantic_similarity_pass": true,
    "unit_compatible": false,
    "quantity_type_compatible": true,
    "physical_role_compatible": true,
    "location_compatible": false,
    "direction_compatible": false,
    "source_confidence_pass": false
  },
  "source_confidence_evidence": {
    "pass": false,
    "basis": "explicit_source_tokens_and_candidate_score; not provenance verification"
  },
  "semantic_evidence": {
    "method": "trained_model_auto",
    "confidence": 0.883288,
    "identity_basis": "candidate_only; values are not identity evidence"
  },
  "unit_evidence": {
    "status": "not_declared",
    "compatible": false,
    "basis": "unknown"
  },
  "quantity_type_evidence": {
    "source": "flow",
    "expected": "flow",
    "compatible": true,
    "basis": "source_name_tokens"
  },
  "role_evidence": {
    "source": "process_measurement",
    "expected": "process_measurement",
    "compatible": true,
    "basis": "source_name_tokens"
  },
  "location_evidence": {
    "source": "feed",
    "expected": "downstream_line",
    "compatible": false,
    "basis": "source_name_tokens",
    "equipment": {
      "source": "feed_line",
      "expected": "column",
      "compatible": false,
      "basis": "source_name_tokens"
    },
    "channel": {
      "source": null,
      "expected": null,
      "compatible": true,
      "basis": "source_name_tokens"
    }
  },
  "direction_evidence": {
    "source": "inlet",
    "expected": "downstream",
    "compatible": false,
    "basis": "source_name_tokens"
  },
  "physical_decision_reason": "physical gates require review: unit_compatible, location_compatible, direction_compatible, source_confidence_pass",
  "source_column": "Feed Flow to DB",
  "candidate_field": "next_process_flow",
  "mapping_method": "trained_model_auto",
  "raw": "Feed Flow to DB",
  "base_name": "Feed Flow to DB",
  "standard": "next_process_flow",
  "display_name": "后续流程流量",
  "role": "manipulated",
  "data_type": "float",
  "expected_unit": "t/h",
  "detected_unit": null,
  "unit_status": "not_declared",
  "unit_action": null,
  "confidence": 0.883,
  "method": "trained_model_auto",
  "value_profile": {
    "available": false,
    "plausibility": 0.5,
    "missing_ratio": 0.0,
    "anomaly_ratio": 0.0
  },
  "neighbor_fields": [],
  "point_resolution": {
    "status": "not_a_point",
    "point_id": "FEED FLOW TO DB",
    "missing_knowledge": []
  },
  "status": "review",
  "need_level": "uncertain",
  "is_needed": null,
  "decision": "REVIEW_REQUIRED",
  "decision_reason": "physical gates require review: unit_compatible, location_compatible, direction_compatible, source_confidence_pass; final status: review"
}
```
## 最终完整后端结果

`manage.py test core`：315项测试，3个失败断言（同一阶段规划测试的三个subtest）、3项跳过。不是全绿；失败均为cleaning/selection/modeling预测返回evidence_only。专项61项0失败。完整及隔离日志见 `runtime/data_validation/field_matching_safety/`。`git diff --check`通过。
