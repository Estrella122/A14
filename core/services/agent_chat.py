from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from core.skills import execute_skill_plan, plan_skills

from .expert_qa import answer_expert_question
from .evidence_values import number, display, final_result_view
from .pipeline import PipelineError, get_run, rerun_pipeline
from .llm_gateway import LLMGatewayError, generate_grounded_answer
from core.mcp.client import MCPInvocationError, invoke_and_wait as invoke_mcp_and_wait
from core.skills.catalog import resolve_scene_family
from django.conf import settings
from core.skills.response_renderer import DeterministicResponseRenderer


INTENTS = [
    ("diagnosis", ("最大的问题", "主要问题", "有什么问题", "哪里不好", "问题是什么", "薄弱", "短板", "瓶颈")),
    ("standardization", ("字段", "映射", "标准", "单位", "场景", "变量角色")),
    ("cleaning", ("清洗", "缺失", "异常", "质量", "规整", "插值", "采样周期", "采样频率", "混叠")),
    ("selection", ("动态段", "动态数据", "高信噪比", "信噪比", "筛选", "优选", "稳态", "持续激励", "可辨识")),
    ("lag", ("时滞", "延迟", "滞后", "补偿", "互相关", "因果")),
    ("collinearity", ("共线", "vif", "冗余", "相关变量", "降维")),
    ("modeling", ("模型", "辨识", "arx", "拟合", "r2", "r²", "rmse", "mae", "预测", "残差", "白噪声", "稳定性", "极点", "伯德", "奈奎斯特", "频响", "过拟合", "泛化", "数据泄漏", "阶次", "aic", "bic")),
    ("optimization", ("寻优", "优化", "候选", "最佳策略", "最优策略", "最优轮次", "轮次", "几轮", "三轮", "八轮", "闭环", "哪一轮", "这一轮", "轮最好", "目标函数", "收敛", "停止条件", "局部最优")),
    ("review", ("评审", "通过", "报告", "交付", "缺陷", "风险", "上线", "投运", "联锁", "审计", "复现", "迁移", "模型漂移")),
]
INTENT_LABELS = {
    "conversation": "自然对话",
    "capability": "能力说明",
    "clarification": "需要确认",
    "diagnosis": "问题诊断",
    "overview": "任务总览",
    "standardization": "字段标准化",
    "cleaning": "数据清洗",
    "selection": "动态优选",
    "lag": "时滞分析",
    "collinearity": "共线性处理",
    "modeling": "系统辨识",
    "optimization": "闭环寻优",
    "review": "Agent评审",
}

TASK_INTENT_TO_CHAT_INTENT = {
    "anomaly_detection": "diagnosis", "process_stability": "diagnosis", "trend_analysis": "cleaning",
    "time_window_analysis": "selection", "relationship_analysis": "collinearity",
    "missing_data_analysis": "cleaning", "energy_analysis": "overview", "quality_analysis": "overview",
    "equipment_health": "diagnosis", "bottleneck_analysis": "diagnosis", "root_cause_analysis": "diagnosis",
    "data_profiling": "overview",
}


def _explicit_execution_authorized(message: str) -> bool:
    """Require an action-shaped request before rerunning Pipeline through MCP.

    Manifest Skills may inspect existing artifacts for a question, but a matched
    capability noun alone must not authorize a new pipeline run.
    """
    normalized = str(message or "").strip().lower()
    return bool(re.search(
        r"^(?:(?:请|麻烦|劳驾|帮我|帮忙|给我|替我|我需要|我想|现在|立即|开始|继续|先|再|把|将|对)\s*)*"
        r"(?:重新执行|重新运行|重跑|运行一遍|执行|运行|训练|清洗|生成|提取|找出|筛选|计算|估计|优化|寻优|建立|建模|剔除|补偿|冻结|选择|选取)",
        normalized,
    ) or re.search(
        r"^(?:请|麻烦|劳驾|帮我|帮忙|给我|替我|我需要|我想).{0,50}"
        r"(?:重新执行|重新运行|重跑|执行|运行|训练|清洗|生成|提取|找出|筛选|计算|估计|优化|寻优|建立|建模|剔除|补偿|冻结|选择|选取)",
        normalized,
    ))


def _intent_from_task_spec(task_spec: dict[str, Any]) -> tuple[str, float, list[str], list[str]]:
    matched = task_spec.get("response_intents") or [task_spec.get("response_intent", "overview")]
    key = task_spec.get("response_intent", "overview")
    return key, float(task_spec.get("confidence", 0.7)), [], matched or [key]


def _detect_intent(message: str, previous_intent: str | None = None, previous_intents: list[str] | None = None) -> tuple[str, float, list[str], list[str]]:
    normalized = message.lower()
    if any(word in normalized for word in ("你好", "您好", "在吗", "嗨", "hello", "hi")):
        return "conversation", 0.99, [], ["conversation"]
    if any(word in normalized for word in ("你是谁", "你能做什么", "怎么用", "有什么功能", "能干什么")):
        return "capability", 0.98, [], ["capability"]
    ranked: list[tuple[int, int, str, list[str]]] = []
    for key, keywords in INTENTS:
        hits = [word for word in keywords if word.lower() in normalized]
        first = min((normalized.find(word.lower()) for word in hits), default=len(normalized))
        ranked.append((len(hits), -first, key, hits))
    ranked.sort(reverse=True)
    count, _, key, hits = ranked[0]
    matched = [item[2] for item in ranked if item[0] > 0]
    if count == 0:
        is_follow_up = any(word in normalized for word in ("这个", "它", "那", "为什么", "具体", "然后", "可靠吗", "呢"))
        previous_domains = [item for item in (previous_intents or []) if item in INTENT_LABELS and item not in {"overview", "conversation", "capability", "clarification"}]
        if previous_intent in INTENT_LABELS and previous_intent not in {"overview", "conversation", "capability", "clarification"} and is_follow_up:
            return previous_intent, 0.88, [], [previous_intent]
        if is_follow_up and len(previous_domains) > 1:
            return "clarification", 0.96, [], previous_domains
        return "overview", 0.68, [], ["overview"]
    if len(matched) >= 2 and any(word in normalized for word in ("总结", "整体", "全部", "分别", "以及", "和报告", "还有")):
        return "overview", min(0.86 + len(matched) * 0.025, 0.98), hits, matched
    return key, min(0.82 + count * 0.05, 0.98), hits, matched


def _requires_execution(message: str) -> bool:
    return any(word in message.lower() for word in ("重新执行", "重新运行", "重跑", "开始执行", "立即执行", "运行一遍"))


def _scenario_family(name: str | None) -> str | None:
    return resolve_scene_family(name)


