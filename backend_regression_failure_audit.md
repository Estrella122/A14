# 后端回归失败审计

修复前重新实际运行 `.venv/bin/python manage.py test core --verbosity 1`：315项，3个失败断言、3个原有skip。完整日志见 runtime/data_validation/planning_regression/full_before.log。

测试位置：core/test_acceptance.py，AcceptanceHarnessTests.test_stage_prediction_matches_execution_scope，line 23。未删除或改动原测试。

|subtest输入|expected|actual|单独判定|证据|
|---|---|---|---|---|
|清洗缺失值|cleaning|evidence_only|RUNTIME_REGRESSION|Task Understanding识别清洗执行；MD选missing_anomaly_cleaner，具有执行节点；缺snapshot导致mode被降级|
|提取高信噪比动态段|selection|evidence_only|RUNTIME_REGRESSION|识别提取动作；MD选动态段与SNR，依赖展开存在；不是“为什么筛选”解释请求|
|训练系统辨识模型|modeling|evidence_only|RUNTIME_REGRESSION|识别训练动作；MD选system_identification_trainer，manifest execution_mode=execute；不是查看模型指标|

三条分别核验动作、选中Skill、manifest和节点后，确实具有共同根因，而非将测试期待统一替换成actual。它们均不属于TEST_EXPECTATION_STALE。没有证据表明执行请求应因暂缺数据变成只读。

## 调用链

plan_skills → understand_task（已有规则动作/否定/疑问保护）→ registry.search（MD intent_terms过滤、正文token重合、trigger辅助召回）→ plan_from_manifests（选中及否定过滤）→ resolve_dependencies（根据requires与available artifacts展开）→ readiness检查 → mode → predicted_stop。

原错误行在core/skills/md_planning.py：`mode = "analyze" if explanation or conflicts or snapshot is None else "execute"`。snapshot=None覆盖先前execute intent，随后又将task.execution_mode写成analyze。acceptance/evaluate_real_routing.py::predicted_stop首先检查plan.mode，非execute立即返回evidence_only，尚未进入阶段选择。

MD路径不通过旧Capability Resolver重新选择；manifest recall和depends_on直接构建MD节点。legacy路径保持已有routing/capability兼容；hybrid在有MD匹配时进入相同MD路径，因此同样受影响。不是manifest声明read，也不是artifact复用造成（失败用例没有snapshot）。

## 额外定位

“请重新运行模型辨识”已有execute intent，但MD trainer intent_terms只有“系统辨识/训练模型/完成辨识”，缺“模型辨识”，导致无MD候选。仅补manifest的同义召回词与使用说明，未改Registry检索算法或Executor。

修复前30个模式/问法对照在before_modes.json；修复后60个模式/上下文对照在after_modes.json，均位于上述runtime目录。包含任务结构、候选、选中Skill、execution_modes、plan_nodes、依赖展开、已有artifact类型和最终mode。

## 原始堆栈

```text
Creating test database for alias 'default'...
.................FFF.........................................................................s.....s................................................................................................................................................s........................................................................
======================================================================
FAIL: test_stage_prediction_matches_execution_scope (core.test_acceptance.AcceptanceHarnessTests.test_stage_prediction_matches_execution_scope) (text='清洗缺失值')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/komi/Documents/ChatGPT/作品修复/A14/core/test_acceptance.py", line 23, in test_stage_prediction_matches_execution_scope
    self.assertEqual(predicted_stop(plan_skills(text)), expected)
AssertionError: 'evidence_only' != 'cleaning'
- evidence_only
+ cleaning


======================================================================
FAIL: test_stage_prediction_matches_execution_scope (core.test_acceptance.AcceptanceHarnessTests.test_stage_prediction_matches_execution_scope) (text='提取高信噪比动态段')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/komi/Documents/ChatGPT/作品修复/A14/core/test_acceptance.py", line 23, in test_stage_prediction_matches_execution_scope
    self.assertEqual(predicted_stop(plan_skills(text)), expected)
AssertionError: 'evidence_only' != 'selection'
- evidence_only
+ selection


======================================================================
FAIL: test_stage_prediction_matches_execution_scope (core.test_acceptance.AcceptanceHarnessTests.test_stage_prediction_matches_execution_scope) (text='训练系统辨识模型')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/komi/Documents/ChatGPT/作品修复/A14/core/test_acceptance.py", line 23, in test_stage_prediction_matches_execution_scope
    self.assertEqual(predicted_stop(plan_skills(text)), expected)
AssertionError: 'evidence_only' != 'modeling'
- evidence_only
+ modeling


----------------------------------------------------------------------
Ran 315 tests in 19.715s

FAILED (failures=3, skipped=3)
Destroying test database for alias 'default'...
Found 315 test(s).
System check identified no issues (0 silenced).

```
