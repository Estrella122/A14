from __future__ import annotations

from typing import Any

from .catalog import WORK_REPAIR_TASK_TYPES


TASK_RULES = {
    "FIELD_UNIFICATION": ("字段", "语义", "单位", "standard_field", "mapping_confidence"),
    "SCENE_RECOGNITION": ("场景识别", "识别正确", "scene"),
    "SCENE_REGISTRY": ("scene registry", "场景注册", "场景配置"),
    "DATA_CLEANING": ("清洗", "缺失", "异常", "重采样"),
    "PIPELINE": ("pipeline", "流水线", "数据流", "识别正确"),
    "MODELING_GATE": ("建模门禁", "modeling gate", "准入", "建模"),
    "FRONTEND_PAGE": ("页面", "前端", "vue", "组件"),
    "PAGE_SCENE_MAPPING": ("页面场景", "路由映射", "page scene"),
    "INDUSTRIAL_ANALYSIS": ("工业分析", "趋势", "相关", "根因", "能耗"),
    "AGENT": ("agent", "智能体", "代理"),
    "BUG_DIAGNOSIS": ("bug", "错误", "失败", "不一致", "但页面", "诊断"),
    "TESTING": ("测试", "回归", "验证"),
    "ARCHITECTURE": ("架构", "重构", "模块", "skill"),
}

LAZY_ROUTES = {
    "FIELD_UNIFICATION": ("field_system", "field_unification"),
    "SCENE_RECOGNITION": ("scene_system", "scene_recognition"),
    "SCENE_REGISTRY": ("scene_system", "scene_registry"),
    "DATA_CLEANING": ("data_pipeline", "data_cleaning"),
    "PIPELINE": ("data_pipeline", "bug_diagnosis"),
    "MODELING_GATE": ("data_pipeline", "modeling_gate"),
    "FRONTEND_PAGE": ("frontend_page_mapping", "frontend_change"),
    "PAGE_SCENE_MAPPING": ("frontend_page_mapping", "scene_recognition"),
    "INDUSTRIAL_ANALYSIS": ("industrial_analysis", "analysis_plan"),
    "AGENT": ("agent_contract", "bug_diagnosis"),
    "BUG_DIAGNOSIS": ("data_pipeline", "bug_diagnosis"),
    "TESTING": ("testing_system", "regression"),
    "ARCHITECTURE": ("architecture", "change_review"),
}


def route_work_repair_task(message: str) -> dict[str, Any]:
    """工程级路由：多标签分类，并只返回命中任务需要的知识入口。"""
    normalized = (message or "").lower()
    task_types = [task for task in WORK_REPAIR_TASK_TYPES if any(term in normalized for term in TASK_RULES[task])]
    if not task_types:
        task_types = ["ARCHITECTURE"]
    refs: list[str] = []
    workflows: list[str] = []
    for task in task_types:
        reference, workflow = LAZY_ROUTES[task]
        if reference not in refs:
            refs.append(reference)
        if workflow not in workflows:
            workflows.append(workflow)
    return {"task_types": task_types, "lazy_loading": {"references": refs, "workflows": workflows}}