def _compound_result(snapshot: dict[str, Any], degraded: bool) -> tuple[str, list[dict[str, Any]], list[str]]:
    result = snapshot.get("results", {})
    cleaning = result.get("cleaning", {})
    modeling = result.get("modeling", {})
    optimization = result.get("optimization", {})
    original = modeling.get("input_cols", [])
    selected = modeling.get("selected_inputs", [])
    removed = modeling.get("collinearity", {}).get("recommendations", {}).get("drop", [])
    validation = modeling.get("metrics", {}).get("validation", {})
    test = modeling.get("metrics", {}).get("test", {})
    diagnostic = modeling.get("diagnostics", {}).get("test", {})
    snr = cleaning.get("snr", {})
    config = modeling.get("config", {})
    review = result.get("review", {})
    def fmt(value):
        return display(value, 4)
    quality_note = ("已估计窗口SNR（白噪声假设下的代理值，非仪表标定结果）。" if snr.get("status") == "estimated"
                    else "当前没有可核验的SNR估计，不能确认高信噪比。")
    answer = (
        "已完成本地流水线：动态段提取 → 因果时滞 → 共线性诊断 → 结构比较 → 共同验证集寻优 → 独立测试。"
        f"训练区间内 {cleaning.get('selected_segment_count', 0)} 个窗口达标（窗口重叠，不等于独立激励次数），"
        f"选中候选训练数据 {modeling.get('training_rows', cleaning.get('modeling_row_count', '—'))} 行。{quality_note}"
        + ("没有达标窗口，本次仅使用候选窗口降级建模。" if degraded else "") +
        f"共线性诊断从 {len(original)} 个输入保留 {len(selected)} 个；剔除：{'、'.join(removed) or '无，无需强行删除'}。"
        f"本次候选范围内第 {optimization.get('best_round', '—')} 轮验证得分最高，"
        f"top_k={optimization.get('best_parameters', {}).get('top_k', '—')}、max_lag请求上限={optimization.get('best_parameters', {}).get('max_lag', '—')}；"
        f"实际模型为 {config.get('family', '未保存')}，阶次 {config.get('output_order', '—')}，"
        f"实际使用外部输入 {len(modeling.get('fitted_inputs', []))} 个。"
        f"验证集R²={fmt(validation.get('r2'))}；独立测试单步R²={fmt(test.get('r2'))}、RMSE={fmt(test.get('rmse'))}、MAE={fmt(test.get('mae'))}。"
        f"相较持续值基线RMSE改善 {fmt(diagnostic.get('rmse_improvement_over_persistence_pct'))}%。"
        f"评审：{review.get('conclusion', '缺少评审证据')}。"
        + ("原因：" + "；".join(review['blockers']) + "。" if review.get('blockers') else "")
    )
    cards = [
        {"label": "SNR", "value": "代理估计，未标定" if snr else "证据不足"},
        {"label": "训练数据", "value": f"{modeling.get('training_rows', cleaning.get('modeling_row_count', '—'))} 行"},
        {"label": "共线保留", "value": f"{len(selected)}/{len(original)}"},
        {"label": "验证选中轮次", "value": optimization.get("best_round", "—")},
        {"label": "独立测试 R²", "value": fmt(test.get('r2'))},
        {"label": "评审", "value": "候选通过" if review.get('passed') else "待复核"},
    ]
    return answer, cards, ["查看SNR估计依据", "对比单步预测、10步预测和自由仿真", "当前结果还缺哪些验证证据"]


