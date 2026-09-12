from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from django.conf import settings

from .analysis_plan import build_analysis_plan
from .task_understanding import understand_task
from .catalog import CATEGORIES, SKILLS, SKILL_MAP, identify_scene_from_text
from .context import build_data_context
from .routing import select
from .skill_loader import default_skill_roots, load_skill_context
from .skill_loader import discover_skills
from .skill_resolver import resolve_skills
from .executor import get_executor
from .execution_plan import build_execution_plan
from .artifacts import RuntimeArtifactResolver


RUNS_DIR = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / "agent_skill_runs"

# Expert questions rarely use the exact wording of a feature button. This semantic
# coverage table keeps the 30 skills stable while accepting control-engineering,
# data-science and deployment terminology used during reviews.
EXPERT_ROUTING_RULES = [
    (("采样周期", "采样频率", "奈奎斯特频率", "混叠", "aliasing"), ("time_axis_alignment_resampler",)),
    (("信噪比", "snr", "噪声水平", "滤波"), ("signal_noise_ratio_estimator", "high_snr_dynamic_segment_extractor")),
    (("持续激励", "激励充分", "可辨识", "阶跃激励", "输入激励"), ("steady_transient_state_detector", "segment_quality_scorer_ranker", "modeling_dataset_assembler")),
    (("候选段降级", "降级建模", "严格优质动态段", "0个严格", "参数可信度", "候选模型"), ("segment_quality_scorer_ranker", "modeling_dataset_assembler", "model_diagnostics_evaluator", "engineering_result_interpreter")),
    (("数据泄漏", "未来信息", "时间穿越", "泄露"), ("modeling_dataset_assembler", "evidence_audit_reproducer")),
    (("残差", "白噪声", "自相关", "独立性", "正态性"), ("model_diagnostics_evaluator",)),
    (("稳定性", "极点", "单位圆", "发散"), ("arx_structure_order_selector", "model_diagnostics_evaluator")),
    (("频率特性", "频响", "伯德", "bode", "奈奎斯特", "nyquist", "阶跃响应", "超调量", "调节时间"), ("model_diagnostics_evaluator", "engineering_visualization_builder")),
    (("因果", "因果性", "相关不等于因果", "外生变量"), ("time_delay_estimator_compensator", "engineering_result_interpreter")),
    (("过拟合", "泛化", "交叉验证", "验证集", "训练集", "测试集", "训练测试", "训练/测试"), ("modeling_dataset_assembler", "multi_model_benchmark", "model_diagnostics_evaluator")),
    (("阶次", "aic", "bic", "参数量", "结构选择"), ("arx_structure_order_selector", "multi_model_benchmark")),
    (("vif", "共线", "条件数", "冗余变量"), ("collinearity_detector_reducer",)),
    (("时滞", "纯滞后", "互相关估计", "负时滞", "延迟"), ("time_delay_estimator_compensator",)),
    (("目标函数", "约束", "收敛", "停止条件", "局部最优", "寻优策略", "闭环寻优", "最佳候选", "最优候选", "最优模型", "各轮候选", "候选结果", "数据覆盖率", "综合得分", "目标权重", "权重敏感性", "敏感性分析"), ("closed_loop_preprocessing_optimizer",)),
    (("复现", "随机种子", "审计", "追溯", "版本"), ("experiment_tracker_comparator", "evidence_audit_reproducer")),
    (("上线", "投运", "生产使用", "安全边界", "联锁", "闭环控制", "验收", "可验收"), ("engineering_result_interpreter", "evidence_audit_reproducer")),
    (("迁移", "泛化到", "其他设备", "其他塔", "其他炉", "跨场景"), ("dataset_scenario_profiler", "semantic_field_unit_standardizer", "model_diagnostics_evaluator")),
    (("在线学习", "实时更新", "概念漂移", "模型漂移", "漂移监测"), ("experiment_tracker_comparator", "execution_supervisor_replanner")),
    (("缺失机制", "插值", "线性插值", "异常值", "异常点", "离群点", "鲁棒", "平滑动态"), ("missing_anomaly_cleaner",)),
    (("单位", "量纲", "字段映射", "语义映射", "变量角色"), ("semantic_field_unit_standardizer",)),
    (("报告", "产物", "导出", "下载", "证据链"), ("expert_report_writer", "final_artifact_exporter", "evidence_audit_reproducer")),
]
ROUTING_TOPIC_KEYS = (
    "sampling", "snr", "excitation", "degraded_modeling", "leakage", "residual", "stability", "frequency", "causality",
    "generalization", "order", "collinearity", "lag", "optimization", "reproducibility", "deployment",
    "transfer", "drift", "cleaning", "standardization", "delivery",
)


