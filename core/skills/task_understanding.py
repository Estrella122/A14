from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .answer_intent import resolve_answer_intent
from .visualization_request import requests_chart


@dataclass
class TaskSpec:
    objective: str
    task_kind: str
    action_type: str = "QUERY_EXISTING"
    semantic_intents: list[str] = field(default_factory=list)
    requested_capabilities: list[str] = field(default_factory=list)
    requested_outputs: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "analyze"
    negations: list[str] = field(default_factory=list)
    scene_hint: str | None = None
    requires_clarification: bool = False
    clarification_reason: str | None = None
    confidence: float = 0.0
    provider: str = "legacy_rule"
    response_intent: str = "overview"
    response_intents: list[str] = field(default_factory=list)
    answer_intent: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        return asdict(self)


class TaskUnderstandingProvider(ABC):
    @abstractmethod
    def understand(self, message: str, conversation_context: dict[str, Any] | None = None) -> TaskSpec:
        raise NotImplementedError


INTENT_PATTERNS = {
    "scene_identification": r"(?:这个|这批|当前|上传)?数据.{0,12}(?:什么|哪个|哪种).{0,8}场景|(?:什么|哪个|哪种).{0,8}工业场景|(?:属于|识别为).{0,8}(?:什么|哪个|哪种).{0,8}场景",
    "anomaly_detection": r"异常|不正常|不一样|偏离正常|重点检查|波动.{0,8}(?:问题|异常)|忽高忽低",
    "process_stability": r"稳定|正常运行|波动|漂移|越来越",
    "trend_analysis": r"趋势|走势|变化|越来越|上升|下降",
    "time_window_analysis": r"时间段|重点检查|哪些时候|哪段|时滞|滞后",
    "relationship_analysis": r"相关|关联|因果|影响",
    "missing_data_analysis": r"缺失|空值|完整性",
    "energy_analysis": r"能耗|能源|电量|功率|燃料",
    "quality_analysis": r"产品质量|合格率|硅含量|水分",
    "equipment_health": r"设备健康|故障|劣化|振动",
    "bottleneck_analysis": r"瓶颈|产能|卡点",
    "root_cause_analysis": r"根因|为什么|原因",
    "data_profiling": r"数据概况|数据画像|概览这批数据|列名|行数|列数|数据类型|重复行|常量列|时间.*可解析",
}

INTENT_CAPABILITIES = {
    "scene_identification": "DATA_PROFILING",
    "anomaly_detection": "ANOMALY_DETECTION", "process_stability": "PROCESS_STABILITY",
    "trend_analysis": "TREND_ANALYSIS", "time_window_analysis": "TIME_SERIES_ANALYSIS",
    "relationship_analysis": "CORRELATION_ANALYSIS", "missing_data_analysis": "MISSING_DATA_ANALYSIS",
    "energy_analysis": "ENERGY_ANALYSIS", "quality_analysis": "QUALITY_ANALYSIS",
    "equipment_health": "EQUIPMENT_HEALTH", "bottleneck_analysis": "BOTTLENECK_ANALYSIS",
    "root_cause_analysis": "ROOT_CAUSE_CANDIDATES", "data_profiling": "DATA_PROFILING",
}

OBJECTIVE_LABELS = {
    "scene_identification": "识别当前数据的工业场景",
    "anomaly_detection": "识别异常波动", "process_stability": "评估过程稳定性",
    "trend_analysis": "分析变化趋势", "time_window_analysis": "定位重点时间段",
    "relationship_analysis": "分析变量关系", "missing_data_analysis": "检查数据完整性",
    "energy_analysis": "分析能源表现", "quality_analysis": "分析产品质量",
    "equipment_health": "评估设备状态", "bottleneck_analysis": "定位过程瓶颈",
    "root_cause_analysis": "筛选根因候选", "data_profiling": "概括数据特征",
}

