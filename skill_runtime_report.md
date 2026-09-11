# 项目 Skill Runtime 动态加载报告

## 当前架构与原缺口

总控入口为 `core/skills/runtime.py::plan_skills`，对话服务和 Agent API 都调用它。原链路直接通过 `analysis_plan.py` adapter 调用 `industrial-analysis/scripts/build_analysis_plan.py`。因为 Runtime 没有扫描 `SKILL.md`、解析声明、选择资源或注入上下文的步骤，所以 `SKILL.md` 只是文档。

本次保留原 30 Skill DAG、Agent API、Pipeline 和 analysis_plan adapter，只在计划阶段加入通用 Discovery → Resolver → Loader → Context Injector。

## Skill Discovery

`core/skills/skill_loader.py::discover_skills` 扫描配置的 Skill 根目录下 `*/SKILL.md`。它读取 YAML frontmatter 的 `name`、`description`，并解析 `SKILL.md` 内的 `skill-runtime-manifest`。manifest 声明 triggers、capabilities、workflows、references、scripts、input requirements 和 output contract。

Runtime 不包含 `industrial-analysis` 名称判断。新增 Skill 只要遵守相同入口和 manifest 结构即可被发现。

## Resolver、Loader 与 Context Injector

Resolver 按各 Skill 自己声明的 triggers 评分，选择命中最多的 Skill；平分时按名称稳定排序，并保留全部候选及分数供调试。与工业无关的请求没有命中时不加载任何 Skill。

Loader 再根据所选 Skill manifest 中每个 capability 的 triggers 选择资源。通用 workflow、unknown workflow、验证 workflow 和 references 都由 manifest 的声明路径加载。所有路径必须是 Skill 根目录内的相对路径；绝对路径、`../` 越界、未声明资源和缺失文件都会被拒绝或记录为可降级错误。只有 manifest 声明为 `ANALYSIS_PLAN` 且实际存在的 script 才会进入 invoked_scripts。

Context Injector 在 `plan_skills().analysis.agent_context` 中分开记录：

- `base_agent_context`：基础 Agent Runtime 身份。
- `loaded_skill_context`：带 `[source: relative/path]` 来源标记的动态 Skill 内容。
- `task_context`：objective 与 run_id。
- `data_context`：本次 scene。

这套工程是规则型总控，没有独立 LLM system prompt；以上结构是其真实 Agent 上下文入口，对话服务随后消费同一份 plan。

## Lazy Loading 与兼容

每次只加载 SKILL.md、命中的 capability、所需 workflow 和 references。“工业异常分析”不会加载 energy-analysis 或 equipment-health。性能 trace 记录 Skill 总数、扫描耗时、加载 Skill 数、capability 数、上下文字符数和 token 估算。

新流程先读取 SKILL.md 并确定资源，再通过原 `analysis_plan.py` adapter 调用声明的 `build-analysis-plan`。旧的 `Agent → analysis_plan.py` 调用仍保留，可作为兼容 fallback；工业分析算法没有改动。

## 修改文件

- `core/skills/skill_loader.py`：通用 Discovery、Resolver、Loader、安全路径校验与 Context Injector。
- `core/skills/industrial-analysis/SKILL.md`：新增 Runtime manifest，成为机器可读入口。
- `core/skills/runtime.py`：在 plan 阶段接入动态 Skill 上下文和 trace。
- `core/test_skill_loader.py`：动态发现、路由、缺失资源、双 Skill、非工业请求与注入测试。

## 完整加载 trace

请求：`分析工业数据中的异常`

```json
{
  "discovered_skills": ["industrial-analysis"],
  "selected_skill": "industrial-analysis",
  "loaded_capabilities": ["ANOMALY_DETECTION"],
  "loaded_workflows": ["generic-analysis", "unknown-scene"],
  "loaded_references": ["evidence-rules", "confidence-rules"],
  "invoked_scripts": ["build-analysis-plan"],
  "sources": [
    "SKILL.md",
    "capabilities/anomaly-detection.md",
    "workflows/generic-analysis.md",
    "workflows/unknown-scene.md",
    "references/evidence-rules.md",
    "references/confidence-rules.md"
  ],
  "errors": [],
  "performance": {
    "skill_count": 1,
    "loaded_skill_count": 1,
    "capability_count": 1,
    "context_characters": 5237,
    "estimated_tokens": 1310
  }
}
```

这条请求未提供已知 scene，因此加载 unknown-scene 安全 workflow。

## 非工业任务 trace

请求：`修改登录页面按钮颜色`

```json
{
  "discovered_skills": ["industrial-analysis"],
  "selected_skill": null,
  "loaded_capabilities": [],
  "loaded_workflows": [],
  "loaded_references": [],
  "invoked_scripts": [],
  "sources": [],
  "errors": [],
  "performance": {
    "skill_count": 1,
    "loaded_skill_count": 0,
    "capability_count": 0,
    "context_characters": 0,
    "estimated_tokens": 0
  }
}
```

## 测试结果与剩余风险

测试覆盖工业异常、工业能耗、unknown scene、非工业任务、两个 Skill 竞争、缺失 SKILL.md、缺失 capability、manifest 元数据和总控上下文注入。完整相关测试共 103 项，全部通过，Django system check 无告警。

当前 manifest 使用嵌入 SKILL.md 的 JSON 块，避免新增 YAML 运行依赖。Discovery 每次计划都会扫描本地目录；现有 Skill 数量很少，实测为毫秒级。未来 Skill 数量显著增加时，可加入基于文件修改时间的缓存。
