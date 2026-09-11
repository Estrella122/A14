from __future__ import annotations

from dataclasses import asdict, dataclass

from typing import Any

SUPPORTED_SCENARIOS = ("blast_furnace", "debutanizer_column", "industrial_dryer")


WORK_REPAIR_TASK_TYPES = (
    "FIELD_UNIFICATION",
    "SCENE_RECOGNITION",
    "SCENE_REGISTRY",
    "DATA_CLEANING",
    "PIPELINE",
    "MODELING_GATE",
    "FRONTEND_PAGE",
    "PAGE_SCENE_MAPPING",
    "INDUSTRIAL_ANALYSIS",
    "AGENT",
    "BUG_DIAGNOSIS",
    "TESTING",
    "ARCHITECTURE",
)


WORK_REPAIR_MODULE_REFERENCES = (
    "frontend/",
    "core/",
    "integrations/",
)


# 工程级场景配置：优先使用标准化注册场景作为事实真值，补充 registry/文档场景别名仅用于需求侧软路由。
SCENARIO_LIBRARY = {
    "blast_furnace": {
        "id": "blast_furnace",
        "name": "钢铁高炉铁水质量预测",
        "family": "钢铁高炉",
        "aliases": ("高炉", "炼铁高炉", "铁水", "铁水硅含量"),
        "aliases_pattern": ("blast_furnace", "钢铁高炉铁水质量预测"),
    },
    "debutanizer_column": {
        "id": "debutanizer_column",
        "name": "炼油脱丁烷精馏塔",
        "family": "炼油脱丁烷精馏塔",
        "aliases": ("脱丁烷塔", "脱丁烷精馏塔", "精馏塔", "脱丁烷"),
        "aliases_pattern": ("debutanizer_column", "脱丁烷", "精馏塔"),
    },
    "industrial_dryer": {
        "id": "industrial_dryer",
        "name": "工业干燥器",
        "family": "工业干燥器",
        "aliases": ("工业干燥器", "干燥器", "干燥机", "烘干机"),
        "aliases_pattern": ("industrial_dryer", "工业干燥器"),
    },
}

# 兼容层：不增加新场景执行语义，仅作为软路由提示；实际运行仍以已有场景标准为准。
EXTENDED_SCENE_HINTS = {
    "steel_industry_energy": {"name": "钢铁工业能源", "family": "钢铁工业能源", "aliases": ("steel_industry_energy", "钢厂加热炉", "加热炉")},
    "thermal_power_boiler_long_tail": {"name": "火电锅炉长尾", "family": "火电锅炉", "aliases": ("thermal_power_boiler_long_tail", "热源锅炉", "锅炉长尾", "锅炉")},
    "vapor_pressure_soft_sensor": {"name": "蒸汽压力软测量", "family": "蒸汽系统", "aliases": ("vapor_pressure_soft_sensor", "蒸汽压力", "软测量")},
    "unknown_scene": {"name": "未知场景", "family": "未知场景", "aliases": ("unknown_scene", "未知场景")},
}


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    name: str
    category: str
    description: str
    triggers: tuple[str, ...]
    depends_on: tuple[str, ...] = ()
    handler: str = "evidence"
    version: str = "1.0.0"
    supported_scenarios: tuple[str, ...] = SUPPORTED_SCENARIOS
    task_types: tuple[str, ...] = ()
    workflow_scope: str = "workflow"
    scope: str = "PROJECT"
    references: tuple[str, ...] = ()
    related_references: tuple[str, ...] = ()
    overlaps_with: tuple[str, ...] = ()
    duplicate_of: str | None = None
    hardcoded_scene_or_field: bool = False
    engineering_only: bool = False

    def public(self) -> dict:
        payload = asdict(self)
        payload["triggers"] = list(self.triggers)
        payload["depends_on"] = list(self.depends_on)
        payload["supported_scenarios"] = list(self.supported_scenarios)
        payload["task_types"] = list(self.task_types)
        payload["references"] = list(self.references)
        payload["related_references"] = list(self.related_references)
        payload["overlaps_with"] = list(self.overlaps_with)
        payload["input_contract"] = [
            "run_id",
            "scenario",
            "equipment_id",
            "dataset_ref",
            "objective",
            "parameters",
            "constraints",
        ]
        payload["output_contract"] = [
            "status",
            "metrics",
            "artifacts",
            "evidence",
            "warnings",
            "suggested_next_skills",
        ]
        return payload


