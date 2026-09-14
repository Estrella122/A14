# 全量回归与同步验收

2026-09-14，本轮开始与结束均 fetch GitHub，基线 main=eb240e8；origin/main 无新增差异。工作区此前未提交的修改保持原状；本轮无 commit/push。

| 检查 | 结果 |
| --- | --- |
| manage.py test core | 381 total，378 passed，3 原有 skipped，0 failure/error |
| 新增 final acceptance 专项 | 13 tests，无新增 skip |
| 既有物理门禁 / Ground Truth / OOD / 清洗 | 包含于全量，通过 |
| pipeline rejection / real dataset / 三场景 | 包含于全量，通过；原有不可得数据 skip 如实保留 |
| MD runtime / planning / routing / knowledge integration | 包含于全量，通过 |
| npm test | 32 passed，0 skipped |
| npm run lint | PASS |
| npm run build | PASS |
| git diff --check | PASS |
| 固定高炉真实数值回归 | 12 个 Executor 实际调用；hash、Skill、module、metrics 与基线一致 |
| 真实字段复评 | 脱丁烷错接受 24/43 → 0/43；三场景已正确接受字段新增误拒 0 |

初版统一门禁使 4 个旧断言失败，原因是旧测试要求 U1…U8 在无物理元数据时被接受或仅阻断部分 U 列。现保留原测试目的，并精确检查匿名列不再 AUTO_ACCEPT、8 个 required 均受阻、场景不能 confirmed；没有删除测试、放宽门禁或新增 skip。

旧 skip：缺再分发许可数据文件；缺真实物理量/可信 inverse metadata 的两项数值验收。未计作实际三场景 Pipeline PASS。

本轮业务修改：

- integrations/standardization/standard_agent/engine.py：所有最终接受及人工覆盖经过统一 gate；去重不能恢复物理冲突。
- integrations/standardization/standard_agent/physical_semantics.py：统一 Final Acceptance Gate；alias 源冲突优先；匿名/缩放元数据检查；point 和元数据场景/单位绑定。
- core/services/dataset_evidence.py：离线 inverse 字段绑定也经过同一 gate，增加 scenario 与物理一致性约束。

测试修改：core/test_final_field_acceptance.py（新增13项）、core/test_debutanizer.py、core/test_debutanizer_contract.py、core/test_three_scene_final.py。新增两个评测/报告脚本、datasets/field_acceptance_safety 证据及13份交付文档/收据。没有改 alias、required、阈值、模型权重、Skill Runtime 或工业算法。

日志/哈希位于 datasets/field_acceptance_safety/validation。未声称运行新的浏览器 E2E、在线 LLM 或生产服务验收。本轮原始下载候选只在被忽略的 runtime 缓存中，未发布不明再分发许可数据。