RESPONSE_INTENT_PATTERNS = (
    ("standardization", r"字段|映射|标准|单位|场景|变量角色"),
    ("cleaning", r"清洗|缺失|异常值|数据质量|插值|采样周期|采样频率|混叠"),
    ("selection", r"动态段|动态数据|高信噪比|信噪比|噪声比|筛选|优选|稳态|持续激励|可辨识"),
    ("lag", r"时滞|延迟|滞后|补偿|互相关"),
    ("collinearity", r"共线|vif|冗余|相关变量|降维"),
    ("modeling", r"模型|建模|辨识|arx|拟合|r2|r²|rmse|mae|预测|残差|白噪声|稳定性|极点|伯德|奈奎斯特|频响|过拟合|泛化|数据泄漏|阶次|aic|bic"),
    ("optimization", r"寻优|优化|候选|最佳策略|最优策略|最优轮次|轮次|闭环|目标函数|收敛|停止条件|局部最优"),
    ("review", r"评审|通过|报告|交付|缺陷|风险|上线|投运|联锁|审计|复现|迁移|模型漂移"),
    ("diagnosis", r"最大的问题|主要问题|有什么问题|哪里不好|问题是什么|薄弱|短板|瓶颈"),
)


REQUEST_PREFIX_ACTION = re.compile(
    r"^(?:请|麻烦|劳驾|帮我|帮忙|给我|替我|我需要|我想)"
    r".{0,40}?(?:执行|运行|训练|清洗|生成|提取|找出|筛选|计算|估计|导出|下载|优化|寻优|建立|建模|剔除|补偿|冻结|选择|选取|尝试)",
)
OPERATIONAL_ACTION = re.compile(
    r"(?:自动尝试|重新执行|重新运行|重跑|开始执行|立即执行|"
    r"补偿.{0,16}(?:时滞|滞后|延迟)|剔除.{0,16}(?:冗余|共线|变量)|"
    r"冻结.{0,16}(?:数据|模型|候选|策略))"
)