# 分类标签：以最小侵入方式贴元信息，保持原ID与执行图不变。
SKILL_CLASSIFICATION = {
    "industrial_intent_parser": ("ARCHITECTURE",),
    "equipment_entity_resolver": ("SCENE_RECOGNITION", "FIELD_UNIFICATION", "SCENE_REGISTRY", "INDUSTRIAL_ANALYSIS"),
    "constraint_parameter_extractor": ("PIPELINE", "MODELING_GATE", "AGENT"),
    "skill_capability_matcher": ("AGENT", "ARCHITECTURE"),
    "workflow_dag_planner": ("WORKFLOW", "AGENT", "PIPELINE"),
    "execution_supervisor_replanner": ("BUG_DIAGNOSIS", "AGENT", "TESTING"),

    "csv_asset_manager": ("DATA_ASSET", "PIPELINE", "TESTING"),
    "industrial_simulation_generator": ("DATA_CLEANING", "WORKFLOW"),
    "dataset_scenario_profiler": ("SCENE_RECOGNITION", "FIELD_UNIFICATION", "SCENE_REGISTRY"),
    "semantic_field_unit_standardizer": ("FIELD_UNIFICATION", "DATA_CLEANING", "SCENE_REGISTRY"),
    "time_axis_alignment_resampler": ("DATA_CLEANING", "PIPELINE"),
    "missing_anomaly_cleaner": ("DATA_CLEANING", "PIPELINE"),

    "steady_transient_state_detector": ("INDUSTRIAL_ANALYSIS", "PIPELINE"),
    "signal_noise_ratio_estimator": ("INDUSTRIAL_ANALYSIS", "DATA_CLEANING"),
    "high_snr_dynamic_segment_extractor": ("INDUSTRIAL_ANALYSIS", "PIPELINE"),
    "segment_quality_scorer_ranker": ("INDUSTRIAL_ANALYSIS", "PIPELINE"),
    "time_delay_estimator_compensator": ("INDUSTRIAL_ANALYSIS", "MODELING_GATE"),
    "collinearity_detector_reducer": ("INDUSTRIAL_ANALYSIS", "MODELING_GATE"),

    "modeling_dataset_assembler": ("MODELING_GATE", "PIPELINE", "INDUSTRIAL_ANALYSIS"),
    "arx_structure_order_selector": ("MODELING_GATE", "INDUSTRIAL_ANALYSIS"),
    "system_identification_trainer": ("MODELING_GATE", "INDUSTRIAL_ANALYSIS"),
    "multi_model_benchmark": ("MODELING_GATE", "INDUSTRIAL_ANALYSIS", "TESTING"),
    "model_diagnostics_evaluator": ("MODELING_GATE", "INDUSTRIAL_ANALYSIS", "BUG_DIAGNOSIS"),
    "closed_loop_preprocessing_optimizer": ("MODELING_GATE", "TESTING", "INDUSTRIAL_ANALYSIS"),

    "engineering_result_interpreter": ("TESTING", "BUG_DIAGNOSIS"),
    "engineering_visualization_builder": ("TESTING", "FRONTEND_PAGE"),
    "expert_report_writer": ("TESTING", "BUG_DIAGNOSIS"),
    "final_artifact_exporter": ("TESTING", "FRONTEND_PAGE"),
    "experiment_tracker_comparator": ("TESTING", "PAGE_SCENE_MAPPING", "ARCHITECTURE"),
    "evidence_audit_reproducer": ("TESTING", "BUG_DIAGNOSIS"),
}


# 统一分类配置函数，避免重复传参。
def _s(
    skill_id,
    name,
    category,
    description,
    triggers,
    depends_on=(),
    handler="evidence",
    task_types: tuple[str, ...] | None = None,
    scope: str = "PROJECT",
    workflow_scope: str = "workflow",
    references: tuple[str, ...] = (),
    related_references: tuple[str, ...] = (),
    overlaps_with: tuple[str, ...] = (),
    hardcoded_scene_or_field: bool = False,
    engineering_only: bool = False,
    duplicate_of: str | None = None,
):
    if task_types is None:
        task_types = SKILL_CLASSIFICATION.get(skill_id, ())
    return SkillDefinition(
        skill_id,
        name,
        category,
        description,
        tuple(triggers),
        tuple(depends_on),
        handler,
        task_types=tuple(task_types),
        scope=scope,
        workflow_scope=workflow_scope,
        references=references or WORK_REPAIR_MODULE_REFERENCES,
        related_references=related_references,
        overlaps_with=overlaps_with,
        hardcoded_scene_or_field=hardcoded_scene_or_field,
        engineering_only=engineering_only,
        duplicate_of=duplicate_of,
    )


