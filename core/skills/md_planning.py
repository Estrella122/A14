"""Manifest matching and dependency nodes for the existing execution runtime."""
from uuid import uuid4
import re
from .artifacts import RuntimeArtifactResolver
from .context import build_data_context


def plan_from_manifests(message, task, snapshot, run_id, registry):
    from .runtime import _entities
    chart_request = "charts" in task.get("requested_outputs", []) and task.get("execution_mode") == "execute"
    # The normalized output intent enriches recall; manifests still decide the Skill.
    recall_message = message + (" 可视化 图表 曲线" if chart_request else "")
    # The three public MCP capabilities are intentionally coarser than the
    # internal Skill names.  Expand their common business wording before MD
    # retrieval so users do not need to know an implementation-level Skill ID.
    execution_recall = task.get("execution_mode") == "execute"
    if execution_recall and re.search(r"高信噪比.*(?:动态|数据段)|动态优选|有效建模数据段", message):
        recall_message += " 提取适合建模的高信噪比动态段"
    if execution_recall and re.search(r"时滞.*共线|共线.*时滞|解耦辨识", message):
        recall_message += " 时滞估计与补偿 共线性诊断与消减 系统辨识训练"
    if execution_recall and re.search(r"闭环寻优|预处理策略.*(?:优化|寻优)|拟合度最高", message):
        recall_message += " 闭环预处理策略寻优"
    candidates = registry.search(recall_message)
    denied = {row["skill_id"] for clause in task.get("negations", [])
              for row in registry.search(clause) if row["score"] >= .45}
    selected = [row["skill_id"] for row in candidates if row["score"] >= .45 and row["skill_id"] not in denied]
    boundary = bool(re.search(r"如果|假如|假设|按钮|原话|原文|引用|这句话|提示|(?:不要|禁止|无需).{0,8}(?:执行|运行|计算)|会不会|能不能|可不可以", message))
    if chart_request:
        boundary = False
    boundary = boundary or bool(re.search(
        r"^\s*(?:请)?(?:介绍|解释|说明|解读)(?:一下)?|"
        r"^\s*(?:请)?(?:告诉我)?如何|怎么证明|做过.+吗|请结合.+说明",
        message,
    ))
    # Reading existing stage results is not authorization to rerun a stage.
    evidence_query = task.get("execution_mode") != "execute" and bool(re.search(
        r"(?:查看|解释|解读|为什么|为何).*(?:结果|指标|筛选|清洗)|(?:当前|已有|现有).*(?:结果|指标)|哪些参数.*(?:重新)?辨识", message))
    explanation = evidence_query or task["task_kind"] in {"knowledge_explanation", "conversation"} or task.get("execution_mode") == "explain" or boundary
    if not selected:
        return None
    available = RuntimeArtifactResolver(snapshot or {}).available_types()
    ordered = registry.resolve_dependencies(selected, available) if not explanation else selected
    conflicts = set(ordered) & denied
    context = build_data_context(snapshot, run_id).public()
    available = RuntimeArtifactResolver(snapshot or {}).available_types()
    nodes, steps, documents = [], [], []
    producer = {}
    for index, skill_id in enumerate(ordered, 1):
        skill = registry.get(skill_id)
        doc = registry.get_prompt_content(skill_id)
        documents.append(f"# {skill.name}\n{doc}")
        kind = "direct" if skill_id in selected else "dependency"
        steps.append({"order": index, "skill_id": skill_id, "name": skill.name, "category": skill.category,
                      "reason": "MD 正文语义匹配" if kind == "direct" else "MD depends_on 依赖",
                      "selection_kind": kind, "relevance_score": next((row["score"] for row in candidates if row["skill_id"] == skill_id), 1),
                      "status": "ready", "manifest_source": "SKILL.md", "manifest_hash": skill.digest})
        if explanation or conflicts:
            continue
        missing = [key for key in skill.requires if key not in available and key not in producer]
        dependencies = list(dict.fromkeys([*(key for key in skill.depends_on if key in ordered), *(producer[k] for k in skill.requires if k in producer)]))
        nodes.append({"id": skill_id, "executor": skill_id, "skill_ids": [skill_id],
            "requested_skill_ids": [skill_id] if kind == "direct" else [], "dependencies": dependencies,
            "requires_artifacts": skill.requires, "produces_artifacts": skill.produces,
            "readiness_status": "blocked" if missing else "ready", "missing_artifacts": missing,
            "readiness_reason": "缺少 MD 声明输入：" + "、".join(missing) if missing else "输入已具备或由上游提供",
            "dispatch_mode": "md_executor", "manifest_hash": skill.digest,
            "capability_dispatch": [{"skill_id": skill_id, "capability": skill_id, "selection_kind": kind}]})
        for artifact in skill.produces:
            producer[artifact] = skill_id
    for row in candidates:
        skill = registry.get(row["skill_id"])
        node = next((node for node in nodes if node["id"] == skill.id), {})
        preconditions = {key: key in available or key in producer for key in skill.requires}
        fit = sum(preconditions.values()) / len(preconditions) if preconditions else 1.0
        requested = row["skill_id"] in selected and not conflicts
        blocked = bool(node.get("missing_artifacts"))
        row.update(candidate=skill.id, display_name=skill.name, final_score=row["score"],
                   semantic_intent_score=round((row["score"] - .1 * row["lexical_recall"]) / .9, 4),
                   context_fit_score=fit, data_precondition_score=fit,
                   scene_fit_score=None, dependency_readiness_score=1.0 if not node.get("dependencies") else None,
                   lexical_recall_score=float(row["lexical_recall"]), preconditions=preconditions,
                   required_artifacts=skill.requires, missing_artifacts=node.get("missing_artifacts", []),
                   selected=requested and not blocked and not explanation,
                   status="documentation" if explanation and requested else "blocked" if requested and blocked else "selected" if requested else "skipped",
                   reason="缺少 MD 声明输入" if blocked else "MD 正文匹配后通过任务边界；执行仍检查 requires" if requested else "未通过评分或否定边界")
    content = "\n\n".join(documents)
    mode = "analyze" if explanation or conflicts or (snapshot is None and task.get("execution_mode") != "execute") else "execute"
    task = {**task, "execution_mode": "explain" if explanation else mode,
            "requires_clarification": bool(conflicts)}
    selected_rows = [{"capability": key, "selected_skill_ids": [key], "reason": "SKILL.md"} for key in selected] if not explanation else []
    blocked_rows = [row for row in candidates if row["status"] == "blocked"]
    executable = [row["skill_id"] for row in candidates if row["selected"]]
    return {"plan_id": "plan_" + uuid4().hex[:12], "run_id": run_id, "objective": task["objective"],
        "user_message": message, "mode": mode, "entities": _entities(message),
        "parameters": {p["name"]: p["value"] for p in task.get("parameters", [])}, "constraints": task.get("constraints", {}),
        "selected_count": len(steps), "direct_skill_ids": selected, "direct_count": len(selected), "steps": steps,
        "candidates": candidates, "execution_contract": {"executor": "md_skill_executor_registry", "supported_parameters": [], "unapplied_parameters": []},
        "analysis": {"mode": mode, "routing_source": "md_registry", "needs_clarification": bool(conflicts),
            "dependency_conflicts": sorted(conflicts), "full_pipeline_requested": False, "excluded_skills": sorted(denied),
            "unresolved_clauses": [], "task_understanding": task, "data_context": context,
            "capability_resolution": {"selected": executable, "candidates": candidates, "documentation": selected if explanation else [], "blocked": blocked_rows, "skipped": []},
            "skill_resolution": {"selected_skills": selected, "blocked_capabilities": [], "skipped_capabilities": []},
            "analysis_plan": {"selected_capabilities": selected_rows, "blocked_capabilities": blocked_rows, "skipped_capabilities": []},
            "execution_plan": {"executor": "md_registry", "capabilities": selected, "blocked": [], "skipped": [],
                               "core": {"version": "md-executor-dag-v1", "steps": nodes, "target_groups": selected}},
            "skill_runtime": {"selected_skill": None, "sources": [registry.get_manifest(k)["manifest_path"] for k in ordered],
                              "context": content, "manifest_source": "SKILL.md", "loaded_business_skills": ordered},
            "agent_context": {"base_agent_context": "ProcessPilot Agent Runtime", "loaded_skill_context": content,
                              "task_context": {"user_message": message, "run_id": run_id}, "data_context": context}}}
