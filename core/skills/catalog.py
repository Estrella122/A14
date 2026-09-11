from __future__ import annotations

from dataclasses import asdict, dataclass

SUPPORTED_SCENARIOS = (
    "steel_reheating_furnace", "thermal_power_boiler", "wastewater_aeration",
    "cement_rotary_kiln", "distillation_column", "debutanizer_column", "industrial_dryer",
)


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

    def public(self) -> dict:
        payload = asdict(self)
        payload["triggers"] = list(self.triggers)
        payload["depends_on"] = list(self.depends_on)
        payload["supported_scenarios"] = list(self.supported_scenarios)
        payload.update({
            "status": "ready",
            "input_contract": ["run_id", "scenario", "equipment_id", "dataset_ref", "objective", "parameters", "constraints"],
            "output_contract": ["status", "metrics", "artifacts", "evidence", "warnings", "suggested_next_skills"],
        })
        return payload


CATEGORIES = [
    {"id": "orchestration", "name": "理解与编排", "color": "#3b82f6"},
    {"id": "data", "name": "数据接入与治理", "color": "#06b6d4"},
    {"id": "selection", "name": "动态优选与解耦", "color": "#8b5cf6"},
    {"id": "modeling", "name": "辨识建模与寻优", "color": "#f59e0b"},
    {"id": "delivery", "name": "交付与审计", "color": "#10b981"},
]


def _s(skill_id, name, category, description, triggers, depends_on=(), handler="evidence"):
    return SkillDefinition(skill_id, name, category, description, tuple(triggers), tuple(depends_on), handler)


