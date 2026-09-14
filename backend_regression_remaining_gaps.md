# 后端回归剩余边界

本轮三个规划失败均已修复，完整core 0 failures、0 errors。没有遗留本轮回归失败。

- 原有3个skip保留，没有新增skip；主要是数据/场景条件未满足，不是工业数值验收PASS。
- 脱丁烷仍缺合格物理数据或可信inverse元数据；本轮不改变Pipeline UNAVAILABLE或第2项PARTIAL结论。
- legacy/hybrid/md兼容PASS限于本轮覆盖的规划语义，不要求所有Skill ID完全相同。
- 来源为规则/MD词项的意图召回仍有词汇覆盖边界。本轮只补有实测证据缺失的“模型辨识”，没有重写语义理解架构。
- 执行计划可因缺snapshot保留execute并blocked；调用方仍需展示缺失输入，不能将计划意图当作完成运行。
- 本轮未执行前端、部署、Git提交；用户目标是后端回归，未改这些范围。