class LegacyRuleTaskUnderstandingProvider(TaskUnderstandingProvider):
    """Explicit fallback. It makes no claim of LLM or embedding semantics."""

    def understand(self, message: str, conversation_context: dict[str, Any] | None = None) -> TaskSpec:
        text = str(message or "").strip()
        normalized = text.lower()
        answer_intent = resolve_answer_intent(text, conversation_context)
        if re.search(r"你好|您好|在吗|嗨|\bhello\b|\bhi\b", normalized):
            return TaskSpec("进行自然对话", "conversation", execution_mode="explain", confidence=.99, response_intent="conversation", response_intents=["conversation"], answer_intent=answer_intent)
        if re.search(r"你是谁|你能做什么|怎么用|有什么功能|能干什么", normalized):
            return TaskSpec("说明 Agent 能力和使用方式", "knowledge_explanation", requested_outputs=["explanation"], execution_mode="explain", confidence=.98, response_intent="capability", response_intents=["capability"], answer_intent=answer_intent)
        knowledge = bool(re.search(r"(?:解释|介绍|说明).{0,20}(?:是什么|什么意思|概念|区别)|^(?:解释|介绍|说明)(?:一下)?(?:异常检测|趋势分析|相关性|因果)|(?:异常检测|趋势分析|相关性|因果).{0,12}(?:是什么|什么意思|有什么区别)[？?]?$", normalized))
        knowledge = knowledge or bool(re.search(r'(?:信噪比|snr|firx|自回归|共线性|时滞|vif)(?:到底|究竟)?(?:是什么|什么意思)|基本概念|原理|a14.*(?:怎么算|方法)|请解释为什么需要重新训练', normalized))
        artifact = bool(re.search(r"导出|下载|打包|产物|生成.{0,8}报告", normalized))
        question = bool(re.search(r"为什么|为何|怎么|如何|是否|能否|什么|哪些|[？?吗呢]$", normalized))
        positive_text = re.sub(r"(?:不要|不必|无需|禁止|别)\s*[^，。；]+", "", normalized)
        action = bool(re.search(r"^(?:(?:请|帮我|给我|立即|重新|开始|继续|先|再|只|仅|把|将|对|用|直接)\s*|按\s*\d+\s*(?:秒|s)\s*)*(?:执行|重新执行|重跑|重新运行|运行|训练|清洗|生成|提取|找|找出|筛选|计算|估计|导出|下载|优化|建立|建模|建一个)", positive_text.strip(" ，,。")))
        action = action or bool(re.search(r"(?:通过|调用|使用|用)\s*mcp.{0,24}(?:执行|重新执行|重跑|运行|提取|筛选|训练|辨识|优化|寻优)", positive_text, re.I))
        action = action or bool(re.search(r"^用.{0,30}(?:优化|寻优|训练|建模)", positive_text.strip(" ，,。")))
        action = action or bool(re.search(r"^(?:请|帮我|给我|用这份数据|把|将).{0,30}(?:清洗|训练|建立|建一个|生成|优化|寻优|导出|下载)", positive_text.strip(" ，,。")))
        # Natural user requests commonly place the data object between the
        # polite request and the operation: “帮我从当前数据中筛选……”.  Treat
        # that as execution without requiring users to know or mention MCP.
        action = action or bool(REQUEST_PREFIX_ACTION.search(positive_text.strip(" ，,。")))
        action = action or bool(OPERATIONAL_ACTION.search(positive_text))
        request_then_evaluate = bool(action and re.search(r"并.{0,12}(?:告诉|评估|比较|判断|验证)", normalized))
        # “请说明当前……闭环寻优结果” asks to read evidence; a later
        # capability noun must not turn the leading explanation verb into an
        # execution command.
        if re.search(r"^(?:请)?(?:说明|解释|解读|分析|介绍|告诉我)", normalized) and not re.search(
            r"(?:并|然后|再)(?:请)?(?:执行|运行|重跑|训练|提取|筛选|优化|寻优)", normalized
        ):
            action = False
        if (question and not request_then_evaluate) or re.search(r"按钮|字符串|这句话|原话|原文|引用|提示|如果|假如|假设|会不会|能不能|可不可以", normalized):
            action = False
        execution_mode = "explain" if knowledge else "execute" if action else "analyze"
        task_kind = "knowledge_explanation" if knowledge else "artifact_request" if artifact else "execute_pipeline" if execution_mode == "execute" else "data_analysis"
        intents = [name for name, pattern in INTENT_PATTERNS.items() if re.search(pattern, normalized)]
        negations = re.findall(r"(?:不要|不必|无需|禁止|别)\s*([^，。；]+)", text)
        if negations:
            intents = [name for name in intents if not any(re.search(INTENT_PATTERNS[name], clause.lower()) for clause in negations)]
        previous = (conversation_context or {}).get("previous_task_spec") or {}
        follow_up = bool(re.search(r"这个|该结果|它|那|刚才|继续|具体|然后|这么|靠谱|可靠", normalized))
        if not intents and follow_up:
            intents = list(previous.get("semantic_intents") or [])
        capabilities = [INTENT_CAPABILITIES[item] for item in intents]
        outputs = [name for name, pattern in (("time_windows", r"时间段|哪段"), ("explanation", r"解释|介绍|说明|为什么"), ("findings", r"找|看看|分析|检查|评估"), ("artifact", r"导出|下载|报告")) if re.search(pattern, normalized)]
        objective = "并".join(dict.fromkeys(OBJECTIVE_LABELS[item] for item in intents))
        if knowledge and capabilities:
            objective = "解释" + "、".join(capabilities) + "的概念和适用边界"
        elif artifact:
            objective = "整理并交付当前任务已有产物"
        elif not objective:
            objective = "理解并回答当前工业数据问题" if re.search(r"数据|设备|工况|过程", normalized) else "确认用户任务目标"
        requires_clarification = not intents and not knowledge and not artifact and not re.search(r"数据|设备|工况|过程|模型|清洗|报告", normalized)
        response_intents = [name for name, pattern in RESPONSE_INTENT_PATTERNS if re.search(pattern, normalized)]
        if response_intents:
            requires_clarification = False
        broad_summary = bool(re.search(r"总结|整体|全部|分别|以及", normalized)) and len(response_intents) > 1
        if follow_up and not response_intents:
            previous_responses = list(previous.get("response_intents") or ([previous.get("response_intent")] if previous.get("response_intent") else []))
            if len(previous_responses) == 1:
                response_intents = previous_responses
            elif len(previous_responses) > 1:
                requires_clarification = True
        if requires_clarification and follow_up:
            response_intent = "clarification"
        elif broad_summary:
            response_intent = "overview"
        elif response_intents:
            # Specific domains outrank the generic diagnosis wording in questions.
            response_intent = next((item for item in response_intents if item != "diagnosis"), response_intents[0])
        elif knowledge:
            response_intent = "capability"
        else:
            response_intent = "diagnosis" if "root_cause_analysis" in intents else "overview"
        if requests_chart(text):
            task_kind = "artifact_request"
            execution_mode = "execute"
            objective = "基于当前真实数据生成可视化图表"
            outputs = ["charts"]
            requires_clarification = False
        entity_rows = []
        for match in re.finditer(r"(?:(\d+)\s*号)?(高炉|锅炉|脱丁烷塔|精馏塔|干燥器|设备)", text):
            entity_rows.append({"type": "equipment", "value": match.group(0), "equipment_type": match.group(2), "equipment_id": match.group(1)})
        parameter_rows = []
        for name, pattern, unit in (("resample_seconds", r"(?:采样周期|按|改为)\s*(\d+)\s*(?:秒|s)", "s"), ("max_lag", r"(?:时滞|max[_ ]?lag)[^\d]{0,5}(\d+)", "samples"), ("model_order", r"(?:阶次|order)[^\d]{0,5}(\d+)", "order")):
            match = re.search(pattern, normalized)
            if match:
                parameter_rows.append({"name": name, "value": int(match.group(1)), "unit": unit})
        top_k_match = re.search(r'\b(?:top[_ ]?k|modeling_top_k)\s*[=:：]?\s*(\d+)', normalized)
        if top_k_match:
            parameter_rows.append({'name': 'top_k', 'value': int(top_k_match[1]), 'unit': 'windows'})
        return TaskSpec(
            objective=objective, task_kind=task_kind, semantic_intents=intents,
            requested_capabilities=list(dict.fromkeys(capabilities)), requested_outputs=outputs or ["findings"], entities=entity_rows, parameters=parameter_rows,
            execution_mode=execution_mode, negations=negations,
            constraints={"chart_request": text if requests_chart(text) else None,
                         "use_existing_model": bool(re.search(r"已有模型|现有模型", normalized)),
                         "use_existing_artifacts": bool(re.search(r"已有|现有|当前结果", normalized)),
                         "deep_analysis": bool(re.search(r"完整深度分析|全面深度分析|所有能力|full deep analysis", normalized)),
                         "selection_only": bool(re.search(r"适合建模.{0,8}(?:动态|工况|数据)?段", normalized)
                                                and not re.search(r"重新建模|训练模型|建立模型", normalized))},
            requires_clarification=requires_clarification,
            clarification_reason="未识别出工业数据目标" if requires_clarification else None,
            confidence=round(min(0.92, 0.58 + 0.08 * len(intents) + 0.05 * bool(previous and follow_up)), 2),
            response_intent=response_intent, response_intents=response_intents or [response_intent],
            answer_intent=answer_intent,
        )


