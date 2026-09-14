# 工业知识库

知识库用于补强 Agent 的 Skill 候选召回，但不替代确定性路由、执行契约和安全门禁。第一版采用结构化词法检索，避免在没有真实问句评测集时贸然引入 embedding 模型。

## 数据层

- `KnowledgeDocument` / `KnowledgeChunk`：版本、来源、校验值、审核状态和可检索片段。
- `KnowledgeEntity` / `KnowledgeAlias`：场景、变量、设备与 Skill 的标准名称和别名。
- `KnowledgeRelation`：变量归属等可追溯关系。
- `SkillKnowledgeRule`：正向术语、排除术语、前置产物、置信度和规则依据。
- `RoutingFeedback`：保存预测、人工纠正和复核结果；反馈不会未经审核自动改写生产规则。

只有 `approved` 数据能参与检索。检索结果写入 Agent 计划的 `analysis.knowledge_retrieval` 与 `agent_context.knowledge_context`，包含规则 ID、命中词、来源文档和分数。

## 初始化和维护

```bash
python manage.py migrate
python manage.py seed_knowledge_base
```

种子命令幂等，写入 3 个正式场景、16 个变量实体和 30 条 Skill 规则。`npm run setup`、`npm run dev` 与 Docker API 启动会自动执行它。管理员可在 `/admin/` 审核文档、实体和规则。

接口：

- `GET /api/knowledge/summary/`
- `GET /api/knowledge/search/?q=...&scene_id=...`
- `POST /api/knowledge/feedback/`

前端入口：`/knowledge-base/`。

## 后续向量化门槛

累计至少 200 条经过人工标注的真实问句，并按场景、设备和意图分层切分训练集与固定测试集后，再比较 BM25/向量/混合检索。只有固定测试集的 Top-1、Top-3、误触发率和拒识率都优于当前规则，才启用向量检索；embedding 版本、语料 checksum 和评测报告必须同时登记。
