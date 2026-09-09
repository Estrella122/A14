from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from django.conf import settings

from .catalog import CATEGORIES, SKILLS, SKILL_MAP


RUNS_DIR = Path(settings.BASE_DIR) / "runtime" / "agent_skill_runs"

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
    equipment = re.search(r"(\d+)\s*号\s*(塔|炉|反应器)", message)
    scenario = "钢厂加热炉" if "加热炉" in message or (equipment and equipment.group(2) == "炉") else "精馏塔" if "塔" in message else None
    return {"equipment_id": f"{equipment.group(1)}号{equipment.group(2)}" if equipment else None, "scenario": scenario}


def _parameters(message: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    rules = (("resample_seconds", r"(\d+)\s*秒"), ("max_lag", r"(?:时滞|max[_ ]?lag)[^\d]{0,5}(\d+)"), ("model_order", r"(?:阶次|order)[^\d]{0,5}(\d+)"))
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
    def visit(skill_id: str):
        if skill_id in resolved or skill_id not in SKILL_MAP:
            return
        for dependency in SKILL_MAP[skill_id].depends_on:
            visit(dependency)
        resolved.add(skill_id)
    for item in selected:
        visit(item)
    return [skill.id for skill in SKILLS if skill.id in resolved]


def plan_skills(message: str, run_id: str | None = None) -> dict[str, Any]:
    text = str(message or "").strip()
    if not text:
        raise ValueError("规划指令不能为空。")
    analysis = _request_analysis(text)
    direct, relevance_scores, candidates = _direct_matches(text, analysis)
    execution_mode = analysis["mode"]
    runtime_skills = {"industrial_intent_parser", "skill_capability_matcher", "workflow_dag_planner", "evidence_audit_reproducer"}
    if execution_mode == "execute":
        runtime_skills.add("execution_supervisor_replanner")
    if execution_mode == "execute":
        ordered = _with_dependencies(direct | runtime_skills)
    else:
        selected = direct | runtime_skills
        ordered = [skill.id for skill in SKILLS if skill.id in selected]
    entities = _entities(text)
    parameters = _parameters(text)
    steps = []
    for index, skill_id in enumerate(ordered, 1):
        skill = SKILL_MAP[skill_id]
        reason = "用户目标直接命中" if skill_id in direct else ("上游依赖自动补齐" if execution_mode == "execute" else "Agent 运行时治理")
        steps.append({"order": index, "skill_id": skill.id, "name": skill.name, "category": skill.category, "reason": reason, "relevance_score": relevance_scores.get(skill_id, 1.0 if skill_id in runtime_skills else 0.68), "status": "ready"})
    return {
        "plan_id": f"plan_{uuid4().hex[:12]}", "run_id": run_id, "objective": text,
        "mode": execution_mode, "analysis": analysis, "entities": entities, "parameters": parameters,
        "constraints": {"local_execution": True, "auditable": True},
        "selected_count": len(steps), "steps": steps, "candidates": candidates,
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
        "selection": {"selected_segments": cleaning.get("selected_segment_count"), "modeling_rows": cleaning.get("modeling_row_count"), "dynamic_score": cleaning.get("dimension_scores", {}).get("dynamic")},
        "lag": {"lags": modeling.get("lags", [])},
        "collinearity": {"input_count": len(modeling.get("input_cols", [])), "selected_count": len(modeling.get("selected_inputs", [])), "details": modeling.get("collinearity", {})},
        "modeling": {"output": modeling.get("output_col"), "selected_inputs": modeling.get("selected_inputs", []), **test},
        "optimization": {"best_round": optimization.get("best_round"), "best_score": optimization.get("best_score"), "best_parameters": optimization.get("best_parameters", {})},
        "review": {"passed": review.get("passed"), "conclusion": review.get("conclusion"), "warnings": review.get("warnings", [])},
        "report": {"title": results.get("report", {}).get("title"), "available": "analysis_report_md" in artifacts},
        "artifact": {"artifact_keys": list(artifacts)},
        "audit": {"run_id": snapshot.get("run_id"), "stage_count": len(snapshot.get("stages", [])), "artifact_count": len(artifacts)},
        "experiment": {"run_id": snapshot.get("run_id"), **test},
        "asset": {"dataset": snapshot.get("original_name"), "run_id": snapshot.get("run_id")},
    }
    metrics = metrics_by_handler.get(handler, {"run_id": snapshot.get("run_id"), "evidence_available": bool(results)})
    related = [key for key in artifacts if handler.split("_")[0] in key]
    evidence = [f"pipeline:{snapshot.get('run_id')}", f"results:{handler}"]
    warnings = [] if results else ["当前任务尚无可用阶段结果"]
    return metrics, related, evidence, warnings


def execute_skill_plan(plan: dict[str, Any], snapshot: dict[str, Any], blocked_reason: str | None = None) -> dict[str, Any]:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
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
        if skill.handler == "intent":
            metrics = {"objective": plan["objective"], "mode": "execute" if any(word in plan["objective"] for word in ("执行", "运行", "生成")) else "analyze"}
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
        executions.append({
            **step, "status": "success", "activity": "planned" if blocked_reason else "executed" if plan.get("mode") == "execute" else "read", "duration_ms": max(1, round((perf_counter() - tick) * 1000)),
            "input": {"run_id": snapshot.get("run_id"), "objective": plan["objective"], "parameters": plan["parameters"]},
            "metrics": metrics, "artifacts": artifacts, "evidence": evidence, "warnings": warnings,
            "suggested_next_skills": [item.id for item in SKILLS if skill.id in item.depends_on][:3],
        })
    skill_run_id = f"skillrun_{uuid4().hex[:12]}"
    payload = {
        "skill_run_id": skill_run_id, "pipeline_run_id": snapshot.get("run_id"), "status": "blocked" if blocked_reason else "completed",
        "blocked_reason": blocked_reason,
        "started_at": started, "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "plan": plan, "executions": executions,
        "summary": {
            "total": len(executions), "success": sum(item["status"] == "success" for item in executions),
            "blocked": sum(item["status"] == "blocked" for item in executions), "failed": 0,
            "warnings": sum(bool(item["warnings"]) for item in executions),
        },
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{skill_run_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def get_skill_run(skill_run_id: str) -> dict[str, Any] | None:
    path = RUNS_DIR / f"{skill_run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