class LLMTaskUnderstandingProvider(TaskUnderstandingProvider):
    """Provider-neutral structured-output adapter; a callable is injected by the host."""

    def __init__(self, structured_completion: Callable[[dict[str, Any]], dict[str, Any]]):
        self.structured_completion = structured_completion

    def understand(self, message: str, conversation_context: dict[str, Any] | None = None) -> TaskSpec:
        payload = self.structured_completion({
            "instruction": "Return a TaskSpec JSON object. Separate explanation, analysis and execution; preserve negations.",
            "message": message,
            "conversation_context": conversation_context or {},
            "schema": {name: str(field.type) for name, field in TaskSpec.__dataclass_fields__.items()},
        })
        if isinstance(payload, str):
            payload = json.loads(payload)
        allowed = set(TaskSpec.__dataclass_fields__)
        data = {key: value for key, value in payload.items() if key in allowed}
        data["provider"] = "llm"
        data.setdefault("answer_intent", resolve_answer_intent(message, conversation_context))
        return TaskSpec(**data)


def understand_task(message: str, conversation_context: dict[str, Any] | None = None, provider: TaskUnderstandingProvider | None = None) -> dict[str, Any]:
    task = (provider or LegacyRuleTaskUnderstandingProvider()).understand(message, conversation_context).public()
    boundary = action_boundary(message)
    if boundary['action_type'] == 'QUERY_EXISTING' and task['execution_mode'] == 'execute':
        boundary['action_type'] = 'EXECUTE_NUMERIC'
    task['action_type'] = boundary['action_type']
    task['constraints']['requested_actions'] = boundary['requested_actions']
    if boundary['action_type'] in {'GENERATE_REPORT', 'EXPORT_ARTIFACT'}:
        task.update(task_kind='artifact_request', execution_mode='execute', requires_clarification=False)
    elif boundary['action_type'] in {'QUERY_EXISTING', 'GENERAL_EXPLANATION'}:
        task['execution_mode'] = 'explain' if boundary['action_type'] == 'GENERAL_EXPLANATION' else 'analyze'
    elif boundary['optimization']:
        task.update(task_kind='execute_pipeline', execution_mode='execute', requires_clarification=False,
                    response_intent='optimization', response_intents=list(dict.fromkeys([*task['response_intents'], 'optimization'])))
    if requests_chart(message):
        task.update(task_kind='artifact_request', execution_mode='execute', requested_outputs=['charts'])
        task['action_type'] = 'QUERY_EXISTING'
    if re.search(r'(?:最佳|最优).{0,6}参数', message):
        task.update(response_intent='optimization', response_intents=list(dict.fromkeys([*task['response_intents'], 'optimization'])))
    return task


