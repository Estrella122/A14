# 后端回归修复验收

结论：PASS。完整core后端325项，322通过、3个原有跳过，0 failures、0 errors。

|项目|状态|
|---|---|
|Cleaning evidence intent|PASS|
|Cleaning execute intent|PASS|
|Selection evidence intent|PASS|
|Selection execute intent|PASS|
|Modeling evidence intent|PASS|
|Modeling execute intent|PASS|
|“重新”非动作误触发保护|PASS|
|MD mode行为正确|PASS|
|legacy compatibility|PASS（本轮规划兼容范围）|
|field matching safety无回归|PASS|
|manage.py test core|PASS|

## 原三失败结论

cleaning、selection、modeling均为RUNTIME_REGRESSION，逐条核验见failure_audit。原因是MD Planner用snapshot是否存在覆盖execute意图，并非用户问法应只读。保留原断言，修复规划决策。

修复后“清洗缺失值”“提取高信噪比动态段”“训练系统辨识模型”“重新执行数据清洗”“请重新运行模型辨识”是execute。查看清洗结果、为什么筛选、当前模型指标、哪些参数需要重新辨识是evidence_only。execute只是计划意图，实际缺输入仍blocked。

## 测试实测

- 修复前完整core：315项，3个失败断言、3跳过。
- 原失败+planning/routing/router quality gate/MD Runtime/字段安全/脱丁烷专项：64项，63通过、1原有跳过。
- 新语义测试：10项全通过（每项含多模式/上下文subtest）。
- 最终完整core：325项，322通过、3原有跳过，0 failures/errors，21.924秒。
- 未修改失败测试期待、未删除断言、未mock真实规划、未新增skip。未改字段安全门禁及三场景契约。

## 修改文件

- core/skills/md_planning.py：保留execute意图，新增已有结果查询边界。
- core/skills/system-identification-trainer/SKILL.md：模型辨识同义召回 metadata/说明。
- core/test_planning_execution_modes.py：10项语义回归。
- 本轮4份报告，以及runtime/data_validation/planning_regression中的模式对照和测试日志。

未改Skill Runtime总体架构、Loader、Registry、SceneContext、12 Skill算法、三场景配置或前端。工作区其他既有修改不是本轮新增。未提交/推送GitHub。

完整日志：runtime/data_validation/planning_regression/full_after.log。完整模式证据：同目录after_modes.json。现有数据缺失skip和脱丁烷UNAVAILABLE不因测试全绿而消失。
