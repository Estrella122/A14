# A14 Skill 迁移报告

## 结论

本次在既有 `core/skills` 运行时内完成增量重构。30 个 Skill 的 ID、分类数量、依赖执行图、API 与 Pipeline 执行器保持兼容；没有创建平行 Skill 系统，也没有删除原 Skill。

完整逐项扫描见 `core/skills/skill_inventory.md`。

## 修改前与修改后目录

修改前：

```text
core/skills/
├── README.md
├── __init__.py
├── catalog.py
├── router_model.py
├── routing.py
├── runtime.py
└── models/skill_router.json.gz
```

修改后：

```text
core/skills/
├── README.md
├── __init__.py
├── analysis_plan.py       # 独立工业分析 Skill 的兼容 adapter
├── industrial-analysis/   # 项目 Agent 可独立加载的通用能力包
├── catalog.py             # 原30 Skill + 工程元数据 + 集中场景别名
├── router_model.py
├── routing.py
├── runtime.py             # 原计划输出中增量加入 analysis_plan
├── skill_inventory.md     # 全量现状扫描
├── work_repair.py         # 作品修复工程级多标签路由
└── models/skill_router.json.gz
```

## 原问题与工程级结构

- 场景识别分散在 `runtime.py` 与 `agent_chat.py`，且“炉”会把加热炉误识别为高炉。
- 30 个 Skill 缺少工程任务类型、作用域、引用、重叠与硬编码风险元数据。
- 工业能力按既有算法阶段组织，缺少分析前 capability 选择和跳过理由。
- 工程任务没有多标签路由和可审查的按需加载清单。

新工程级入口为 `work_repair.route_work_repair_task`。它支持需求指定的 13 类任务，一个任务可命中多个类型；输出只包含命中任务需要的 reference/workflow。示例“Steel 数据识别正确，但页面要求高炉字段”会同时命中 `SCENE_RECOGNITION`、`PIPELINE`、`FRONTEND_PAGE`、`BUG_DIAGNOSIS`。

## 原 Skill 到新结构的映射

- 原 `catalog.py`：保留 30 个 Skill 定义，新增任务类型、作用域、references、overlap、硬编码风险等元数据。
- 原 `routing.py`、`router_model.py`：保留原职责和调用方式。
- 原 `runtime.py`：保留 DAG 与执行协议，在计划的 `analysis.analysis_plan` 中增加通用能力计划。
- 原 `agent_chat._scenario_family`：迁移到 `catalog.resolve_scene_family`，聊天服务继续通过兼容函数调用。
- 原字段统一、清洗、辨识与寻优实现：全部保留，通用 Skill 仅消费其输出，不复制算法。
- 删除内容：无。过宽的单字场景别名“炉”被移除，因为它会污染加热炉、锅炉等场景识别。

## Lazy Loading

`work_repair.py` 按任务类型返回 reference/workflow；`industrial-analysis/SKILL.md` 再按实际目标加载 workflow、capability 和 reference。字段、场景、Pipeline 与工业分析资料不会在每次请求中全部加载。

## API、Pipeline 与风险

API 仍输出原计划字段，`analysis_plan` 是向后兼容的新增字段。执行仍由 `validated_pipeline_bundle` 完成。现网可执行场景仍为高炉、脱丁烷塔、工业干燥器；新增三个场景名目前只用于分析计划软路由，真实执行需由 Scene Registry 和字段知识后续接入。前端仍有 demo/mock 的高炉 fallback，它们属于展示兼容逻辑，本次未扩大范围修改。

## 验证

- Python 编译检查通过。
- 新增工程级多标签路由、14 capability 契约、五场景计划、unknown 安全边界、加热炉/锅炉防误识别回归。
- 相关测试共 94 项并全部通过；覆盖裸“1号塔”兼容、低字段置信度传播、五场景计划和 unknown 安全边界。