def action_boundary(message):
    """Execution authority comes from the request, never capability nouns in a report."""
    text = str(message or '').strip()
    positive = re.sub(r'(?:不要|不必|无需|禁止|别)\s*[^，。；,;]+', '', text)
    explanation = bool(re.search(r'^(?:请|帮我|只|仅|\s)*(?:解释|说明|介绍|解读|告诉我)', positive.strip(' ，,。')))
    numeric = bool(re.search(r'(?:重新|继续|开始|执行|运行|重跑).{0,8}(?:全流程|全部流程|寻优|优化|训练|建模|清洗|筛选)|循环(?:比较|评估)|闭环寻优|提取.{0,30}动态|筛选.{0,30}动态|训练模型|建立模型', positive))
    question = bool(re.search(r'为什么|为何|是多少|怎么样|是否|能否|[？?]$', positive))
    compound = bool(re.search(r'(?:并|然后|完成后|再).{0,8}(?:执行|运行|重新|训练|提取|筛选|优化|寻优)', positive))
    if (explanation or question) and not compound:
        numeric = False
    report = bool(re.search(r'(?:生成|制作|整理|输出).{0,16}(?:图文|工程|分析)?报告', positive))
    export = bool(re.search(r'导出|下载|打包', positive)) and not explanation and not question
    # Report requirements list methods as nouns. Only an independent numeric
    # imperative before the report clause authorizes running those methods.
    if report:
        prefix = re.split(r'(?:生成|制作|整理|输出).{0,16}(?:图文|工程|分析)?报告', positive, maxsplit=1)[0]
        numeric = numeric and bool(re.search(r'重新寻优|继续寻优|训练|重跑|循环比较|执行|运行|提取|筛选', prefix))
    optimization = numeric and bool(re.search(r'寻优|优化|闭环|循环(?:比较|评估)|选出(?:最好|最佳)', positive))
    action = 'CONTINUE_OPTIMIZATION' if optimization and '继续' in positive else 'EXECUTE_NUMERIC' if numeric else 'GENERATE_REPORT' if report else 'EXPORT_ARTIFACT' if export else 'GENERAL_EXPLANATION' if explanation else 'QUERY_EXISTING'
    # Preserve existing explicit commands outside the compound patterns.
    if action == 'QUERY_EXISTING' and not question and not explanation and not report and not export:
        if re.search(r'^(?:(?:请|帮我|给我|立即|重新|开始|继续|先|再|只|仅|直接)\s*)*(?:执行|运行|训练|清洗|提取|筛选|计算|估计|优化|寻优|建模)', positive.strip(' ，,。')):
            action = 'EXECUTE_NUMERIC'
    actions = ([action] if action in {'EXECUTE_NUMERIC', 'CONTINUE_OPTIMIZATION'} else []) + (['GENERATE_REPORT'] if report else []) + (['EXPORT_ARTIFACT'] if export else [])
    return {'action_type': action, 'requested_actions': actions or [action], 'optimization': optimization}
