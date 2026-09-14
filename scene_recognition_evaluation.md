# 场景识别与 OOD 基线

| 期望 | 候选 | final_scene | status | confidence |
| --- | --- | --- | --- | --- |
| unknown_sales | vapor_pressure_soft_sensor | None | unknown | 0.24 |
| unknown_medical | steel_industry_energy | None | uncertain | 0.339 |
| unknown_opaque | thermal_power_boiler_long_tail | None | unknown | 0.0 |
| blast_furnace | blast_furnace | blast_furnace | confirmed | 0.943 |
| debutanizer_column | debutanizer_column | None | uncertain | 0.635 |
| industrial_dryer | debutanizer_column | None | uncertain | 0.42 |

三份已知源 schema 的候选分类准确率 2/3；要求 confirmed 且正确时只有 1/3。DAISY 返回脱丁烷塔候选，是已知缺陷，未当成功。

三个 OOD 中严格 unknown 2/3（66.7%）；医疗列返回 uncertain，因此不满足严格 UNKNOWN。错误 confirmed 已知场景率 0/3，但有候选绝不等于已拒识。均保留 final_scene=null。

场景 Agent：NO_MATERIAL_GAIN（仅评测、未训练）。没有在这 6 个测试 schema 上改阈值或加规则，避免用测试集调参。要增强需要独立真实 OOD/已知场景训练语料及保留测试集；本次未伪称具备足够训练证据。

检测调用 StandardizationAgent.detect_scenario，不用 project UI 场景覆盖；完整结果与候选保存在 datasets/field_ground_truth/scene_evaluation.json。
