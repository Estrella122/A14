# GitHub 同步与兼容验收

2026-09-14，开始实现前先 fetch。main 从 13443c0 快进至 origin/main 的 eb240e8，共 5 个上游提交；收尾再次 fetch，HEAD...origin/main=0/0。

保留原有未提交工作：先将 tracked 修改保存为 stash「A14 pre-sync preserved local MD runtime and acceptance work」，快进后 apply；untracked 文件保持在目录中。stash 仍保留作为备份，不自动删除。当前工作区的新旧本地修改均未提交/推送。

唯一文本冲突 .env.example 已合并，保留上游 LLM/生产配置和本地 SKILL_MANIFEST_MODE 示例配置。未覆盖用户实际密钥环境文件。

上游知识库增加 analysis.knowledge_retrieval，本地 MD plan 提前返回导致 2 个 KnowledgeBaseTests KeyError。core/skills/runtime.py 的 MD 路径补充知识检索观测信息，同时写入 agent_context.knowledge_context；采用 detected_scene，仅作为上下文，不改变 MD Skill 决策权。其他历史 Runtime 大段 diff 是本轮开始前的本地工作，不是本次重构。

同步依赖后安装合并 requirements，补齐 certifi/gunicorn；前端 npm ci 使用当前 lockfile。保留上游 LLM gateway、生产加固、知识库与前端配置变更。

| 验证 | 结果 |
| --- | --- |
| 同步基线（依赖补齐后） | 358 tests，2 errors，3 原有 skip |
| 知识库/LLM/生产加固/字段安全/MD Runtime 专项 | 54 passed |
| 最终 manage.py test core | 368 tests，365 passed，0 failure/error，3 原有 skip |
| 本轮新增 Ground Truth 测试 | 10 passed，无 skip |
| npm test | 32 passed，0 skipped |
| npm run lint | PASS，43 JS/Vue 文件 |
| npm run build | PASS |
| git diff --check | PASS |
| 固定高炉真实 12 Executor | 实际调用，数据哈希/Skill/模块/指标与既有固定基线一致 |

3 个已有 skip 来自源文件再分发许可或真实物理量/逆缩放元数据缺口；不是本轮新增，也未被计作数值验收 PASS。

本轮新增代码：tools/evaluate_real_field_ground_truth.py、tools/evaluate_field_agents.py、tools/write_ground_truth_reports.py、core/test_ground_truth_evaluation.py。业务代码仅为合并兼容补充 runtime.py 的知识库上下文；未改变标准化、安全门禁、清洗算法、12 Skill、Registry、Planner 总体架构。新增 datasets/field_ground_truth 语料及 14 个指定报告/收据。

验收限制：没有声称重新做过浏览器 E2E 或生产 LLM 网络验收；这里是自动回归、前端构建和真实数值 Pipeline 兼容验证。原文件授权不明的下载缓存未发布到 GitHub。

## 2026-09-15 GitHub 同步复核

合并远端75376ac（实时事件流/技能状态修复）与本地MD Runtime、统一字段门禁、真实数据验收和需求规范成果。Runtime冲突合并同时保留document_only解释保护和status=skipped保护；远端新增catalog审计测试显式使用SKILL_MANIFEST_MODE=legacy，校验其对应兼容路径，不改变生产模式。

合并后完整本地回归：core 400项，397通过、3个已有数据限制skip，0失败/错误；前端32项通过；lint/build及暂存diff检查PASS。未暂存runtime、原始下载数据或本地.env（仅.env.example）。真实验收的部分测试依赖本地来源文件/运行产物，当前结果是本地环境验证，不宣称全新checkout无数据也能完成真实验收。两个缺数据场景仍UNAVAILABLE，第2项PARTIAL。