def _deliverables(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    labels = {
        "segments_csv": "动态段CSV", "modeling_csv": "选中候选训练数据CSV", "delays_csv": "时滞结果CSV",
        "snr_csv": "SNR估计明细", "split_json": "时间分区清单", "test_predictions_csv": "独立测试预测", "metrics_json": "分区模型指标", "diagnostics_json": "基线与多步诊断", "order_search_json": "结构比较", "audit_json": "复现清单", "optimization_json": "寻优记录", "analysis_report_md": "分析报告", "analysis_report_html": "自包含图文报告", "report_package_zip": "报告与图片包",
    }
    from .delivery_report import artifact_manifest
    artifacts = artifact_manifest(snapshot) if snapshot.get('run_id') else {}
    return [{"key": key, "label": label} for key, label in labels.items() if artifacts.get(key, {}).get('state') == 'ready']


def _number(message: str, patterns: tuple[str, ...], default: int) -> int:
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return default


def _stage_plan(snapshot: dict[str, Any], focus: str, executed: bool) -> list[dict[str, Any]]:
    result = snapshot.get("results", {})
    standard = result.get("standardization", {})
    cleaning = result.get("cleaning", {})
    modeling = result.get("modeling", {})
    optimization = result.get("optimization", {})
    review = result.get("review", {})
    report = result.get("report", {})
    nodes = [
        {"key": "intent", "name": "意图解析", "tool": "intent_router", "output": f"聚焦 {focus}", "status": "completed"},
        {"key": "standardization", "name": "字段标准化", "tool": "task2_standardizer", "output": standard.get("scenario", {}).get("scenario_name", "等待数据"), "status": "completed" if standard else "pending"},
        {"key": "cleaning", "name": "数据清洗", "tool": "cleaning_agent", "output": f"质量 {cleaning.get('overall_score', '—')}", "status": "completed" if cleaning else "pending"},
        {"key": "selection", "name": "动态优选", "tool": "dynamic_segmenter", "output": f"建模 {cleaning.get('modeling_row_count', '—')} 行", "status": "completed" if cleaning else "pending"},
        {"key": "modeling", "name": "系统辨识", "tool": "arx_identifier", "output": f"测试 R² {_metric(modeling.get('metrics', {}).get('test', {}).get('r2'))}", "status": "completed" if modeling else "pending"},
        {"key": "optimization", "name": "闭环寻优", "tool": "real_data_optimizer", "output": f"第 {optimization.get('best_round', '—')} 轮最优 · 得分 {optimization.get('best_score', '—')}", "status": "completed" if optimization else "pending"},
        {"key": "review", "name": "Agent评审", "tool": "evidence_reviewer", "output": review.get("conclusion", "等待评审"), "status": "completed" if review else "pending"},
        {"key": "report", "name": "分析报告", "tool": "report_agent", "output": report.get("title", "等待生成"), "status": "completed" if report else "pending"},
    ]
    if not executed and focus != "overview":
        for node in nodes:
            if node["key"] not in {"intent", focus} and not (focus in {"lag", "collinearity"} and node["key"] == "modeling"):
                node["status"] = "context"
    return nodes


def _metric(value):
    return f"{float(value):.3f}" if value is not None else "未计算"


def _overview(snapshot: dict[str, Any]) -> str:
    result = snapshot.get("results", {})
    standard = result.get("standardization", {})
    cleaning = result.get("cleaning", {})
    modeling = result.get("modeling", {})
    optimization = result.get("optimization", {})
    review = result.get("review", {})
    test = modeling.get("metrics", {}).get("test", {})
    return (
        f"当前任务 {snapshot['run_id']} 已识别为{standard.get('scenario', {}).get('scenario_name', '未知场景')}。"
        f"字段决策为 {standard.get('data_decision', {}).get('status', '—')}，数据质量评分 {cleaning.get('overall_score', '—')}，"
        f"建模数据 {cleaning.get('modeling_row_count', '—')} 行，测试集 R² {_metric(test.get('r2'))}、RMSE {_metric(test.get('rmse'))}。"
        f"闭环寻优选择第 {optimization.get('best_round', '—')} 轮策略，综合得分 {optimization.get('best_score', '—')}。"
        f"Agent评审结论：{review.get('conclusion', '尚未评审')}。"
    )


def _answer(snapshot: dict[str, Any], intent: str, message: str = "", matched_intents: list[str] | None = None) -> tuple[str, list[dict[str, Any]], list[str]]:
    result = snapshot.get("results", {})
    standard = result.get("standardization", {})
    cleaning = result.get("cleaning", {})
    modeling = result.get("modeling", {})
    optimization = result.get("optimization", {})
    review = result.get("review", {})
    mapping = standard.get("mapping", {})
    test = modeling.get("metrics", {}).get("test", {})
    cards: list[dict[str, Any]] = []
    suggestions: list[str] = []
    matched_intents = matched_intents or [intent]

    if intent == "conversation":
        return (
            f"你好，我在。当前连接的是任务 {snapshot['run_id']}。你可以直接问我某个字段为什么这样映射、数据质量哪里有问题、模型是否可靠，或者让我重新跑一遍；我会引用这次任务的真实结果，不需要使用固定指令。",
            [{"label": "当前任务", "value": snapshot["run_id"]}, {"label": "运行状态", "value": snapshot.get("status", "—")}],
            ["这批数据最大的问题是什么", "为什么选择当前寻优策略", "这个模型能直接使用吗"],
        )
    if intent == "capability":
        return (
            "我负责把整条工业时序建模流程串起来：读取CSV、判断场景、统一字段和单位、清洗异常与缺失、筛选动态段、分析时滞和共线性、训练ARX模型、比较候选策略，最后给出评审结论和可下载报告。你也可以追问任何一步的依据。",
            [{"label": "真实阶段", "value": len(snapshot.get("stages", []))}, {"label": "当前任务", "value": snapshot["run_id"]}],
            ["先总结这批数据", "字段统一结果怎么样", "模型为什么得到这个分数"],
        )
    if intent == "clarification":
        labels = [INTENT_LABELS[item] for item in matched_intents if item in INTENT_LABELS]
        return (
            f"你上一句同时提到了{'、'.join(labels)}。你说的“这样”具体是指哪一项？我不想替你猜错。",
            [{"label": "待确认范围", "value": len(labels)}, {"label": "当前任务", "value": snapshot["run_id"]}],
            [f"为什么{label}是这个结果" for label in labels[:3]],
        )
    if intent == "diagnosis":
        missing = cleaning.get("missing_rate", {})
        worst_field = max(missing, key=missing.get) if missing else "无"
        worst_rate = float(missing.get(worst_field, 0))
        r2 = number(test.get("r2"))
        segment_count = int(cleaning.get("selected_segment_count") or 0)
        strict_segment_count = int(cleaning.get("strict_selected_segment_count", segment_count) or 0)
        relaxed = bool(cleaning.get("relaxed_acceptance"))
        findings = []
        if worst_rate >= 0.2:
            findings.append((worst_rate, f"重采样后 `{worst_field}` 的空档率达到 {worst_rate:.1%}"))
        if cleaning.get("selection_metrics") and segment_count == 0:
            findings.append((0.9, "没有窗口达到严格优质动态段阈值，当前建模数据来自候选窗口兜底"))
        elif relaxed:
            findings.append((0.6, f"严格优质段为 {strict_segment_count} 个，已按小数据模式接纳 {segment_count} 个可用候选段"))
        if r2 is not None and r2 < 0.5:
            findings.append((0.8, f"最优模型测试集 R² 只有 {r2:.3f}，解释能力仍偏弱"))
        if number(cleaning.get("overall_score")) is not None and number(cleaning["overall_score"]) < 70:
            findings.append((0.7, f"总体数据质量评分为 {cleaning.get('overall_score')}，尚未达到70分"))
        findings.sort(reverse=True)
        diagnosis = "；".join(item[1] for item in findings[:3]) or ("当前没有可核验的模型评价指标，尚不能评价模型；请先检查输入与执行状态" if r2 is None else "当前自动规则未发现上述问题，仍需独立工况验证")
        return (
            f"这批数据最值得先处理的问题是：{diagnosis}。仅对当前已保存的证据作上述判断；未计算或缺失的阶段不能视为完成。",
            [{"label": "质量评分", "value": cleaning.get("overall_score")}, {"label": "接纳动态段", "value": segment_count}, {"label": "测试 R²", "value": display(r2)}],
            ["为什么严格动态段为0", f"{worst_field}为什么缺失这么高", "应该先改哪个参数"],
        )

    if intent == "overview" and len(matched_intents) >= 2:
        answer = (
            f"我按你提到的内容一起回答。字段方面，当前场景是{standard.get('scenario', {}).get('scenario_name', '未知场景')}，"
            f"必需字段覆盖率 {float(mapping.get('required_coverage') or 0):.1%}；数据方面，质量评分 {cleaning.get('overall_score', '—')}，"
            f"规整后 {cleaning.get('cleaned_row_count', '—')} 行、建模使用 {cleaning.get('modeling_row_count', '—')} 行；"
            f"模型方面，测试集 R²={_metric(test.get('r2'))}、RMSE={_metric(test.get('rmse'))}；"
            f"寻优方面，第 {optimization.get('best_round', '—')} 轮得分最高（{optimization.get('best_score', '—')}）；"
            f"最终评审为“{review.get('conclusion', '尚未评审')}”，报告已经随任务产物生成。"
        )
        cards = [
            {"label": "字段覆盖", "value": f"{float(mapping.get('required_coverage') or 0):.1%}"},
            {"label": "质量评分", "value": cleaning.get("overall_score")},
            {"label": "测试 R²", "value": f"{_metric(test.get('r2'))}"},
            {"label": "评审", "value": "通过" if review.get("passed") else "待复核"},
        ]
        return answer, cards, ["这批数据最大的问题是什么", "为什么选择当前寻优策略", "报告里有哪些内容"]

    if intent == "standardization":
        matched = sum(item.get("status") == "matched" for item in mapping.get("mappings", []))
        if re.search(r"(?:什么|哪个|哪种).{0,8}场景|场景.{0,8}(?:是什么|是哪个|是哪种)", message):
            scenario = standard.get("scenario", {})
            scene_name = scenario.get("scenario_name") or scenario.get("display_name") or scenario.get("scenario_id") or "未知场景"
            status = scenario.get("status") or standard.get("runtime_trace", {}).get("scene_status") or "已识别"
            confidence = scenario.get("confidence")
            confidence_text = f"，置信度 {float(confidence):.1%}" if isinstance(confidence, (int, float)) else ""
            return (
                f"当前上传数据识别为【{scene_name}】，场景状态为 {status}{confidence_text}。"
                f"这是本次数据的自动识别结果，与 Web 顶部的项目预设场景独立。",
                [{"label": "数据场景", "value": scene_name}, {"label": "识别状态", "value": status}, {"label": "字段匹配", "value": f"{matched}/{len(mapping.get('mappings', []))}"}],
                ["这个场景的判定依据是什么", "查看字段统一结果", "分析当前数据质量"],
            )
        answer = (
            f"2号Agent将当前数据识别为{standard.get('scenario', {}).get('scenario_name', '未知场景')}，"
            f"共自动匹配 {matched}/{len(mapping.get('mappings', []))} 个字段，必需字段覆盖率 {float(mapping.get('required_coverage') or 0):.1%}。"
            f"当前数据决策为 {standard.get('data_decision', {}).get('status', '—')}，缺失必需字段："
            f"{'、'.join(mapping.get('missing_required', [])) or '无'}。"
        )
        cards = [{"label": "字段匹配", "value": f"{matched}/{len(mapping.get('mappings', []))}"}, {"label": "必需字段覆盖", "value": f"{float(mapping.get('required_coverage') or 0):.1%}"}, {"label": "单位风险", "value": mapping.get("unit_risk_count", 0)}]
        suggestions = ["解释未映射字段", "当前数据属于哪个工业场景", "重新执行字段统一"]
    elif intent == "cleaning":
        missing = cleaning.get("missing_rate", {})
        worst = max(missing, key=missing.get) if missing else "无"
        resample_warning = (
            "该缺失率主要由目标采样周期明显细于原始采样周期造成，建议改用更接近原始周期的重采样参数。"
            if float(missing.get(worst, 0)) >= 0.5 else "当前重采样没有造成大比例空档。"
        )
        answer = (
            f"清洗结果来自本次真实任务：总体质量评分 {cleaning.get('overall_score', '—')}，规整后 {cleaning.get('cleaned_row_count', '—')} 行。"
            f"缺失率最高字段为 {worst}（{float(missing.get(worst, 0)):.2%}），建模数据保留 {cleaning.get('modeling_row_count', '—')} 行。"
            f"缺失值使用时间插值，异常值由物理边界、阶跃阈值和局部中位数联合检测。{resample_warning}"
        )
        cards = [{"label": "质量评分", "value": cleaning.get("overall_score")}, {"label": "规整后行数", "value": cleaning.get("cleaned_row_count")}, {"label": "建模行数", "value": cleaning.get("modeling_row_count")}]
        suggestions = ["哪些字段缺失最多", "为什么使用时间插值", "按5秒重新执行"]
    elif intent == "selection":
        count = cleaning.get("selected_segment_count", 0)
        strict_count = cleaning.get("strict_selected_segment_count", count)
        relaxed = bool(cleaning.get("relaxed_acceptance"))
        answer = (
            f"动态优选采用{snapshot.get('policy_receipt', {}).get('effective_parameters', {}).get('selection', {}).get('window_samples', '未记录')}点滑动窗口，从输入变化、输出响应、完整性、异常率和平滑度五个角度评分。"
            f"严格优质段为 {strict_count} 个，当前接纳动态段为 {count} 个，用于辨识的数据为 {cleaning.get('modeling_row_count', '—')} 行。"
            + ("当前启用小样本自适应分层筛选，工程可用段已进入后续辨识与寻优，严格段数量仍保留用于结果分级。" if relaxed else "优质窗口已直接进入系统辨识。")
        )
        cards = [{"label": "接纳动态段", "value": count}, {"label": "严格优质段", "value": strict_count}, {"label": "建模数据", "value": cleaning.get("modeling_row_count")}, {"label": "动态质量", "value": cleaning.get("dimension_scores", {}).get("dynamic")}]
        suggestions = ["为什么优质动态段为0", "查看动态段筛选逻辑", "重新执行动态优选"]
    elif intent == "lag":
        lags = modeling.get("lags", [])
        strongest = max(lags, key=lambda item: abs(float(item.get("correlation") or 0)), default={})
        answer = (
            f"系统对 {len(lags)} 个输入完成互相关时滞估计。相关性最强的是 {strongest.get('input', '—')} → {strongest.get('output', '—')}，"
            f"时滞 {strongest.get('delay_samples', '—')} 个采样点，相关系数 {float(strongest.get('correlation') or 0):.3f}。"
            "正时滞表示输入需要前移补偿，负时滞表示当前窗口下输出领先，需要结合工艺机理复核。"
        )
        cards = [{"label": "分析变量", "value": len(lags)}, {"label": "最强时滞", "value": strongest.get("delay_samples", "—")}, {"label": "相关系数", "value": f"{float(strongest.get('correlation') or 0):.3f}"}]
        suggestions = ["解释负时滞的含义", "哪个变量相关性最强", "将时滞范围改为60并重新执行"]
    elif intent == "collinearity":
        original = modeling.get("input_cols", [])
        selected = modeling.get("selected_inputs", [])
        removed = [item for item in original if f"{item}_aligned" not in selected and item not in selected]
        answer = (
            f"共线性处理前有 {len(original)} 个候选输入，处理后保留 {len(selected)} 个。"
            f"被剔除或合并的变量包括：{'、'.join(removed) or '无'}。筛选依据是相关系数阈值和VIF，目的是降低参数方差，而不是单纯追求变量更少。"
        )
        cards = [{"label": "原始输入", "value": len(original)}, {"label": "保留输入", "value": len(selected)}, {"label": "处理数量", "value": max(len(original) - len(selected), 0)}]
        suggestions = ["为什么剔除高共线变量", "列出最终保留变量", "重新执行共线性分析"]
    elif intent == "modeling":
        answer = (
            f"当前{modeling.get('config', {}).get('family', '未记录模型族')}模型输出为 {modeling.get('output_col', '—')}，输入 {len(modeling.get('selected_inputs', []))} 个。"
            f"测试集 R²={_metric(test.get('r2'))}，RMSE={_metric(test.get('rmse'))}，MAE={_metric(test.get('mae'))}。"
            + ("当前解释能力偏弱，建议增加真实动态工况并重新筛选，而不是仅继续调参。" if number(test.get("r2")) is not None and number(test.get("r2")) < 0.5 else "当前模型具备初步解释能力，但仍应使用独立工况做外部验证。" if number(test.get("r2")) is not None else "缺少有效测试指标，不能评价模型能力。")
        )
        cards = [{"label": "测试 R²", "value": f"{_metric(test.get('r2'))}"}, {"label": "RMSE", "value": f"{_metric(test.get('rmse'))}"}, {"label": "MAE", "value": f"{_metric(test.get('mae'))}"}]
        suggestions = ["这个模型是否可靠", "为什么R²不高", "重新运行模型"]
    elif intent == "optimization":
        from .optimization_state import readable_stop
        stopped = readable_stop(snapshot)
        if stopped:
            return stopped, [], ["查看候选原因", "查看当前约束"]
        rounds = [item for item in optimization.get("iterations", []) if item.get("status") == "completed"]
        if not rounds:
            return "当前任务未保存已完成的寻优候选，无法判断是否改善；需要对应搜索的候选、验证指标及停止记录。本次未启动新搜索。", [], ["查看当前运行证据"]
        best = optimization.get("best_metrics", {})
        params = optimization.get("best_parameters", {})
        best_round = optimization.get("best_round")
        runner_up = sorted(rounds, key=lambda item: float(item.get("score") or -1), reverse=True)[1:2]
        comparison = f"，比次优策略高 {float(optimization.get('best_score') or 0) - float(runner_up[0].get('score') or 0):.3f} 分" if runner_up else ""
        answer = (
            f"闭环寻优真实执行了 {len(rounds)} 组候选策略，并按R²、误差和数据覆盖率综合评分。"
            f"{optimization.get('search_strategy', '')}。"
            f"第 {best_round or '—'} 轮“{optimization.get('best_label', '—')}”最优{comparison}，"
            f"top_k={params.get('top_k', '—')}、max_lag={params.get('max_lag', '—')}，综合得分 {optimization.get('best_score', '—')}。"
            f"胜者验证集 R²={_metric(best.get('r2'))}、RMSE={_metric(best.get('rmse'))}，数据覆盖率 {float(best.get('coverage') or 0):.1%}。"
        )
        if optimization.get('selection_warnings'):
            answer += '最佳模型及预测结果已保留。质量提示：' + '；'.join(optimization['selection_warnings']) + '。是否适合生产使用以工程评审为准。'
        cards = [{"label": "候选轮次", "value": len(rounds)}, {"label": "最优轮次", "value": optimization.get("best_round")}, {"label": "综合得分", "value": optimization.get("best_score")}]
        suggestions = ["为什么这一轮最好", "最优模型是否可靠", "以稳健性优先重新执行闭环寻优"]
    elif intent == "review":
        answer = (
            f"当前评审结论为“{review.get('conclusion', '尚未评审')}”。"
            f"阻断项：{'、'.join(review.get('blockers', [])) or '无'}；警告：{'、'.join(review.get('warnings', [])) or '无'}。"
            "这里的通过仅表示满足当前本地准入规则，不等同于已经达到工厂上线标准。"
        )
        cards = [{"label": "评审状态", "value": "通过" if review.get("passed") else "未通过"}, {"label": "阻断项", "value": len(review.get("blockers", []))}, {"label": "警告", "value": len(review.get("warnings", []))}]
        suggestions = ["当前还有哪些风险", "生成交付结论", "模型能否直接上线"]
    else:
        answer = _overview(snapshot)
        cards = [{"label": "质量评分", "value": cleaning.get("overall_score")}, {"label": "测试 R²", "value": f"{_metric(test.get('r2'))}"}, {"label": "评审", "value": "通过" if review.get("passed") else "待复核"}]
        suggestions = ["解释字段统一结果", "分析数据质量", "这个模型是否可靠"]
    return answer, cards, suggestions


def chat(message: str, run_id: str | None = None, previous_intent: str | None = None,
         previous_intents: list[str] | None = None, *, skill_run_id: str | None = None,
         event_sink=None, llm_config: dict[str, Any] | None = None, parameters: dict | None = None) -> dict[str, Any]:
    message = str(message or "").strip()
    if not message:
        raise ValueError("聊天内容不能为空。")
    if len(message) > 2000:
        raise ValueError("单条指令不能超过2000字。")
    from core.skills.task_understanding import understand_task
    from .task_admission import capability_availability, basic_data_profile
    from .algorithm_policy import snapshot_policy
    task = understand_task(message)
    snapshot = get_run(run_id) if run_id else None
    if run_id and not snapshot:
        raise PipelineError("指定运行不存在，不能使用其他运行代替。")
    snapshot = final_result_view(snapshot or {"run_id": None, "results": {}, "artifacts": {}})
    from .optimization_state import readable_stop
    stopped = readable_stop(snapshot)
    if stopped and re.search(r'为什么.*(卡|停|失败)|继续分析|结果怎么样|停止原因|失败原因|候选.*原因', message) and not re.search(r'重试|重新(执行|运行|训练|寻优)|再跑', message):
        # Reading a terminal result never schedules another numerical job.
        response = {'answer': stopped, 'run_id': snapshot.get('run_id'), 'snapshot': snapshot,
                    'executed': False, 'blocked': False, 'execution_scope': 'evidence_only',
                    'execution_mode': 'analysis', 'needs_clarification': False, 'expert_topic': 'optimization',
                    'skill_run_id': skill_run_id, 'pipeline_status': snapshot.get('status'),
                    'cards': [], 'logs': [], 'skill_executions': [], 'suggestions': ['查看候选原因', '查看当前约束'],
                    'intent': {'key': 'optimization', 'matched': ['optimization']}}
        return _finish_answer(message, snapshot, response, {'provider': 'evidence'}, event_sink)
    from .llm_gateway import propose_task_spec
    task, understanding_audit = propose_task_spec(message, snapshot, llm_config, {'previous_task_spec': {'response_intent': previous_intent, 'response_intents': previous_intents or ([previous_intent] if previous_intent else [])}})
    understanding_audit.pop('final_task_spec', None)
    task['constraints']['understanding_audit'] = understanding_audit
    if event_sink:
        event_sink('task_understanding_validated', stage='task_understanding', status='completed', message='已校验任务理解与执行边界', metadata=understanding_audit)
    knowledge_only = task.get("task_kind") == "knowledge_explanation"
    basic = bool(set(task.get("semantic_intents", [])) & {"data_profiling", "missing_data_analysis"}) and task.get("execution_mode") != "execute"
    capability_query = bool(re.search(r"还能做什么|可以做什么|可做哪些|能做哪些", message))
    availability = capability_availability(snapshot, "basic_data_exploration" if basic else "knowledge")
    if knowledge_only or basic or capability_query or not snapshot.get("run_id"):
        profile = None
        expert = answer_expert_question(message, snapshot, answer_intent=task.get("answer_intent"))
        answer = expert["answer"] if expert else "以下为方法解释；是否适用于当前数据，仍需相应运行证据。" if knowledge_only else "当前没有对应的运行证据；可以解释方法与缺口，不能编造当前指标。"
        if basic and "basic_data_exploration" in availability["available_tasks"]:
            profile = basic_data_profile(snapshot)
            ranked = sorted(profile['fields'], key=lambda row: -(row['missing_rate'] or 0))
            answer = f"原始数据共{profile['row_count']}行、{profile['column_count']}列，重复行{profile['duplicate_rows']}。"
            answer += "缺失统计：" + "；".join(f"{row['raw_name']}={row['missing_rate']:.2%}" for row in ranked[:12]) + "。"
            answer += "本次仅做原始数据统计，未填补数据、未训练；字段的物理身份与单位仍需复核。"
            cleaning_logs = snapshot.get("results", {}).get("cleaning", {}).get("logs", [])
            if cleaning_logs:
                target = snapshot.get("results", {}).get("standardization", {}).get("scenario", {}).get("primary_output")
                relevant_logs = [row for row in cleaning_logs if target and target in str(row)]
                relevant_logs += [row for row in cleaning_logs if row not in relevant_logs]
                answer += "已有清洗记录：" + "；".join(str(row) for row in relevant_logs[:6])
            elif snapshot.get("results", {}).get("cleaning"):
                answer += "具体处理方式见当前清洗产物；不能由缺失率推断填补方式。"
        if capability_query:
            answer = "当前可用任务：" + '、'.join(availability['available_tasks']) + "。缺少：" + '、'.join(availability['missing_requirements']) + "。建模、寻优与控制仍须各自通过字段、分区、验证和生产安全门禁。"
        availability["requested_task_status"] = "executed" if profile else "evidence_only"
        response = {'answer': answer, 'run_id': snapshot.get('run_id'), 'executed': bool(profile), 'blocked': False,
                    'execution_scope': 'basic_data_exploration' if profile else 'evidence_only',
                    'execution_mode': 'analysis', 'needs_clarification': False,
                    'intent': {'key': task.get('response_intent'), 'label': '基础数据检查' if profile else '知识与证据问答'},
                    'answer_intent': task.get('answer_intent'), 'cards': expert.get('cards', []) if expert else [],
                    'suggestions': availability['next_actions'], 'skill_executions': [], 'logs': [],
                    'capability_availability': availability, 'basic_data_profile': profile,
                    'runtime_observability': {}, 'skill_plan': {'steps': [], 'analysis': {'task_understanding': task}}}
        return _finish_answer(message, snapshot, response, llm_config, event_sink)
    if task.get('action_type') in {'GENERATE_REPORT', 'EXPORT_ARTIFACT'}:
        from .delivery_report import artifact_manifest, generate_report
        if task['action_type'] == 'GENERATE_REPORT':
            # Reload the persisted baseline, not the projected winner view.
            snapshot = generate_report(get_run(snapshot['run_id']))
        manifest = artifact_manifest(snapshot)
        available = [{'key': key, 'label': {'analysis_report_html': '图文报告 HTML', 'report_package_zip': '报告与图片 ZIP', 'modeling_csv': '胜者建模数据 CSV'}.get(key, key), 'url': f"/api/pipeline/runs/{snapshot['run_id']}/artifacts/{key}/", **item}
                     for key, item in manifest.items() if item['state'] == 'ready']
        answer = ('已基于本次已保存证据生成图文报告；未重新清洗、训练或寻优。' if task['action_type'] == 'GENERATE_REPORT' else '当前任务真实可下载的产物：')
        answer += '\n' + ('\n'.join(f"{item['key']}: {item['url']}" for item in available) or '暂无可下载产物；需要先完成对应任务。')
        response = {'answer': answer, 'run_id': snapshot['run_id'], 'snapshot': snapshot,
                    'executed': task['action_type'] == 'GENERATE_REPORT', 'numeric_executions': 0,
                    'execution_scope': 'report' if task['action_type'] == 'GENERATE_REPORT' else 'evidence_only',
                    'execution_mode': 'analysis', 'cards': [], 'suggestions': [], 'skill_executions': [], 'logs': [],
                    'deliverables': available, 'intent': {'key': 'review', 'label': '当前产物'},
                    'skill_plan': {'steps': [], 'analysis': {'task_understanding': task}}, 'runtime_observability': {}}
        return _finish_answer(message, snapshot, response, llm_config, event_sink)
    requested = dict(parameters or {})

    if event_sink:
        event_sink("task_understanding_started", stage="task_understanding", status="executing", message="正在理解任务目标与执行边界")
        event_sink("skill_resolution_started", stage="skill_resolution", status="executing", message="正在结合数据上下文解析 Skill 与 Capability")
    previous_semantic = [name for name, chat_intent in TASK_INTENT_TO_CHAT_INTENT.items() if chat_intent in set(previous_intents or ([previous_intent] if previous_intent else []))]
    previous_response_intents = list(previous_intents or ([previous_intent] if previous_intent else []))
    conversation_context = {"previous_task_spec": {"semantic_intents": previous_semantic, "response_intent": previous_intent, "response_intents": previous_response_intents}} if previous_semantic or previous_response_intents else None
    skill_plan = plan_skills(message, snapshot["run_id"], snapshot=snapshot, conversation_context=conversation_context, task_spec=task)
    if event_sink:
        analysis = skill_plan.get("analysis", {})
        task = analysis.get("task_understanding", {})
        event_sink("task_understanding_completed", stage="task_understanding", status="completed", message=f"任务理解完成：{task.get('objective') or message}", metadata={"task_kind": task.get("task_kind"), "execution_mode": task.get("execution_mode")})
        resolution = analysis.get("capability_resolution", {})
        for candidate in resolution.get("candidates", []):
            status = "selected" if candidate.get("selected") else candidate.get("status", "skipped")
            event_sink(f"capability_{status}", stage="skill_resolution", capability_id=candidate.get("candidate"), status=status,
                       message=candidate.get("reason") or f"{candidate.get('candidate')} {status}", metadata={"candidate": candidate})
        loaded = analysis.get("skill_runtime", {})
        selected_skills = analysis.get("skill_resolution", {}).get("selected_skills", [])
        for selected_skill in selected_skills:
            event_sink("skill_selected", stage="skill_resolution", skill_id=selected_skill, status="selected", message=f"已选择 Skill：{selected_skill}")
        if loaded.get("loaded") or selected_skills:
            event_sink("skill_loaded", stage="skill_loading", skill_id=loaded.get("skill_name") or (selected_skills[0] if selected_skills else None), status="loaded",
                       message="Skill 文档与运行约束已加载", metadata={"loaded_files": loaded.get("loaded_files", []), "capabilities": resolution.get("selected", [])})
        core_plan = analysis.get("execution_plan", {}).get("core", {})
        event_sink("execution_plan_created", stage="planning", status="completed", message=f"已生成 {len(core_plan.get('steps', []))} 个 Executor 节点", metadata={"execution_dag": core_plan})
        for node in core_plan.get("steps", []):
            waiting = node.get("readiness_status") in {"deferred", "waiting"}
            event_sink("executor_waiting" if waiting else "executor_queued", stage="planning", executor=node.get("executor"), status="waiting" if waiting else "queued",
                       message=node.get("readiness_reason") or f"{node.get('executor')} Executor 已入队", metadata={"missing_artifacts": node.get("missing_artifacts", []), "dependencies": node.get("dependencies", [])})
    if getattr(settings, "AGENT_RUNTIME_MODE", "hybrid") == "legacy":
        intent, confidence, keywords, matched_intents = _detect_intent(message, previous_intent, previous_intents)
    else:
        intent, confidence, keywords, matched_intents = _intent_from_task_spec(skill_plan["analysis"]["task_understanding"])
    if skill_plan["analysis"].get("needs_clarification") and previous_intent == intent and intent not in {"conversation", "capability", "clarification", "overview"} and not keywords:
        skill_plan = plan_skills("解释" + INTENT_LABELS[intent] + "结果", snapshot["run_id"], snapshot=snapshot)
        skill_plan["objective"] = message
        skill_plan["mode"] = skill_plan["analysis"]["mode"] = "analyze"
        skill_plan["analysis"]["context_intent"] = intent
    parsed_parameters = dict(skill_plan.get("parameters", {}))
    parsed_parameters.update({row['name']: row['value'] for row in task.get('parameters', []) if row.get('source') == 'llm_validated'})
    parsed_parameters.update(requested)
    skill_plan["parameters"] = parsed_parameters
    policy_receipt = snapshot_policy(snapshot, parsed_parameters)
    requested_family = _scenario_family(skill_plan.get("entities", {}).get("scenario"))
    current_scenario = snapshot.get("results", {}).get("standardization", {}).get("scenario", {}).get("scenario_name")
    current_family = _scenario_family(current_scenario)
    mismatch = bool(requested_family and current_family and requested_family != current_family)
    blocked_reason = None
    if mismatch:
        blocked_reason = f"问题指定{skill_plan['entities'].get('equipment_id') or requested_family}，当前 CSV 属于{current_scenario}，设备场景不一致。"
    executed = False
    direct = set(skill_plan.get("direct_skill_ids", []))
    needs_clarification = skill_plan.get("analysis", {}).get("needs_clarification", False) and intent not in {"conversation", "capability", "clarification"}
    action_note = ""
    execution_scope = "evidence_only"
    mcp_execution = None
    core_executor_steps = skill_plan.get("analysis", {}).get("execution_plan", {}).get("core", {}).get("steps", [])
    stop_after = None
    if skill_plan.get("analysis", {}).get("full_pipeline_requested") or "closed_loop_preprocessing_optimizer" in direct:
        stop_after = "report"
    elif "system_identification_trainer" in direct:
        stop_after = "modeling"
    elif "high_snr_dynamic_segment_extractor" in direct:
        stop_after = "selection"
    elif "missing_anomaly_cleaner" in direct or "time_axis_alignment_resampler" in direct:
        stop_after = "cleaning"
    elif "semantic_field_unit_standardizer" in direct or "dataset_scenario_profiler" in direct:
        stop_after = "standardization"
    if task.get("execution_mode") != "execute" and answer_expert_question(message, snapshot):
        needs_clarification = False
    if needs_clarification and not mismatch:
        blocked_reason = "未能确定完整执行目标，请明确需要的技能；没有启动算法。"
    runtime_mode = getattr(settings, "AGENT_RUNTIME_MODE", "hybrid")
    use_pipeline_fallback = runtime_mode == "legacy" or (runtime_mode == "hybrid" and not core_executor_steps)
    mcp_tool = None
    if skill_plan.get("analysis", {}).get("full_pipeline_requested") or "closed_loop_preprocessing_optimizer" in direct:
        mcp_tool = "run_closed_loop_optimization"
    elif direct.intersection({"system_identification_trainer", "arx_structure_order_selector", "time_delay_estimator_compensator", "collinearity_detector_reducer"}):
        mcp_tool = "run_decoupling_identification"
    elif "high_snr_dynamic_segment_extractor" in direct:
        mcp_tool = "run_dynamic_selection"
    mcp_url = getattr(settings, "PROCESSPILOT_MCP_URL", "")
    execution_authorized = task.get('execution_mode') == 'execute' and task.get('action_type') in {'EXECUTE_NUMERIC', 'CONTINUE_OPTIMIZATION'}
    if task.get("requested_outputs") == ["charts"]:
        execution_authorized = True
    if not execution_authorized:
        skill_plan["mode"] = skill_plan["analysis"]["mode"] = "analyze"
        skill_plan["analysis"].get("execution_plan", {}).get("core", {})["steps"] = []
    if execution_authorized and availability["missing_requirements"]:
        blocked_reason = "建模输入契约不满足：" + '、'.join(availability["missing_requirements"])

    if mcp_url and mcp_tool and skill_plan.get("mode") == "execute" and execution_authorized and not blocked_reason and not needs_clarification:
        resample_seconds = _number(message, (r"(?:按|改为|使用)\s*(\d+)\s*(?:秒|s)",), 10)
        max_lag = _number(message, (r"时滞(?:范围)?\s*(?:改为|为|=)?\s*(\d+)", r"max[_ ]?lag\s*[=:]?\s*(\d+)"), 60)
        def publish_mcp_progress(payload):
            if not event_sink:
                return
            mcp_status = payload.get("status", "running")
            current = payload.get("current_stage") or {}
            progress = payload.get("progress") or {}
            percent = progress.get("percent")
            terminal = mcp_status in {"completed", "partial", "blocked", "failed", "cancelled"}
            event_type = (
                "mcp_tool_completed" if terminal and mcp_status in {"completed", "partial"}
                else "mcp_tool_blocked" if mcp_status == "blocked"
                else "mcp_tool_cancelled" if mcp_status == "cancelled"
                else "mcp_tool_failed" if mcp_status == "failed"
                else "mcp_tool_progress"
            )
            event_sink(
                event_type,
                stage=f"mcp:{current.get('key') or payload.get('stage') or 'queued'}",
                status=mcp_status if terminal else "executing",
                message=(
                    f"MCP {mcp_tool}：{current.get('label') or '任务已提交'}"
                    + (f" · {current.get('message')}" if current.get("message") else "")
                ),
                progress=float(percent) if isinstance(percent, (int, float)) else None,
                metadata={
                    "protocol": "MCP",
                    "tool_name": mcp_tool,
                    "job_id": payload.get("job_id"),
                    "run_id": payload.get("run_id"),
                    "current_stage": current,
                    "execution_timeline": payload.get("execution_timeline", []),
                    "quality_gates": payload.get("quality_gates", []),
                    "artifact_count": len(payload.get("output_artifacts", [])),
                },
            )
        try:
            mcp_execution = invoke_mcp_and_wait(
                mcp_url,
                mcp_tool,
                snapshot["run_id"],
                parameters=parsed_parameters,
                request_key=skill_run_id,
                timeout_seconds=float(getattr(settings, "PROCESSPILOT_MCP_TIMEOUT_SECONDS", 180)),
                on_progress=publish_mcp_progress,
            )
        except MCPInvocationError as exc:
            raise PipelineError(str(exc)) from exc
        result_run_id = mcp_execution.get("run_id")
        result_snapshot = get_run(result_run_id) if result_run_id else None
        if result_snapshot:
            snapshot = result_snapshot
            policy_receipt = snapshot.get("policy_receipt") or snapshot_policy(snapshot, parsed_parameters)
        if mcp_execution.get("status") in {"completed", "partial"} and result_snapshot:
            executed = True
            execution_scope = {
                "run_dynamic_selection": "selection",
                "run_decoupling_identification": "modeling",
                "run_closed_loop_optimization": "optimization",
            }[mcp_tool]
            skill_plan = plan_skills(message, snapshot["run_id"], snapshot=snapshot, task_spec=task)
            # The algorithms already ran through MCP. The local Skill runtime now
            # reads and renders their evidence instead of executing a second copy.
            skill_plan["mode"] = "analyze"
            skill_plan["analysis"]["mode"] = "analyze"
            skill_plan["analysis"]["mcp_execution"] = mcp_execution
        elif mcp_execution.get("status") == "blocked":
            error = mcp_execution.get("error") or {}
            blocked_reason = error.get("message") or "MCP 质量门禁阻断了本次执行。"
            skill_plan["mode"] = "analyze"
            skill_plan["analysis"]["mode"] = "analyze"
            skill_plan["analysis"]["mcp_execution"] = mcp_execution
        else:
            error = mcp_execution.get("error") or {}
            raise PipelineError(error.get("message") or f"MCP 任务状态异常：{mcp_execution.get('status')}")
    from core.skills.artifacts import RuntimeArtifactResolver
    has_source = bool(RuntimeArtifactResolver(snapshot).resolve("SOURCE_DATA"))
    if (use_pipeline_fallback or mcp_tool == "run_closed_loop_optimization" and has_source) and not mcp_execution and skill_plan.get("mode") == "execute" and execution_authorized and not blocked_reason and not needs_clarification and stop_after:
        resample_seconds = _number(message, (r"(?:按|改为|使用)\s*(\d+)\s*(?:秒|s)",), 10)
        max_lag = _number(message, (r"时滞(?:范围)?\s*(?:改为|为|=)?\s*(\d+)", r"max[_ ]?lag\s*[=:]?\s*(\d+)"), 60)
        rerun_kwargs = {"parameters": parsed_parameters}
        if stop_after != "report":
            rerun_kwargs["stop_after"] = stop_after
        snapshot = rerun_pipeline(snapshot["run_id"], **rerun_kwargs)
        execution_scope = stop_after
        executed = True
        skill_plan = plan_skills(message, snapshot["run_id"], snapshot=snapshot, task_spec=task)
        skill_plan["mode"] = skill_plan["analysis"]["mode"] = "analyze"
        policy_receipt = snapshot.get("policy_receipt") or snapshot_policy(snapshot, parsed_parameters)
        skill_plan["analysis"]["execution_plan"]["fallback"] = {
            "used": runtime_mode == "hybrid",
            "reason": "selected capability has no migrated executor" if runtime_mode == "hybrid" else "legacy runtime mode",
        }

    if executed and 'GENERATE_REPORT' in task.get('constraints', {}).get('requested_actions', []) and not blocked_reason:
        from .delivery_report import generate_report
        snapshot = final_result_view(generate_report(get_run(snapshot['run_id'])))
        execution_scope = 'report'
    snapshot = final_result_view(snapshot)
    answer, cards, suggestions = _answer(snapshot, intent, message, matched_intents)
    # A broad multi-topic summary should retain its complete overview.  A single
    # expert keyword such as “评审结论” must not replace the other requested areas.
    broad_summary = intent == "overview" and message.strip().startswith(("总结", "整体总结", "全部总结"))
    task_understanding = skill_plan.get("analysis", {}).get("task_understanding", {})
    answer_intent = task_understanding.get("answer_intent") or {}
    response_domains = task_understanding.get("response_intents") or []
    # Expert topics are resolved from the user's actual words.  Do not force an
    # SNR answer merely because a compound task also mentions selection: that
    # previously overrode field-review and missing-data questions.
    topic_hints = []
    expert_answer = answer_expert_question(
        message, snapshot, answer_intent=answer_intent, topic_hints=topic_hints,
    ) if intent not in {"conversation", "clarification"} and not broad_summary else None
    if expert_answer:
        answer = expert_answer["answer"]
        cards = expert_answer["cards"]
        suggestions = expert_answer["suggestions"]
    selected_skill_ids = {item["skill_id"] for item in skill_plan.get("steps", [])}
    is_compound = {"high_snr_dynamic_segment_extractor", "collinearity_detector_reducer", "closed_loop_preprocessing_optimizer"}.issubset(selected_skill_ids)
    if mismatch:
        answer = (
            f"已识别为复合执行任务，但已被设备一致性门禁阻断：{blocked_reason}"
            f"我没有把当前场景结果冒充为{skill_plan['entities'].get('equipment_id') or requested_family}的结果，也没有启动后续辨识和寻优。"
            "请上传对应设备的 CSV，或明确说明仅使用当前数据做流程演示。"
        )
        cards = [
            {"label": "执行状态", "value": "已阻断"}, {"label": "请求设备", "value": skill_plan["entities"].get("equipment_id") or requested_family},
            {"label": "当前数据", "value": current_scenario}, {"label": "原因", "value": "设备场景不一致"},
        ]
        suggestions = ["上传对应场景CSV", "改用当前数据执行这条任务", "查看当前数据的设备与字段"]
    elif executed and is_compound:
        degraded = int(snapshot.get("results", {}).get("cleaning", {}).get("selected_segment_count") or 0) == 0
        answer, cards, suggestions = _compound_result(snapshot, degraded)
    if blocked_reason and mcp_execution and not mismatch:
        answer = f"MCP 已安全阻断本次执行：{blocked_reason}没有绕过数据、场景或模型质量门禁。"
        cards = [{"label": "MCP 状态", "value": "已阻断"}, {"label": "工具", "value": mcp_execution.get("tool_name")}, {"label": "任务", "value": mcp_execution.get("job_id")}]
        suggestions = ["查看阻断原因", "检查字段与场景映射", "上传符合场景契约的数据"]
    elif needs_clarification and not mismatch:
        candidates = [item["name"] for item in skill_plan.get("steps", []) if item.get("selection_kind") == "direct"]
        answer = blocked_reason + ("可选方向：" + "、".join(candidates) if candidates else "请说明要处理的数据和目标。")
        cards = [{"label": "路由状态", "value": "需要澄清"}]
    elif skill_plan.get("mode") == "execute" and not executed and not mismatch:
        if direct <= {"final_artifact_exporter", "evidence_audit_reproducer"}:
            answer = "已整理当前任务已有产物与证据的下载入口。" + answer
        else:
            action_note = "已识别请求并读取现有证据；这些技能尚无独立算法执行接口，本次没有生成新结果。"
            answer = action_note + answer
    if executed:
        scope_label = "全流程" if execution_scope == "report" else {"standardization": "字段标准化", "cleaning": "清洗", "selection": "动态段提取", "modeling": "系统辨识", "optimization": "闭环寻优"}[execution_scope]
        answer = f"已执行至{scope_label}，新任务编号为 {snapshot['run_id']}。" + answer
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    logs = [
        {"time": now, "level": "INFO", "text": f"识别意图 {intent}，置信度 {confidence:.0%}"},
        *([{"time": now, "level": "EXPERT", "text": f"命中专家问题域：{expert_answer['topic_name']}"}] if expert_answer else []),
        {"time": now, "level": "TOOL", "text": f"读取任务 {snapshot['run_id']} 的标准化、清洗、辨识和评审证据"},
        *([{"time": now, "level": "MCP", "text": f"通过 {mcp_execution.get('tool_name')} 完成任务 {mcp_execution.get('job_id')}"}] if mcp_execution else []),
        {"time": now, "level": "WARN" if blocked_reason else "BEST" if executed else "INFO", "text": blocked_reason if blocked_reason else f"已执行至 {execution_scope} 并刷新证据" if executed else "本次为只读分析，未修改运行产物"},
    ]
    skill_run = execute_skill_plan(skill_plan, snapshot, blocked_reason=blocked_reason, skill_run_id=skill_run_id, event_sink=event_sink)
    skill_result = skill_run.get("skill_execution_result") or {}
    core_results = skill_run.get("core_skill_execution_results", [])
    core_success = [item for item in core_results if item.get("status") in {"success", "partial"}]
    if core_results and not blocked_reason:
        executed = bool(core_success)
        execution_scope = "+".join(item.get("skill_id", "") for item in core_results)
        if core_success:
            action_note = ""
            answer = "已按最小执行计划调用独立 Skill Executor。" + answer
        elif any(item.get("status") == "blocked" for item in core_results):
            action_note = "独立 Executor 因前置条件不足而阻断；没有回退到 synthetic data 或重跑 Pipeline。"
            answer = action_note + answer
    if skill_result and not core_results and not executed and not blocked_reason and not expert_answer and intent != "standardization":
        answer = DeterministicResponseRenderer().render(skill_plan["analysis"]["task_understanding"], skill_result)
    if skill_plan.get("mode") == "execute" and skill_plan.get("analysis", {}).get("routing_source") == "md_registry" and not blocked_reason and (core_results and execution_authorized or not expert_answer and execution_authorized):
        from core.skills.md_response import render_manifest_response
        answer, cards, suggestions = render_manifest_response(skill_plan, core_results)
        action_note = ""
    logs.extend({
        "time": now,
        "level": "SKILL",
        "text": f"{item['name']} · {item.get('activity', item['status'])} · {item['duration_ms']} ms",
    } for item in skill_run["executions"])
    if event_sink:
        event_sink("answer_generation_started", stage="answer", status="executing", message="正在整理执行证据与回答")
    from core.skills.chart_artifacts import public_charts
    availability["requested_task_status"] = "blocked" if blocked_reason else "executed" if executed else "evidence_only"
    availability["executed_scope"] = execution_scope
    response = {
        "policy_receipt": policy_receipt,
        "capability_availability": availability,
        "charts": public_charts(skill_run["skill_run_id"], skill_run),
        "answer": answer,
        "run_id": snapshot["run_id"],
        "executed": executed,
        "blocked": bool(blocked_reason),
        "needs_clarification": needs_clarification,
        "execution_scope": execution_scope,
        "action_note": action_note,
        "execution_mode": "blocked" if blocked_reason else ("executed" if executed else "analysis"),
        "intent": {"key": intent, "label": INTENT_LABELS[intent], "confidence": confidence, "keywords": keywords, "matched": matched_intents},
        "cards": cards,
        "suggestions": suggestions,
        "plan": _stage_plan(snapshot, intent, executed),
        "skill_plan": skill_plan,
        "skill_run_id": skill_run["skill_run_id"],
        "skill_executions": skill_run["executions"],
        "skill_summary": skill_run["summary"],
        "runtime_observability": {
            "capabilities": skill_plan.get("analysis", {}).get("capability_resolution", {}).get("candidates", []),
            "execution_dag": skill_plan.get("analysis", {}).get("execution_plan", {}).get("core", {}),
            "skill_loading": skill_plan.get("analysis", {}).get("skill_runtime", {}),
            "executor_results": core_results,
            "artifacts": skill_run.get("artifact_registry", []),
            "mcp": mcp_execution,
        },
        "deliverables": _deliverables(snapshot) if (executed or "final_artifact_exporter" in direct) and not blocked_reason else [],
        "expert_topic": expert_answer["topic"] if expert_answer else None,
        "expert_topics": expert_answer.get("topics", []) if expert_answer else [],
        "answer_intent": expert_answer.get("answer_intent", answer_intent) if expert_answer else answer_intent,
        "logs": logs,
        "snapshot": snapshot if executed else None,
    }
    return _finish_answer(message, snapshot, response, llm_config, event_sink)


def _finish_answer(message, snapshot, response, llm_config, event_sink=None):
    from .answer_context import ground_response
    response = ground_response(message, snapshot, response)
    logs = response.setdefault("logs", [])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    if llm_config and llm_config.get("provider") not in {None, "", "evidence"}:
        deterministic_answer = response["answer"]
        if event_sink:
            event_sink("llm_generation_started", stage="answer", status="executing", message=f"正在调用 {llm_config.get('provider')} 生成证据约束回答")
        emitted_characters = 0
        delta_buffer: list[str] = []

        def flush_delta() -> None:
            nonlocal delta_buffer
            delta = "".join(delta_buffer)
            if delta and event_sink:
                event_sink("llm_response_delta", stage="answer", status="streaming", message=f"模型已生成 {emitted_characters} 字", metadata={"delta": delta, "generated_characters": emitted_characters})
            delta_buffer = []

        def emit_delta(delta: str) -> None:
            nonlocal emitted_characters
            emitted_characters += len(delta)
            delta_buffer.append(delta)
            if len("".join(delta_buffer)) >= 20:
                flush_delta()

        try:
            generated = generate_grounded_answer(
                message=message, snapshot=snapshot, response=response, config=llm_config, on_delta=emit_delta,
            )
            if generated.get('fallback_reason'):
                raise LLMGatewayError(generated['fallback_reason'])
            flush_delta()
            response["answer"] = generated["answer"]
            response["deterministic_answer"] = deterministic_answer
            response["llm"] = {**{key: value for key, value in generated.items() if key != "answer"}, "used": True, "fallback": False, "error_reason": None}
            response["answer_mode"] = "llm_grounded"
            cited = set(generated.get("used_source_ids", []))
            response["used_run_evidence"] = [key for key in response["used_run_evidence"] if key in cited]
            response["used_knowledge_chunks"] = [row['chunk_id'] for row in response['answer_sources'] if row['id'] in cited and row.get('chunk_id')]
            response['citation_coverage'] = generated.get('citation_coverage', 'not_cited')
            logs.append({"time": now, "level": "LLM", "text": f"{generated.get('label', generated['provider'])} · {generated['model']} · 证据约束生成完成"})
            if event_sink:
                event_sink("llm_generation_completed", stage="answer", status="completed", message=f"{generated.get('label', generated['provider'])} 回答生成完成", metadata={"provider": generated["provider"], "model": generated["model"]})
        except LLMGatewayError as exc:
            response["llm"] = {"provider": llm_config.get("provider"), "model": llm_config.get("model"), "used": False, "fallback": True, "error": str(exc), "error_reason": str(exc)}
            logs.append({"time": now, "level": "WARN", "text": f"大模型不可用，已回退 Evidence Agent：{exc}"})
            if event_sink:
                event_sink("llm_generation_failed", stage="answer", status="partial", message=f"大模型不可用，已安全回退到证据回答：{exc}")
    else:
        response["llm"] = {"provider": "evidence", "model": "deterministic-evidence-v1", "used": False, "fallback": False, "error_reason": None}
        if event_sink:
            for offset in range(0, len(response["answer"]), 20):
                delta = response["answer"][offset:offset + 20]
                event_sink("llm_response_delta", stage="answer", status="streaming", message=f"Evidence Agent 已生成 {min(offset + 20, len(response['answer']))} 字", metadata={"delta": delta, "generated_characters": min(offset + 20, len(response["answer"]))})
    if event_sink:
        event_sink("answer_generation_completed", stage="answer", status="completed", message="回答已生成")
    return response