SKILLS = [
    _s("industrial_intent_parser", "工业意图解析", "orchestration", "识别分析、执行、解释与交付目标。", ["分析", "提取", "筛选", "建模", "优化", "报告", "为什么"], (), handler="intent", task_types=("ARCHITECTURE",)),
    _s("equipment_entity_resolver", "设备实体解析", "orchestration", "识别钢铁高炉、炼油脱丁烷精馏塔和工业干燥器及设备编号。", ["号塔", "号炉", "号干燥器", "高炉", "铁水", "精馏塔", "脱丁烷塔", "干燥器", "干燥机", "烘干机"], ["industrial_intent_parser"], "entity", hardcoded_scene_or_field=True),
    _s("constraint_parameter_extractor", "约束参数提取", "orchestration", "抽取采样周期、阈值、时滞与模型阶次。", ["秒", "阈值", "时滞", "阶次", "top_k", "max_lag"], ["industrial_intent_parser"], "parameter"),
    _s("skill_capability_matcher", "Skill 能力匹配", "orchestration", "将用户目标映射到能力集合。", ["*"], ["industrial_intent_parser"], "matcher", task_types=("AGENT",)),
    _s("workflow_dag_planner", "工作流 DAG 规划", "orchestration", "补齐依赖并生成可执行拓扑顺序。", ["*"], ["skill_capability_matcher"], "planner", task_types=("WORKFLOW", "PIPELINE")),
    _s("execution_supervisor_replanner", "执行监督与重规划", "orchestration", "监测失败、跳过与质量门禁并提出下一步。", ["重新", "重跑", "失败", "继续", "*"], ["workflow_dag_planner"], "supervisor", task_types=("BUG_DIAGNOSIS", "AGENT")),

    _s("csv_asset_manager", "CSV 数据资产管理", "data", "校验、登记并追踪上传的工业 CSV。", ["csv", "上传", "数据集", "文件"], ["workflow_dag_planner"], "asset", task_types=("DATA_CLEANING", "PIPELINE")),
    _s("industrial_simulation_generator", "工业仿真数据生成", "data", "生成含稳态、阶跃、噪声和异常的可下载测试集。", ["仿真", "生成数据", "测试集"], ["workflow_dag_planner"], "simulation", task_types=("DATA_CLEANING", "WORKFLOW"), workflow_scope="workflow", engineering_only=True),
    _s("dataset_scenario_profiler", "数据场景画像", "data", "根据字段组合、单位、范围与采样特征识别钢铁高炉、炼油脱丁烷精馏和工业干燥场景。", ["场景", "画像", "高炉", "铁水", "精馏塔", "脱丁烷塔", "干燥器", "干燥机", "烘干机"], ["csv_asset_manager"], "standardization", task_types=("SCENE_RECOGNITION", "SCENE_REGISTRY", "FIELD_UNIFICATION"), hardcoded_scene_or_field=True),
    _s("semantic_field_unit_standardizer", "语义字段与单位标准化", "data", "完成字段映射、角色识别与单位换算。", ["字段", "单位", "映射", "变量角色", "标准化"], ["dataset_scenario_profiler"], "standardization", task_types=("FIELD_UNIFICATION", "SCENE_REGISTRY", "DATA_CLEANING")),
    _s("time_axis_alignment_resampler", "时间轴对齐与重采样", "data", "检查时间戳并按目标周期对齐。", ["时间", "采样", "对齐", "重采样", "秒"], ["semantic_field_unit_standardizer"], "cleaning", task_types=("DATA_CLEANING", "PIPELINE")),
    _s("missing_anomaly_cleaner", "缺失与异常清洗", "data", "分区内有限前向填充输入；异常与缺失输出保留为空。", ["缺失", "异常", "清洗", "规整", "插值"], ["time_axis_alignment_resampler"], "cleaning", task_types=("DATA_CLEANING", "MODELING_GATE")),

    _s("steady_transient_state_detector", "稳动态工况识别", "selection", "识别稳态、过渡态和有效动态窗口。", ["稳态", "动态", "工况", "非稳态"], ["missing_anomaly_cleaner"], "selection", task_types=("INDUSTRIAL_ANALYSIS", "PIPELINE")),
    _s("signal_noise_ratio_estimator", "信噪比估计", "selection", "以稳健二阶差分估计窗口SNR代理值，记录白噪声假设与未标定边界。", ["信噪比", "snr", "噪声"], ["steady_transient_state_detector"], "selection", task_types=("INDUSTRIAL_ANALYSIS", "DATA_CLEANING")),
    _s("high_snr_dynamic_segment_extractor", "高信噪比动态段提取", "selection", "按动态分及SNR代理阈值筛选训练窗口，保留估计方法与重叠说明。", ["高信噪比", "动态数据", "动态段", "提取"], ["signal_noise_ratio_estimator"], "selection", task_types=("INDUSTRIAL_ANALYSIS", "MODELING_GATE")),
    _s("segment_quality_scorer_ranker", "动态段质量评分排序", "selection", "按响应、完整性、异常率和平滑度综合排序。", ["质量", "评分", "排序", "优质"], ["high_snr_dynamic_segment_extractor"], "selection", task_types=("INDUSTRIAL_ANALYSIS", "PIPELINE")),
    _s("time_delay_estimator_compensator", "时滞估计与补偿", "selection", "通过互相关估计输入输出时滞并对齐。", ["时滞", "延迟", "滞后", "补偿"], ["segment_quality_scorer_ranker"], "lag", task_types=("INDUSTRIAL_ANALYSIS", "MODELING_GATE")),
    _s("collinearity_detector_reducer", "共线性诊断与消减", "selection", "结合相关系数和 VIF 剔除冗余输入。", ["共线", "vif", "冗余", "降维"], ["time_delay_estimator_compensator"], "collinearity", task_types=("INDUSTRIAL_ANALYSIS", "MODELING_GATE")),

    _s("modeling_dataset_assembler", "建模数据集组装", "modeling", "拼接优选窗口并形成可复现训练数据。", ["建模数据", "训练集", "验证集"], ["collinearity_detector_reducer"], "modeling", task_types=("MODELING_GATE", "PIPELINE", "INDUSTRIAL_ANALYSIS")),
    _s("arx_structure_order_selector", "ARX 结构阶次选择", "modeling", "选择输入输出阶次、纯滞后与候选结构。", ["arx", "阶次", "结构"], ["modeling_dataset_assembler"], "modeling", task_types=("MODELING_GATE", "INDUSTRIAL_ANALYSIS")),
    _s("system_identification_trainer", "系统辨识训练", "modeling", "训练多输入单输出动态模型。", ["辨识", "训练", "模型"], ["arx_structure_order_selector"], "modeling", task_types=("MODELING_GATE", "INDUSTRIAL_ANALYSIS")),
    _s("multi_model_benchmark", "多模型基准对比", "modeling", "对候选结构进行一致数据切分下的公平比较。", ["对比", "候选模型", "基准"], ["system_identification_trainer"], "modeling", task_types=("MODELING_GATE", "INDUSTRIAL_ANALYSIS", "TESTING")),
    _s("model_diagnostics_evaluator", "模型诊断评估", "modeling", "计算 R²、RMSE、MAE、残差与稳定性指标。", ["r2", "r²", "rmse", "mae", "残差", "可靠"], ["multi_model_benchmark"], "modeling", task_types=("MODELING_GATE", "INDUSTRIAL_ANALYSIS", "BUG_DIAGNOSIS")),
    _s("closed_loop_preprocessing_optimizer", "闭环预处理寻优", "modeling", "以共同验证集反馈调整窗口数量与时滞上限，最终独立测试一次。", ["寻优", "优化", "闭环", "最优", "轮次"], ["model_diagnostics_evaluator"], "optimization", task_types=("MODELING_GATE", "TESTING", "INDUSTRIAL_ANALYSIS")),

    _s("engineering_result_interpreter", "工程结果解释", "delivery", "按场景把算法指标转成工艺语言，并分别给出离线、软测量候选和闭环候选准入结论。", ["解释", "为什么", "结论", "问题", "软测量", "上线", "闭环控制"], ["model_diagnostics_evaluator"], "review", task_types=("TESTING", "BUG_DIAGNOSIS"), workflow_scope="delivery"),
    _s("engineering_visualization_builder", "工程可视化生成", "delivery", "组织趋势、残差、频响和寻优过程可视化。", ["图", "可视化", "趋势", "频率", "伯德"], ["engineering_result_interpreter"], "report", task_types=("TESTING", "FRONTEND_PAGE"), workflow_scope="delivery"),
    _s("expert_report_writer", "专家报告撰写", "delivery", "生成包含方法、证据、结论与边界的报告。", ["报告", "总结", "评审"], ["engineering_result_interpreter"], "report", task_types=("TESTING", "BUG_DIAGNOSIS"), workflow_scope="delivery"),
    _s("final_artifact_exporter", "最终产物导出", "delivery", "汇总 CSV、JSON、模型指标和报告下载入口。", ["导出", "下载", "产物", "交付"], ["expert_report_writer"], "artifact", task_types=("TESTING", "FRONTEND_PAGE"), workflow_scope="delivery"),
    _s("experiment_tracker_comparator", "实验追踪与版本对比", "delivery", "追踪历史运行并比较参数与指标。", ["实验", "历史", "版本", "对比"], ["model_diagnostics_evaluator"], "experiment", task_types=("TESTING", "PAGE_SCENE_MAPPING", "ARCHITECTURE"), workflow_scope="delivery"),
    _s("evidence_audit_reproducer", "证据审计与复现", "delivery", "固化输入、参数、事件和产物证据链。", ["审计", "复现", "证据", "追溯", "*"], ["execution_supervisor_replanner"], "audit", task_types=("TESTING", "BUG_DIAGNOSIS"), workflow_scope="delivery", references=("core/agent_api.py", "core/agent_chat.py", "core/skills/runtime.py")),
]