SKILLS = [
    _s("industrial_intent_parser", "工业意图解析", "orchestration", "识别分析、执行、解释与交付目标。", ["分析", "提取", "筛选", "建模", "优化", "报告", "为什么"], handler="intent"),
    _s("equipment_entity_resolver", "设备实体解析", "orchestration", "识别锅炉、曝气池、回转窑、加热炉、蒸馏塔、脱丁烷塔和工业干燥器及编号。", ["号塔", "号炉", "号池", "号窑", "号干燥器", "锅炉", "曝气池", "回转窑", "加热炉", "精馏塔", "蒸馏塔", "脱丁烷塔", "干燥器", "干燥机", "烘干机", "反应器"], ["industrial_intent_parser"], "entity"),
    _s("constraint_parameter_extractor", "约束参数提取", "orchestration", "抽取采样周期、阈值、时滞与模型阶次。", ["秒", "阈值", "时滞", "阶次", "top_k", "max_lag"], ["industrial_intent_parser"], "parameter"),
    _s("skill_capability_matcher", "Skill 能力匹配", "orchestration", "将用户目标映射到能力集合。", ["*"], ["industrial_intent_parser"], "matcher"),
    _s("workflow_dag_planner", "工作流 DAG 规划", "orchestration", "补齐依赖并生成可执行拓扑顺序。", ["*"], ["skill_capability_matcher"], "planner"),
    _s("execution_supervisor_replanner", "执行监督与重规划", "orchestration", "监测失败、跳过与质量门禁并提出下一步。", ["重新", "重跑", "失败", "继续", "*"], ["workflow_dag_planner"], "supervisor"),

    _s("csv_asset_manager", "CSV 数据资产管理", "data", "校验、登记并追踪上传的工业 CSV。", ["csv", "上传", "数据集", "文件"], ["workflow_dag_planner"], "asset"),
    _s("industrial_simulation_generator", "工业仿真数据生成", "data", "生成含稳态、阶跃、噪声和异常的可下载测试集。", ["仿真", "生成数据", "测试集"], ["workflow_dag_planner"], "simulation"),
    _s("dataset_scenario_profiler", "数据场景画像", "data", "根据字段组合、单位、范围与采样特征识别钢铁、火电、污水、水泥、炼油和工业干燥场景。", ["场景", "画像", "加热炉", "锅炉", "燃煤", "曝气池", "污水", "回转窑", "水泥", "精馏塔", "蒸馏塔", "脱丁烷塔", "干燥器", "干燥机", "烘干机"], ["csv_asset_manager"], "standardization"),
    _s("semantic_field_unit_standardizer", "语义字段与单位标准化", "data", "完成字段映射、角色识别与单位换算。", ["字段", "单位", "映射", "变量角色", "标准化"], ["dataset_scenario_profiler"], "standardization"),
    _s("time_axis_alignment_resampler", "时间轴对齐与重采样", "data", "检查时间戳并按目标周期对齐。", ["时间", "采样", "对齐", "重采样", "秒"], ["semantic_field_unit_standardizer"], "cleaning"),
    _s("missing_anomaly_cleaner", "缺失与异常清洗", "data", "分区内有限前向填充输入；异常与缺失输出保留为空。", ["缺失", "异常", "清洗", "规整", "插值"], ["time_axis_alignment_resampler"], "cleaning"),

    _s("steady_transient_state_detector", "稳动态工况识别", "selection", "识别稳态、过渡态和有效动态窗口。", ["稳态", "动态", "工况", "非稳态"], ["missing_anomaly_cleaner"], "selection"),
    _s("signal_noise_ratio_estimator", "信噪比估计", "selection", "以稳健二阶差分估计窗口SNR代理值，记录白噪声假设与未标定边界。", ["信噪比", "snr", "噪声"], ["steady_transient_state_detector"], "selection"),
    _s("high_snr_dynamic_segment_extractor", "高信噪比动态段提取", "selection", "按动态分及SNR代理阈值筛选训练窗口，保留估计方法与重叠说明。", ["高信噪比", "动态数据", "动态段", "提取"], ["signal_noise_ratio_estimator"], "selection"),
    _s("segment_quality_scorer_ranker", "动态段质量评分排序", "selection", "按响应、完整性、异常率和平滑度综合排序。", ["质量", "评分", "排序", "优质"], ["high_snr_dynamic_segment_extractor"], "selection"),
    _s("time_delay_estimator_compensator", "时滞估计与补偿", "selection", "通过互相关估计输入输出时滞并对齐。", ["时滞", "延迟", "滞后", "补偿"], ["segment_quality_scorer_ranker"], "lag"),
    _s("collinearity_detector_reducer", "共线性诊断与消减", "selection", "结合相关系数和 VIF 剔除冗余输入。", ["共线", "vif", "冗余", "降维"], ["time_delay_estimator_compensator"], "collinearity"),

    _s("modeling_dataset_assembler", "建模数据集组装", "modeling", "拼接优选窗口并形成可复现训练数据。", ["建模数据", "训练集", "验证集"], ["collinearity_detector_reducer"], "modeling"),
    _s("arx_structure_order_selector", "ARX 结构阶次选择", "modeling", "选择输入输出阶次、纯滞后与候选结构。", ["arx", "阶次", "结构"], ["modeling_dataset_assembler"], "modeling"),
    _s("system_identification_trainer", "系统辨识训练", "modeling", "训练多输入单输出动态模型。", ["辨识", "训练", "模型"], ["arx_structure_order_selector"], "modeling"),
    _s("multi_model_benchmark", "多模型基准对比", "modeling", "对候选结构进行一致数据切分下的公平比较。", ["对比", "候选模型", "基准"], ["system_identification_trainer"], "modeling"),
    _s("model_diagnostics_evaluator", "模型诊断评估", "modeling", "计算 R²、RMSE、MAE、残差与稳定性指标。", ["r2", "r²", "rmse", "mae", "残差", "可靠"], ["multi_model_benchmark"], "modeling"),
    _s("closed_loop_preprocessing_optimizer", "闭环预处理寻优", "modeling", "以共同验证集反馈调整窗口数量与时滞上限，最终独立测试一次。", ["寻优", "优化", "闭环", "最优", "轮次"], ["model_diagnostics_evaluator"], "optimization"),

    _s("engineering_result_interpreter", "工程结果解释", "delivery", "按场景把算法指标转成工艺语言，并分别给出离线、软测量候选和闭环候选准入结论。", ["解释", "为什么", "结论", "问题", "软测量", "上线", "闭环控制"], ["model_diagnostics_evaluator"], "review"),
    _s("engineering_visualization_builder", "工程可视化生成", "delivery", "组织趋势、残差、频响和寻优过程可视化。", ["图", "可视化", "趋势", "频率", "伯德"], ["engineering_result_interpreter"], "report"),
    _s("expert_report_writer", "专家报告撰写", "delivery", "生成包含方法、证据、结论与边界的报告。", ["报告", "总结", "评审"], ["engineering_result_interpreter"], "report"),
    _s("final_artifact_exporter", "最终产物导出", "delivery", "汇总 CSV、JSON、模型指标和报告下载入口。", ["导出", "下载", "产物", "交付"], ["expert_report_writer"], "artifact"),
    _s("experiment_tracker_comparator", "实验追踪与版本对比", "delivery", "追踪历史运行并比较参数与指标。", ["实验", "历史", "版本", "对比"], ["model_diagnostics_evaluator"], "experiment"),
    _s("evidence_audit_reproducer", "证据审计与复现", "delivery", "固化输入、参数、事件和产物证据链。", ["审计", "复现", "证据", "追溯", "*"], ["execution_supervisor_replanner"], "audit"),
]

SKILL_MAP = {skill.id: skill for skill in SKILLS}