def list_skills() -> dict[str, Any]:
    return {"total": len(SKILLS), "categories": CATEGORIES, "skills": [skill.public() for skill in SKILLS]}


def _entities(message: str) -> dict[str, Any]:
    equipment = re.search(r"(\d+)\s*号\s*(钢铁高炉|炼铁高炉|脱丁烷塔|脱丁烷精馏塔|精馏塔|工业干燥器|干燥器|干燥机|烘干机|高炉|塔|炉)", message)
    equipment_id = f"{equipment.group(1)}号{equipment.group(2)}" if equipment else None
    scene_id, scene_name, _scene_family = identify_scene_from_text(message, equipment_id)
    # 兼容规则只做意图解码，不替换现网三套执行场景以外的主流程约束。
    selected_scene_id = scene_id if scene_id in {"blast_furnace", "debutanizer_column", "industrial_dryer"} else None
    selected_scene = scene_name
    if not selected_scene and equipment_id and equipment_id.endswith("塔"):
        selected_scene = "炼油脱丁烷精馏塔"
        selected_scene_id = "debutanizer_column"
    return {
        "equipment_id": equipment_id,
        "scenario": selected_scene,
        "scenario_id": selected_scene_id,
    }


def _parameters(message: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    rules = (("resample_seconds", r"(?:采样(?:周期)?|按|改为|使用)\s*(\d+)\s*(?:秒|s\b)"), ("max_lag", r"(?:时滞|max[_ ]?lag)[^\d]{0,5}(\d+)"), ("model_order", r"(?:阶次|order)[^\d]{0,5}(\d+)"))
    for key, pattern in rules:
        match = re.search(pattern, message, re.I)
        if match:
            output[key] = int(match.group(1))
    return output


def _request_analysis(message: str) -> dict[str, Any]:
    normalized = message.lower()
    action_starts = ("提取", "筛选", "清洗", "规整", "生成", "训练", "建立", "优化", "寻优", "导出", "处理")
    explicit_actions = ("重新执行", "重新运行", "重跑", "开始执行", "立即执行", "运行一遍", "请执行", "帮我执行", "给我生成")
    question_like = normalized.startswith(("为什么", "如何", "怎么", "是否", "能否", "可以", "哪个", "什么")) or normalized.endswith(("吗", "呢", "?", "？"))
    imperative = normalized.strip().startswith(action_starts) or any(word in normalized for word in explicit_actions)
    mode = "execute" if imperative and (not question_like or any(word in normalized for word in explicit_actions)) else "analyze"
    topics = []
    topic_hits = {}
    for topic, (terms, _) in zip(ROUTING_TOPIC_KEYS, EXPERT_ROUTING_RULES):
        hits = [term for term in terms if term.lower() in normalized]
        if hits:
            topics.append(topic)
            topic_hits[topic] = hits
    metrics = [metric for metric in ("r²", "r2", "rmse", "mae", "aic", "bic", "ljung-box", "vif") if metric in normalized]
    return {
        "mode": mode, "question_type": "compound" if len(topics) > 1 else "single",
        "topics": topics, "topic_hits": topic_hits, "requested_metrics": metrics,
        "safety": {"deny_production_claim": any(word in normalized for word in ("上线", "投运", "生产使用"))},
    }


def _direct_matches(message: str, analysis: dict[str, Any]) -> tuple[set[str], dict[str, float], list[dict[str, Any]]]:
    normalized = message.lower()
    matches: set[str] = set()
    scores: dict[str, float] = {}
    candidates: list[dict[str, Any]] = []
    matched_topics = set(analysis["topics"])
    for topic, (terms, skill_ids) in zip(ROUTING_TOPIC_KEYS, EXPERT_ROUTING_RULES):
        hits = [term for term in terms if term.lower() in normalized]
        if not hits:
            continue
        for skill_id in skill_ids:
            score = min(0.86 + 0.03 * (len(hits) - 1), 0.98)
            matches.add(skill_id)
            scores[skill_id] = max(scores.get(skill_id, 0), score)
            candidates.append({"skill_id": skill_id, "score": score, "reason": f"专业主题 {topic}：{'、'.join(hits)}", "selected": True})

    # Expert analysis uses the curated topic matrix exclusively. Broad lexical
    # triggers such as “测试集” or “工况” must not activate generators/detectors.
    if analysis["mode"] == "execute" or not matched_topics:
        for skill in SKILLS:
            hits = [trigger for trigger in skill.triggers if trigger != "*" and trigger.lower() in normalized]
            if not hits:
                continue
            excluded = (
                skill.id == "industrial_simulation_generator" and not any(word in normalized for word in ("仿真", "生成", "创建"))
            ) or (skill.id == "expert_report_writer" and not any(word in normalized for word in ("报告", "总结", "评审")))
            score = 0.42 if excluded else min(0.68 + 0.04 * (len(hits) - 1), 0.84)
            candidates.append({"skill_id": skill.id, "score": score, "reason": f"术语命中：{'、'.join(hits)}", "selected": not excluded})
            if not excluded:
                matches.add(skill.id)
                scores[skill.id] = max(scores.get(skill.id, 0), score)

    if not matches or any(word in normalized for word in ("总结", "全部", "全流程", "整体")):
        for skill_id in ("engineering_result_interpreter", "expert_report_writer", "evidence_audit_reproducer"):
            matches.add(skill_id)
            scores[skill_id] = max(scores.get(skill_id, 0), 0.72)
    return matches, scores, candidates


def _with_dependencies(selected: set[str]) -> list[str]:
    resolved: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []
    def visit(skill_id: str):
        if skill_id in resolved:
            return
        if skill_id not in SKILL_MAP:
            raise ValueError(f"未知依赖技能：{skill_id}")
        if skill_id in visiting:
            raise ValueError(f"技能依赖存在环：{skill_id}")
        visiting.add(skill_id)
        for dependency in SKILL_MAP[skill_id].depends_on:
            visit(dependency)
        visiting.remove(skill_id)
        resolved.add(skill_id)
        ordered.append(skill_id)
    for item in sorted(selected):
        visit(item)
    return ordered


def plan_skills(message: str, run_id: str | None = None, snapshot: dict[str, Any] | None = None, conversation_context: dict[str, Any] | None = None) -> dict[str, Any]:
    text = str(message or "").strip()
    if not text:
        raise ValueError("规划指令不能为空。")
    analysis = _request_analysis(text)
    task_understanding = understand_task(text, conversation_context)
    try:
        route = select(text, analysis, EXPERT_ROUTING_RULES, ROUTING_TOPIC_KEYS)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        route = {"direct": set(), "scores": {}, "mode": "analyze", "decisions": [],
                 "denied": set(), "needs_clarification": True, "unresolved_clauses": [text],
                 "source": "model_unavailable", "full_pipeline_requested": False,
                 "negative_clauses": [], "error": type(exc).__name__}
    recalled_skill_ids, relevance_scores = route["direct"], route["scores"]
    lexical_candidates = [candidate for decision in route["decisions"] for candidate in decision["candidates"]]
    if snapshot is None and run_id:
        from core.services.pipeline import get_run
        snapshot = get_run(run_id)
    data_context = build_data_context(snapshot, run_id).public()
    discovered_skills, _discovery_metrics = discover_skills(default_skill_roots())
    skill_resolution = resolve_skills(task_understanding, data_context, discovered_skills, recalled_skill_ids, lexical_candidates)
    capability_resolution = skill_resolution["capability_resolution"]
    capability_skill_ids = set(capability_resolution["resolved_skill_ids"])
    # The trained router is the user's direct business intent. Capability
    # resolution may block data-dependent analysis when no run snapshot exists,
    # but it must not erase the skill the Agent learned to call.
    routed_business_skills = set(recalled_skill_ids) if task_understanding["task_kind"] != "knowledge_explanation" else set()
    operational = set(recalled_skill_ids) if task_understanding["task_kind"] in {"execute_pipeline", "artifact_request"} else set()
    direct = capability_skill_ids | routed_business_skills | operational
    if task_understanding["task_kind"] == "execute_pipeline" and any(term in text for term in ("重规划", "失败后重试")):
        direct.add("execution_supervisor_replanner")
    runtime_mode = getattr(settings, "AGENT_RUNTIME_MODE", "hybrid")
    execution_mode = route["mode"] if runtime_mode == "legacy" else task_understanding["execution_mode"]
    if route.get("source") == "model_unavailable":
        execution_mode = "analyze"
    if execution_mode == "explain":
        execution_mode = "analyze"
    detected_scene_id = data_context.get("detected_scene")
    if not detected_scene_id:
        detected_scene_id, _detected_scene_name, _detected_family = identify_scene_from_text(text)
    documents = capability_resolution["selected"] + capability_resolution["documentation"]
    skill_runtime = load_skill_context(
        text,
        default_skill_roots(),
        scene=detected_scene_id or "unknown_scene",
        selected_capabilities=documents,
        selected_skill_name=skill_resolution["selected_skills"][0] if skill_resolution["selected_skills"] else None,
        task_kind=task_understanding["task_kind"],
    )
    analysis_plan = build_analysis_plan(
        text,
        list(direct),
        scene=detected_scene_id or "unknown_scene",
        evidence=data_context,
        capability_resolution=capability_resolution,
        task_understanding=task_understanding,
    )
    needs_clarification = bool(task_understanding.get("requires_clarification") or (task_understanding["task_kind"] not in {"knowledge_explanation", "conversation"} and not direct))
    core_execution_plan = build_execution_plan(task_understanding, [skill.id for skill in SKILLS if skill.id in direct], data_context)
    analysis.update({"mode": execution_mode, "routing_source": route["source"],
                     "needs_clarification": needs_clarification,
                     "unresolved_clauses": route["unresolved_clauses"],
                     "routing_decisions": route["decisions"],
                     "excluded_skills": sorted(route["denied"]),
                     "full_pipeline_requested": route["full_pipeline_requested"],
                     "analysis_plan": analysis_plan,
                     "task_understanding": task_understanding,
                     "data_context": data_context,
                     "capability_resolution": capability_resolution,
                     "skill_resolution": skill_resolution,
                     "execution_plan": {
                         "executor": "industrial-analysis" if "industrial-analysis" in skill_resolution["selected_skills"] else None,
                         "capabilities": capability_resolution["selected"],
                         "blocked": skill_resolution["blocked_capabilities"],
                         "skipped": skill_resolution["skipped_capabilities"],
                         "core": core_execution_plan,
                     },
                     "skill_runtime": skill_runtime,
                     "agent_context": {
                         "base_agent_context": "ProcessPilot Agent Runtime",
                         "loaded_skill_context": skill_runtime["context"],
                         "task_context": {"objective": task_understanding["objective"], "user_message": text, "run_id": run_id},
                         "data_context": data_context,
                     }})
    runtime_skills = {"industrial_intent_parser", "skill_capability_matcher", "workflow_dag_planner", "evidence_audit_reproducer"}
    if execution_mode == "execute":
        runtime_skills.add("execution_supervisor_replanner")
    if execution_mode == "execute":
        pipeline_targets = {"dataset_scenario_profiler", "semantic_field_unit_standardizer", "time_axis_alignment_resampler", "missing_anomaly_cleaner", "high_snr_dynamic_segment_extractor", "system_identification_trainer", "closed_loop_preprocessing_optimizer"}
        needs_pipeline = bool(direct & pipeline_targets)
        ordered = _with_dependencies((direct & pipeline_targets) | runtime_skills) if needs_pipeline else [skill.id for skill in SKILLS if skill.id in runtime_skills]
        ordered += [skill.id for skill in SKILLS if skill.id in direct and skill.id not in ordered]
        conflicts = set(ordered) & route["denied"]
        if conflicts:
            analysis["needs_clarification"] = True
            analysis["dependency_conflicts"] = sorted(conflicts)
            execution_mode = analysis["mode"] = "analyze"
            runtime_skills.discard("execution_supervisor_replanner")
            ordered = [skill.id for skill in SKILLS if skill.id in direct | runtime_skills and skill.id not in route["denied"]]
    else:
        ordered = [skill.id for skill in SKILLS if skill.id in direct | runtime_skills and skill.id not in route["denied"]]
    entities = _entities(text)
    parameters = _parameters(text)
    steps = []
    for index, skill_id in enumerate(ordered, 1):
        skill = SKILL_MAP[skill_id]
        reason = "用户目标直接命中" if skill_id in direct else "Agent 运行时治理" if skill_id in runtime_skills else "上游依赖自动补齐"
        steps.append({"order": index, "skill_id": skill.id, "name": skill.name, "category": skill.category, "reason": reason, "selection_kind": "direct" if skill_id in direct else "governance" if skill_id in runtime_skills else "dependency", "relevance_score": relevance_scores.get(skill_id, 1.0 if skill_id in runtime_skills else 0.68), "status": "ready"})
    return {
        "plan_id": f"plan_{uuid4().hex[:12]}", "run_id": run_id, "objective": task_understanding["objective"], "user_message": text,
        "mode": execution_mode, "analysis": analysis, "entities": entities, "parameters": parameters,
        "execution_contract": {"executor": "skill_executor_registry" if runtime_mode == "skill_runtime" else "hybrid_skill_executor_with_pipeline_fallback" if runtime_mode == "hybrid" else "validated_pipeline_bundle" if execution_mode == "execute" else "evidence_only",
                               "supported_parameters": ["resample_seconds", "max_lag"],
                               "unapplied_parameters": [k for k in parameters if k not in {"resample_seconds", "max_lag"}]},
        "constraints": {"local_execution": True, "auditable": True, "execution_scope": "bundled_pipeline_then_evidence_read"},
        "selected_count": len(steps), "direct_skill_ids": [skill.id for skill in SKILLS if skill.id in direct],
        "direct_count": len(direct), "steps": steps, "candidates": capability_resolution["candidates"],
    }


def _summary(snapshot: dict[str, Any], handler: str) -> tuple[dict, list, list, list]:
    results = snapshot.get("results", {})
    standard = results.get("standardization", {})
    cleaning = results.get("cleaning", {})
    modeling = results.get("modeling", {})
    optimization = results.get("optimization", {})
    review = results.get("review", {})
    artifacts = snapshot.get("artifacts", {})
    test = modeling.get("metrics", {}).get("test", {})
    metrics_by_handler = {
        "standardization": {"scenario": standard.get("scenario", {}).get("scenario_name"), "required_coverage": standard.get("mapping", {}).get("required_coverage")},
        "cleaning": {"quality_score": cleaning.get("overall_score"), "cleaned_rows": cleaning.get("cleaned_row_count"), "missing_rate": cleaning.get("missing_rate", {})},
        "selection": {"selected_segments": cleaning.get("selected_segment_count"), "modeling_rows": cleaning.get("modeling_row_count"), "dynamic_score": cleaning.get("dimension_scores", {}).get("dynamic"), "snr": cleaning.get("snr"), "split": cleaning.get("split")},
        "lag": {"lags": modeling.get("lags", [])},
        "collinearity": {"input_count": len(modeling.get("input_cols", [])), "selected_count": len(modeling.get("selected_inputs", [])), "details": modeling.get("collinearity", {})},
        "modeling": {"output": modeling.get("output_col"), "selected_inputs": modeling.get("selected_inputs", []), **test, "diagnostics": modeling.get("diagnostics"), "order_search": modeling.get("order_search"), "config": modeling.get("config")},
        "optimization": {"best_round": optimization.get("best_round"), "best_score": optimization.get("best_score"), "best_parameters": optimization.get("best_parameters", {}), "evaluation_split": optimization.get("evaluation_split"), "test_evaluations": optimization.get("test_evaluations")},
        "review": {"passed": review.get("passed"), "conclusion": review.get("conclusion"), "warnings": review.get("warnings", [])},
        "report": {"title": results.get("report", {}).get("title"), "available": "analysis_report_md" in artifacts},
        "artifact": {"artifact_keys": list(artifacts)},
        "audit": {"run_id": snapshot.get("run_id"), "stage_count": len(snapshot.get("stages", [])), "artifact_count": len(artifacts)},
        "experiment": {"run_id": snapshot.get("run_id"), **test},
        "asset": {"dataset": snapshot.get("original_name"), "run_id": snapshot.get("run_id")},
    }
    metrics = metrics_by_handler.get(handler, {"run_id": snapshot.get("run_id"), "evidence_available": bool(results)})
    artifact_keys = {
        "selection": ["segments_csv", "snr_csv", "modeling_csv"],
        "modeling": ["modeling_csv", "metrics_json", "diagnostics_json", "order_search_json", "fitted_state_json"],
        "collinearity": ["summary_json"], "lag": ["delays_csv"], "cleaning": ["cleaned_csv", "report_json"],
        "standardization": ["standardized_csv"], "optimization": ["optimization_json"],
        "report": ["analysis_report_md"], "audit": ["audit_json"], "asset": ["source_csv"], "review": ["review_json"],
    }
    related = [key for key in artifact_keys.get(handler, []) if key in artifacts]
    evidence = [f"pipeline:{snapshot.get('run_id')}", f"results:{handler}"]
    required_result = {"selection": "cleaning", "lag": "modeling", "collinearity": "modeling",
                       "asset": "standardization", "audit": "audit", "experiment": "experiment"}.get(handler, handler)
    warnings = [] if results.get(required_result) else ["当前任务没有此能力的可核验结果"]
    return metrics, related, evidence, warnings


def execute_skill_plan(plan: dict[str, Any], snapshot: dict[str, Any], blocked_reason: str | None = None) -> dict[str, Any]:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    skill_run_id = f"skillrun_{uuid4().hex[:12]}"
    runtime_mode = getattr(settings, "AGENT_RUNTIME_MODE", "hybrid")
    industrial_result = None
    core_results: list[dict[str, Any]] = []
    state: dict[str, Any] = {}
    core_result_by_skill: dict[str, dict[str, Any]] = {}
    capability_by_skill: dict[str, list[dict[str, Any]]] = {}
    analysis_plan = plan.get("analysis", {}).get("analysis_plan", {})
    task_kind = plan.get("analysis", {}).get("task_understanding", {}).get("task_kind")
    selected_runtime_skills = plan.get("analysis", {}).get("skill_resolution", {}).get("selected_skills", [])
    if runtime_mode != "legacy" and not blocked_reason and analysis_plan.get("selected_capabilities") and "industrial-analysis" in selected_runtime_skills and task_kind not in {"knowledge_explanation", "artifact_request", "conversation"}:
        data = snapshot.get("_dataframe")
        data_path = None
        if data is None:
            try:
                from core.services.pipeline import resolve_artifact
                data_path, _ = resolve_artifact(snapshot.get("run_id"), "standardized_csv")
            except Exception:
                data_path = None
        if data is not None or data_path is not None:
            skill_runtime = plan.get("analysis", {}).get("skill_runtime", {})
            executor = get_executor("industrial-analysis")
            industrial_result = executor.execute(
                "industrial-analysis",
                [item["capability"] for item in analysis_plan.get("selected_capabilities", [])],
                plan.get("analysis", {}).get("task_understanding", {}),
                plan.get("analysis", {}).get("data_context", {}),
                {"data": data, "data_path": data_path},
                {
                    "analysis_plan": analysis_plan,
                    "execution_policy": skill_runtime.get("manifest", {}).get("execution_policy", {}),
                    "evidence_policy": skill_runtime.get("manifest", {}).get("evidence_policy", {}),
                    "output_dir": RUNS_DIR / skill_run_id,
                },
            )
            for decision, result in zip(analysis_plan.get("selected_capabilities", []), industrial_result["capability_executions"]):
                for skill_id in decision.get("selected_skill_ids", []):
                    capability_by_skill.setdefault(skill_id, []).append(result)
    core_plan = plan.get("analysis", {}).get("execution_plan", {}).get("core", {})
    if runtime_mode != "legacy" and plan.get("mode") == "execute" and not blocked_reason:
        parameters = {item.get("name"): item.get("value") for item in plan.get("analysis", {}).get("task_understanding", {}).get("parameters", [])}
        parameters.update(plan.get("parameters", {}))
        if "resample_seconds" in parameters:
            parameters["resample_rule"] = f"{parameters['resample_seconds']}s"
        for node in core_plan.get("steps", []):
            executor = get_executor(node["executor"])
            def blocked_result(reason, missing_artifacts=None, missing_requirements=None, status="blocked"):
                return {"status": status, "skill_id": node["executor"], "executor": node["executor"], "reason": reason,
                        "inputs": [], "outputs": [], "missing_requirements": missing_requirements or [],
                        "missing_artifacts": missing_artifacts or [], "provenance": {}, "capabilities_executed": [],
                        "facts": [], "findings": [], "hypotheses": [], "limitations": [reason],
                        "metrics": {}, "artifacts": [], "evidence": [],
                        "warnings": ["没有生成或回退到 synthetic data。"] if node["executor"] == "optimization" else [],
                        "execution_trace": [], "duration_ms": 0}
            if node.get("readiness_status") == "blocked":
                result = blocked_result(node.get("readiness_reason", "规划阶段前置条件不足"),
                                        node.get("missing_artifacts"), node.get("missing_requirements"))
            elif executor is None:
                result = blocked_result("当前计划无可用独立 Executor。", status="skipped")
            elif any(result.get("status") in {"failed", "blocked", "skipped"} for result in core_results if result.get("skill_id") in node.get("dependencies", [])):
                result = blocked_result("前置 Executor 未成功。")
            else:
                readiness = RuntimeArtifactResolver(snapshot, state).readiness(node.get("requires_artifacts", []))
                if readiness["missing_artifacts"]:
                    result = blocked_result("上游执行完成后仍缺少 artifact：" + "、".join(readiness["missing_artifacts"]),
                                            readiness["missing_artifacts"])
                    core_results.append(result)
                    for selected_skill_id in node["skill_ids"]:
                        core_result_by_skill[selected_skill_id] = result
                    continue
                try:
                    result = executor.execute(node["executor"], node["skill_ids"], plan.get("analysis", {}).get("task_understanding", {}),
                                              plan.get("analysis", {}).get("data_context", {}),
                                              {"snapshot": snapshot, "parameters": parameters,
                                               "optimization_request": (snapshot.get("runtime_state", {}) or {}).get("optimization_contract") or snapshot.get("optimization_contract")},
                                              {"state": state, "results": core_results, "output_dir": RUNS_DIR / skill_run_id,
                                               "execution_id": skill_run_id,
                                               "target_groups": core_plan.get("target_groups", [])})
                except Exception as exc:
                    result = blocked_result(str(exc), status="failed")
                    result["warnings"] = [type(exc).__name__]
                    result["execution_trace"] = [{"step": node["executor"], "status": "failed"}]
            core_results.append(result)
            for selected_skill_id in node["skill_ids"]:
                core_result_by_skill[selected_skill_id] = result
    executions = []
    for step in plan.get("steps", []):
        skill = SKILL_MAP[step["skill_id"]]
        tick = perf_counter()
        is_blocked = bool(blocked_reason) and skill.category != "orchestration"
        if is_blocked:
            executions.append({
                **step, "status": "blocked", "activity": "blocked", "duration_ms": 0,
                "input": {"run_id": snapshot.get("run_id"), "objective": plan["objective"], "parameters": plan["parameters"]},
                "metrics": {}, "artifacts": [], "evidence": [], "warnings": [blocked_reason], "suggested_next_skills": [],
            })
            continue
        status, activity = "success", "read"
        capability_executions = capability_by_skill.get(skill.id, [])
        core_result = core_result_by_skill.get(skill.id)
        if core_result:
            status = core_result["status"]
            activity = "executed" if status in {"success", "partial"} else status
            metrics = core_result.get("metrics", {})
            artifacts = core_result.get("artifacts", [])
            evidence = core_result.get("evidence", [])
            warnings = core_result.get("warnings", []) + core_result.get("limitations", [])
        elif capability_executions:
            activity = "executed"
            metrics = {item["capability_id"]: item["metrics"] for item in capability_executions}
            artifacts = [industrial_result["artifact"]] if industrial_result and industrial_result.get("artifact") else []
            evidence = [entry for item in capability_executions for entry in item["evidence"]]
            warnings = [entry for item in capability_executions for entry in item["warnings"]]
        elif skill.handler == "intent":
            metrics = {"objective": plan["objective"], "mode": plan.get("mode", "analyze")}
            artifacts, evidence, warnings = [], ["user_instruction"], []
        elif skill.handler == "entity":
            metrics, artifacts, evidence, warnings = plan["entities"], [], ["user_instruction"], []
        elif skill.handler == "parameter":
            metrics, artifacts, evidence, warnings = plan["parameters"], [], ["user_instruction"], []
        elif skill.handler in {"matcher", "planner", "supervisor"}:
            metrics = {"selected_skills": plan["selected_count"], "dependency_check": "passed"}
            artifacts, evidence, warnings = [], [plan["plan_id"]], []
        elif skill.handler == "simulation":
            metrics = {"capability": "available", "entry": "/scenario-data/", "format": "CSV"}
            artifacts, evidence, warnings = [], ["frontend:simulation_generator"], []
        else:
            metrics, artifacts, evidence, warnings = _summary(snapshot, skill.handler)
        if skill.handler in {"intent", "entity", "parameter", "matcher", "planner"}:
            activity = "planned"
        if skill.handler == "supervisor" and core_result is None:
            metrics = {"pipeline_status": snapshot.get("status"), "automatic_replanning": False}
            warnings = ["当前为分析模式，未触发执行监督。"]
        checks = {
            "signal_noise_ratio_estimator": bool(snapshot.get("results", {}).get("cleaning", {}).get("snr")),
            "high_snr_dynamic_segment_extractor": bool(snapshot.get("results", {}).get("cleaning", {}).get("snr")),
            "arx_structure_order_selector": bool(snapshot.get("results", {}).get("modeling", {}).get("order_search")),
            "multi_model_benchmark": bool(snapshot.get("results", {}).get("modeling", {}).get("order_search")),
            "model_diagnostics_evaluator": bool(snapshot.get("results", {}).get("modeling", {}).get("diagnostics")),
            "engineering_visualization_builder": bool(core_result),
            "industrial_simulation_generator": bool(core_result),
            "experiment_tracker_comparator": bool(core_result),
            "execution_supervisor_replanner": bool(core_result),
        }
        if core_result is None and activity != "executed" and (not checks.get(skill.id, True) or (warnings and not artifacts and skill.handler not in {"intent", "entity", "parameter", "matcher", "planner"})):
            status, activity = "unavailable", "unavailable"
            warnings = warnings or ["此能力未执行或缺少独立产物，不能标记完成"]
        executions.append({
            **step, "status": status, "activity": activity, "duration_ms": round((perf_counter() - tick) * 1000),
            "execution_scope": "skill_executor" if core_result is not None or activity == "executed" else "plan" if activity == "planned" else "pipeline_evidence_read",
            "input": {"run_id": snapshot.get("run_id"), "objective": plan["objective"], "parameters": plan["parameters"]},
            "metrics": metrics, "artifacts": artifacts, "evidence": evidence, "warnings": warnings,
            "suggested_next_skills": [item.id for item in SKILLS if skill.id in item.depends_on][:3],
        })
    pipeline_run_id = snapshot.get("run_id")
    if not isinstance(pipeline_run_id, (str, int, float, bool, type(None))):
        pipeline_run_id = None
    result_status = "blocked" if blocked_reason or any(item.get("status") == "blocked" for item in core_results) else "failed" if any(item.get("status") == "failed" for item in core_results) else "partial" if any(item.get("status") in {"partial", "unavailable"} for item in core_results) or any(row["status"] == "unavailable" for row in executions) else "completed"
    fallback = plan.get("analysis", {}).get("execution_plan", {}).get("fallback", {})
    payload = {
        "skill_run_id": skill_run_id, "pipeline_run_id": pipeline_run_id, "status": result_status,
        "blocked_reason": blocked_reason,
        "started_at": started, "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "plan": plan, "executions": executions, "skill_execution_result": industrial_result, "core_skill_execution_results": core_results,
        "artifact_registry": [ref.public() if hasattr(ref, "public") else ref for ref in state.get("artifact_refs", {}).values()] if runtime_mode != "legacy" else snapshot.get("artifact_registry", []),
        "summary": {
            "total": len(executions), "success": sum(item.get("status") == "success" for item in core_results) + (1 if industrial_result else 0),
            "blocked": sum(item.get("status") == "blocked" for item in core_results) + sum(item["status"] == "blocked" for item in executions if item["skill_id"] not in core_result_by_skill),
            "failed": sum(item.get("status") == "failed" for item in core_results),
            "warnings": sum(bool(item["warnings"]) for item in executions),
            "read": sum(item["activity"] == "read" for item in executions),
            "planned": sum(item["activity"] == "planned" for item in executions),
            "unavailable": sum(item["status"] == "unavailable" for item in executions),
            "executed": sum(item.get("status") in {"success", "partial"} for item in core_results) + (1 if industrial_result else 0),
            "selected": len(plan.get("direct_skill_ids", [])),
            "skipped": sum(item["activity"] == "skipped" for item in executions),
            "executor_invocations": (1 if industrial_result else 0) + sum(item.get("status") not in {"unavailable"} for item in core_results),
            "capabilities_executed": len((industrial_result or {}).get("capability_executions", [])) + sum(len(item.get("capabilities_executed", [])) for item in core_results),
            "fallback_used": bool(fallback.get("used")),
            "fallback_reason": fallback.get("reason"),
        },
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{skill_run_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return payload


def get_skill_run(skill_run_id: str) -> dict[str, Any] | None:
    path = RUNS_DIR / f"{skill_run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