CATEGORIES = [
    {"id": "orchestration", "name": "理解与编排", "color": "#3b82f6"},
    {"id": "data", "name": "数据接入与治理", "color": "#06b6d4"},
    {"id": "selection", "name": "动态优选与解耦", "color": "#8b5cf6"},
    {"id": "modeling", "name": "辨识建模与寻优", "color": "#f59e0b"},
    {"id": "delivery", "name": "交付与审计", "color": "#10b981"},
]


SKILL_MAP = {skill.id: skill for skill in SKILLS}


def scenario_aliases() -> dict[str, Any]:
    """返回兼容路由层可读的场景信息，不更改现网场景执行集。"""
    payload = {key: dict(value) for key, value in SCENARIO_LIBRARY.items()}
    payload.update({key: {"id": key, **value} for key, value in EXTENDED_SCENE_HINTS.items()})
    return payload


def _normalize(value: str) -> str:
    return (value or "").lower().replace(" ", "")


def identify_scene_from_text(message: str, equipment_id: str | None = None) -> tuple[str | None, str | None, str | None]:
    normalized = _normalize(message)
    for scene_id, config in SCENARIO_LIBRARY.items():
        aliases = tuple(_normalize(item) for item in config["aliases"] + config["aliases_pattern"])
        for alias in aliases:
            if alias and alias in normalized:
                label = config["name"]
                return scene_id, label, config["family"]
    for scene_id, config in EXTENDED_SCENE_HINTS.items():
        aliases = tuple(_normalize(item) for item in config["aliases"])
        for alias in aliases:
            if alias and alias in normalized:
                return scene_id, config["name"], config["family"]
    if equipment_id and _normalize(equipment_id).endswith("塔") and not _normalize(equipment_id).endswith("油罐"):
        config = SCENARIO_LIBRARY["debutanizer_column"]
        return config["id"], config["name"], config["family"]
    return None, None, None


def scenario_ids() -> tuple[str, ...]:
    """返回对外兼容的现网场景ID集合。"""
    return SUPPORTED_SCENARIOS


def resolve_scene_family(name_or_id: str | None) -> str | None:
    value = (name_or_id or "").strip()
    if not value:
        return None
    for config in SCENARIO_LIBRARY.values():
        if value == config["id"] or value == config["name"] or value == config["family"]:
            return config["family"]
        if value in config["aliases"]:
            return config["family"]
    return None
