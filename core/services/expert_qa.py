from __future__ import annotations

import csv
import re
from statistics import median
from typing import Any

from core.skills.answer_intent import resolve_answer_intent


EXPERT_TOPICS = [
    {"key": "sampling", "name": "采样与混叠", "terms": ("采样周期", "采样频率", "奈奎斯特频率", "混叠", "aliasing")},
    {"key": "snr", "name": "信噪比与动态段", "terms": ("信噪比", "噪声比", "snr", "噪声水平")},
    {"key": "excitation", "name": "持续激励与可辨识性", "terms": ("持续激励", "激励充分", "可辨识", "阶跃激励", "输入激励")},
    {"key": "degraded_modeling", "name": "候选段降级建模", "terms": ("候选段降级", "降级建模", "严格优质动态段", "0个严格", "参数可信度", "候选模型")},
    {"key": "leakage", "name": "时序数据泄漏", "terms": ("数据泄漏", "未来信息", "时间穿越", "泄露")},
    {"key": "residual", "name": "残差诊断", "terms": ("残差", "白噪声", "自相关", "独立性", "正态性")},
    {"key": "stability", "name": "模型稳定性", "terms": ("稳定性", "极点", "单位圆", "发散")},
    {"key": "frequency", "name": "频率与阶跃特性", "terms": ("频率特性", "频响", "伯德", "bode", "奈奎斯特", "nyquist", "阶跃响应", "超调量", "调节时间")},
    {"key": "lag", "name": "时滞估计与物理解释", "terms": ("时滞", "纯滞后", "互相关估计", "负时滞", "延迟")},
    {"key": "collinearity", "name": "共线性与变量保留", "terms": ("共线", "vif", "条件数", "冗余变量", "保留变量")},
    {"key": "causality", "name": "相关性与因果边界", "terms": ("因果", "相关不等于因果", "外生变量")},
    {"key": "generalization", "name": "过拟合与泛化", "terms": ("过拟合", "泛化", "交叉验证", "验证集", "训练集", "测试集", "训练测试", "训练/测试", "验证基线", "持续值基线", "基线对比")},
    {"key": "order", "name": "模型结构与阶次", "terms": ("阶次", "aic", "bic", "参数量", "结构选择")},
    {"key": "optimization", "name": "寻优目标与候选比较", "terms": ("目标函数", "约束", "收敛", "停止条件", "局部最优", "寻优策略", "闭环寻优", "最佳候选", "最优候选", "最优模型", "各轮候选", "候选结果", "数据覆盖率", "综合得分", "目标权重", "权重敏感性", "敏感性分析")},
    {"key": "reproducibility", "name": "实验复现与审计", "terms": ("复现", "随机种子", "审计", "追溯", "版本", "Skill执行证据", "skill执行证据", "Skill证据", "skill证据")},
    {"key": "deployment", "name": "上线安全边界", "terms": ("上线", "投运", "生产使用", "安全边界", "联锁", "验收", "可验收", "评审结论", "是否可靠", "可靠")},
    {"key": "transfer", "name": "跨设备与跨场景迁移", "terms": ("迁移", "泛化到", "其他设备", "其他塔", "其他炉", "跨场景")},
    {"key": "drift", "name": "在线更新与模型漂移", "terms": ("在线学习", "实时更新", "概念漂移", "模型漂移", "漂移监测")},
    {"key": "cleaning", "name": "缺失异常与插值风险", "terms": ("缺失机制", "插值", "线性插值", "异常值", "异常点", "离群点", "鲁棒", "平滑动态")},
    {"key": "standardization", "name": "字段语义与单位校验", "terms": ("单位", "量纲", "字段映射", "语义映射", "字段语义", "变量角色")},
    {"key": "delivery", "name": "产物完整性与交付审计", "terms": ("报告", "产物", "导出", "下载", "证据链")},
]


def coverage_summary() -> list[dict[str, Any]]:
    return [{"key": item["key"], "name": item["name"], "examples": list(item["terms"][:3])} for item in EXPERT_TOPICS]


def _matches(message: str) -> list[str]:
    normalized = message.lower()
    matches = []
    for order, topic in enumerate(EXPERT_TOPICS):
        positions = [normalized.find(term.lower()) for term in topic["terms"] if term.lower() in normalized]
        if positions:
            matches.append((min(positions), order, topic["key"]))
    return [item[2] for item in sorted(matches)]


def _snr_rows(snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    run_id = snapshot.get("run_id")
    if not run_id or not snapshot.get("artifacts", {}).get("snr_csv"):
        return [], None
    try:
        from .pipeline import resolve_artifact
        path, name = resolve_artifact(run_id, "snr_csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = []
            for raw in csv.DictReader(handle):
                try:
                    snr_db = float(raw.get("snr_db", ""))
                except (TypeError, ValueError):
                    continue
                rows.append({**raw, "snr_db": snr_db})
        return rows, name
    except (OSError, ValueError, KeyError):
        return [], None


def _snr_answer(snapshot: dict[str, Any], answer_intent: dict[str, Any]) -> dict[str, Any]:
    results = snapshot.get("results", {})
    cleaning = results.get("cleaning", {})
    snr_meta = cleaning.get("snr", {})
    rows, provenance = _snr_rows(snapshot)
    ranked = sorted(rows, key=lambda row: row["snr_db"], reverse=True)
    values = [row["snr_db"] for row in rows]
    best = ranked[0] if ranked else {}
    kind = answer_intent.get("kind", "INTERPRETATION_QUERY")
    threshold = float(snr_meta.get("threshold_db") or 10)
    method = snr_meta.get("method") or "robust_second_difference_white_noise_proxy"
    method_cn = "稳健二阶差分白噪声代理估计"
    window = f"{best.get('start_time', '—')} 至 {best.get('end_time', '—')}"
    field = best.get("variable") or "—"
    if kind == "VALUE_QUERY":
        if values:
            answer = (f"当前任务保存了 {len(values)} 个有效窗口—字段 SNR："
                      f"中位数 {median(values):.2f} dB，范围 {min(values):.2f}–{max(values):.2f} dB。"
                      f"最高值是 {field} 在 {window} 的 {best['snr_db']:.2f} dB。"
                      "SNR 是分窗估计，因此没有一个能代表整份数据的唯一值。")
        else:
            answer = "当前任务没有可读的窗口级信噪比（SNR）产物，因此不能给出真实数值。"
    elif kind in {"METHOD_QUERY", "FORMULA_QUERY"}:
        answer = (
            f"当前代码实际使用 `{method}`，也就是{method_cn}。"
            "对每个时间窗口先计算二阶差分 Δ²x，再用 "
            "σ̂ = MAD(Δ²x) / (0.67448975 × √6) 估计噪声标准差；"
            "噪声功率 = σ̂²，信号功率 = max(Var(x) − σ̂², 10⁻¹²)，"
            "SNR = 10 log₁₀(信号功率 / 噪声功率)。"
            "这是本工程的实际实现，不是从教科书套用的通用说法。")
    elif kind == "CAUSE_QUERY":
        answer = (f"之所以用{method_cn}，是因为二阶差分能在局部平滑前提下压低慢趋势，"
                  "MAD 又比普通标准差更不容被少量尖峰拉偏。"
                  "它适合在没有仪表标定噪声的情况下做窗口筛选；"
                  f"前提是“{snr_meta.get('assumptions') or '局部信号平滑且噪声近似白噪声'}”。")
    elif kind == "EVIDENCE_QUERY":
        answer = (f"这个 SNR 可用于当前数据的候选窗口排序，但不能当作已标定的仪表信噪比。"
                  f"快照明确记录 calibrated={bool(snr_meta.get('calibrated', False))}，方法是 {method}，"
                  f"当前有 {len(values)} 条可读估计，原始证据来自 {provenance or '未找到 snr_estimates.csv'}。"
                  "有色噪声、快速曲率、量化误差和重叠窗口会降低可靠性，需要仪表噪声标定和阈值敏感性试验才能升级证据。")
    elif kind == "COMPARISON_QUERY":
        if ranked:
            top = "；".join(f"{row.get('variable', '—')} @ {row.get('start_time', '—')}–{row.get('end_time', '—')}: {row['snr_db']:.2f} dB" for row in ranked[:3])
            answer = f"当前 SNR 最高的窗口是 {field} 在 {window}，{best['snr_db']:.2f} dB。排名前 3 条：{top}。"
        else:
            answer = "当前没有可读的 snr_estimates.csv，无法比较哪个时间窗口最高。"
    elif kind == "RECOMMENDATION_QUERY":
        answer = (f"建议保留高于 {threshold:g} dB 的窗口作为候选，再用完整性、异常率、输出响应和重叠去重共同复核。"
                  "下一步应做阈值敏感性对比，并用空载或稳态段估计仪表噪声基线。")
    else:
        answer = (f"SNR 高表示在当前{method_cn}口径下，估计的有效动态方差相对局部噪声更大。"
                  f"本任务用 {threshold:g} dB 作为窗口筛选阈值。"
                  "它不直接说明设备健康、模型可靠或工况正常，这些还要结合语义、时滞、残差和工艺证据。")

    return {
        "topic": "snr", "topics": ["snr"], "topic_name": "信噪比与动态段",
        "answer_intent": answer_intent, "answer": answer,
        "cards": [
            {"label": "回答方式", "value": kind},
            {"label": "有效估计", "value": len(values)},
            {"label": "阈值", "value": f"{threshold:g} dB"},
            {"label": "证据", "value": provenance or "未找到"},
        ],
        "suggestions": {
            "VALUE_QUERY": ["哪个时间段最高", "这个结果可靠吗", "信噪比高说明什么"],
            "METHOD_QUERY": ["为什么这么算", "给出公式", "这个方法的假设是什么"],
            "EVIDENCE_QUERY": ["还缺哪些验证证据", "阈值敏感性怎么做", "查看最高 SNR 窗口"],
        }.get(kind, ["信噪比怎么算", "这个结果可靠吗", "哪个时间段信噪比最高"]),
    }


def answer_expert_question(message: str, snapshot: dict[str, Any], *, answer_intent: dict[str, Any] | None = None,
                           topic_hints: list[str] | None = None) -> dict[str, Any] | None:
    topics = _matches(message)
    if "snr" in (topic_hints or []) and topics in ([], ["deployment"]):
        topics = ["snr"]
    topics = list(dict.fromkeys(topics + list(topic_hints or [])))
    if not topics:
        return None
    answer_intent = answer_intent or resolve_answer_intent(message)
    if topics == ["snr"]:
        return _snr_answer(snapshot, answer_intent)
    results = snapshot.get("results", {})
    cleaning = results.get("cleaning", {})
    modeling = results.get("modeling", {})
    optimization = results.get("optimization", {})
    standardization = results.get("standardization", {})
    test = modeling.get("metrics", {}).get("test", {})
    train = modeling.get("metrics", {}).get("train", {})
    r2 = float(test.get("r2") or 0)
    train_r2 = float(train.get("r2") or 0)
    train_rmse = float(train.get("rmse") or 0)
    test_rmse = float(test.get("rmse") or 0)
    r2_gap = train_r2 - r2
    rmse_ratio = test_rmse / train_rmse if train_rmse > 0 else None
    selected_rows = int(cleaning.get("modeling_row_count") or 0)
    selected_segments = int(cleaning.get("selected_segment_count") or 0)
    cleaning_logs = "\n".join(str(item) for item in cleaning.get("logs") or [])
    sampling_match = re.search(r"按\s*(\d+(?:\.\d+)?)\s*s\s*统一重采样", cleaning_logs, re.IGNORECASE)
    sampling_seconds = float(sampling_match.group(1)) if sampling_match else None
    lags = modeling.get("lags") or []
    strongest_lag = max(lags, key=lambda item: abs(float(item.get("correlation") or 0)), default={})
    lag_input = str(strongest_lag.get("input") or "—").replace("_aligned", "")
    lag_output = str(strongest_lag.get("output") or modeling.get("output_col") or "—").replace("_aligned", "")
    lag_samples = strongest_lag.get("delay_samples", "—")
    lag_correlation = float(strongest_lag.get("correlation") or 0)
    collinearity = modeling.get("collinearity") or {}
    vif_rows = collinearity.get("vif") or []
    max_vif_row = max(vif_rows, key=lambda item: float(item.get("vif") or 0), default={})
    max_vif_name = str(max_vif_row.get("variable") or max_vif_row.get("feature") or "—").replace("_aligned", "")
    max_vif = float(max_vif_row.get("vif") or 0)
    recommendations = collinearity.get("recommendations") or {}
    kept = recommendations.get("keep") or modeling.get("selected_inputs") or []
    dropped = recommendations.get("drop") or []
    kept_text = "、".join(str(item).replace("_aligned", "") for item in kept) or "—"
    dropped_text = "、".join(str(item).replace("_aligned", "") for item in dropped) or "无"
    reason = (recommendations.get("reasons") or [{}])[0]
    pair = reason.get("pair") or recommendations.get("pair") or recommendations.get("highest_pair") or []
    if isinstance(pair, dict):
        pair_left = str(pair.get("left") or pair.get("variable_a") or "—").replace("_aligned", "")
        pair_right = str(pair.get("right") or pair.get("variable_b") or "—").replace("_aligned", "")
    else:
        pair_left = str(pair[0] if len(pair) > 0 else "—").replace("_aligned", "")
        pair_right = str(pair[1] if len(pair) > 1 else "—").replace("_aligned", "")
    pair_correlation = float(reason.get("correlation") or recommendations.get("correlation") or 0)
    if sampling_seconds is not None and isinstance(lag_samples, (int, float)):
        physical_lag = f"；按当前 {sampling_seconds:g} 秒规整周期换算约为 {abs(float(lag_samples) * sampling_seconds):g} 秒"
    else:
        physical_lag = "；当前快照未记录可核验的采样周期，暂不能换算为秒"
    model_config = modeling.get("config") or {}
    output_order = model_config.get("output_order", "—")
    input_order = model_config.get("input_order", "—")
    input_delay = model_config.get("input_delay", "—")
    completed_rounds = [item for item in optimization.get("iterations") or [] if item.get("status") == "completed"]
    scored_rounds = [item for item in completed_rounds if item.get("score") is not None]
    ranked_rounds = sorted(scored_rounds, key=lambda item: float(item.get("score")), reverse=True)
    best_round = optimization.get("best_round")
    best_iteration = next((item for item in completed_rounds if item.get("round") == best_round), ranked_rounds[0] if ranked_rounds else {})
    runner_up = ranked_rounds[1] if len(ranked_rounds) > 1 else {}
    score_margin = (float(best_iteration.get("score") or optimization.get("best_score") or 0) - float(runner_up.get("score"))) if runner_up else None
    best_coverage = float(best_iteration.get("coverage") or optimization.get("best_metrics", {}).get("coverage") or 0)
    dynamic_score = cleaning.get("dimension_scores", {}).get("dynamic")
    anomaly_count = sum(int(value) for value in re.findall(r"检测到\s*(\d+)\s*个异常点", cleaning_logs))
    mapping = standardization.get("mapping") or {}
    required_coverage = mapping.get("required_coverage")
    scenario_name = standardization.get("scenario", {}).get("scenario_name") or "未知场景"
    review_fields = standardization.get("detection", {}).get("selected", {}).get("review_fields")
    decision_status = standardization.get("data_decision", {}).get("status") or "未记录"
    comparison = "；".join(
        f"第{item.get('round')}轮 得分{float(item.get('score') or 0):.3f}/R²={float(item.get('r2') or 0):.3f}/覆盖率{float(item.get('coverage') or 0):.2%}"
        for item in ranked_rounds[:3]
    ) or "暂无可用候选明细"
    lag_answer = (
        f"当前任务共估计 {len(lags)} 组输入—输出时滞；绝对相关最强的是 {lag_input} → {lag_output}，时滞 {lag_samples} 个采样点、相关系数 {lag_correlation:+.3f}{physical_lag}。"
        "这个结果只表示在当前搜索窗内两条序列的相关峰位置。要判断其物理意义，还必须与物料停留时间、测点位置、执行器响应方向和闭环结构核对；零时滞或负时滞应优先排查时间戳错位、反馈耦合与共同扰动。"
        if lags else "当前任务未保存可核验的输入—输出时滞结果，因此不能给出具体采样点数、物理时间或相关系数。应先完成时滞估计，再与工艺停留时间、时钟同步和闭环方向核对。"
    )
    collinearity_answer = (
        f"剔除前诊断的最大 VIF 为 {max_vif:.2f}（{max_vif_name}）。本轮保留变量：{kept_text}；剔除变量：{dropped_text}。最高相关变量对为 {pair_left} / {pair_right}，相关系数 {pair_correlation:+.3f}。"
        "当前规则据此避免把高度同步的变量同时作为独立解释量，但这只是降维，不是因果识别；当前快照没有给出剔除后的 VIF 复算和条件相关结果，仍不能排除共同扰动。"
        if vif_rows else "当前任务未保存 VIF 表和变量剔除依据，不能声称已经消除共线性。需要补充相关矩阵、VIF、保留/剔除清单，并在降维后重新计算 VIF。"
    )
    residual_answer = (
        f"当前测试指标 R²={r2:.3f}、RMSE={test_rmse:.3f}，但拟合度不是充分条件。合格残差应近似零均值、低自相关，并与各输入近似不相关；否则说明仍有未建模动态或外生扰动。当前快照若没有 Ljung–Box 统计量，就只能给出指标层面的初判，不能声称残差已经是白噪声。"
        if test else "当前任务未保存测试集指标或残差统计量，不能判断残差是否为白噪声。至少需要残差均值、ACF、Ljung–Box 和残差—输入互相关。"
    )
    generalization_answer = (
        f"当前训练集 R²={train_r2:.3f}、RMSE={train_rmse:.3f}，测试集 R²={r2:.3f}、RMSE={test_rmse:.3f}；R²下降 {r2_gap:.3f}"
        + (f"，测试 RMSE 是训练集的 {rmse_ratio:.2f} 倍" if rmse_ratio is not None else "")
        + "。这个落差是泛化风险信号，但尚不能单凭一次时间切分断言过拟合；还需滚动窗口验证、未参与寻优的锁定测试集和独立炉次。"
        if train and test else "当前任务没有同时保存训练集与测试集指标，无法量化泛化落差或判断过拟合；需要补齐按时间切分的两组指标、滚动验证和独立炉次。"
    )
    order_answer = (
        f"当前 ARX 结构为输出阶次 na={output_order}、输入阶次 nb={input_order}、输入延迟 nk={input_delay}，共 {int(float(test.get('num_params') or 0))} 个参数；测试集 AIC={float(test.get('aic')):.3f}、BIC={float(test.get('bic')):.3f}。"
        "这些值只能描述当前结构，仍要与相邻阶次的验证误差、AIC/BIC及残差白度共同比较，不能直接选择训练拟合度最高的高阶模型。"
        if model_config and test.get("aic") is not None and test.get("bic") is not None else "当前任务未保存完整的 ARX 阶次配置或 AIC/BIC，无法证明当前结构优于相邻阶次；需要补充候选阶次表、验证误差和残差白度。"
    )
    optimization_answer = (
        f"闭环寻优实际完成 {len(completed_rounds)} 轮候选搜索（{len(completed_rounds)} 组候选策略），目标为“{optimization.get('objective') or 'R²、误差和数据覆盖率的加权综合得分'}”。"
        f"第 {best_round or '—'} 轮得分 {float(optimization.get('best_score') or 0):.3f}、R²={float(best_iteration.get('r2') or optimization.get('best_metrics', {}).get('r2') or 0):.3f}、RMSE={float(best_iteration.get('rmse') or optimization.get('best_metrics', {}).get('rmse') or 0):.3f}、覆盖率 {best_coverage:.2%}，因此按当前目标被选为最佳候选。"
        f"前三名为：{comparison}。" + (f"它仅比次优候选高 {score_margin:.3f} 分；" if score_margin is not None else "当前快照未保存可比较的逐轮得分；")
        + "若优势很小或覆盖率偏低，应报告为“当前权重下暂优”，并做权重敏感性和独立数据复验，而不能称为全局最优。"
        if completed_rounds else "当前任务未保存闭环寻优候选轮次，无法解释最佳候选的选择依据。需要补充目标函数、逐轮参数、R²、误差、覆盖率和综合得分。"
    )
    degraded_modeling_answer = (
        f"当前严格优质动态段为 {selected_segments} 个、动态性得分 {float(dynamic_score):.2f}、降级建模使用 {selected_rows} 行、最佳候选覆盖率 {best_coverage:.2%}。"
        + ("结论是：用候选窗口维持流水线贯通、比较算法方案是合理的，但用它确认模型参数或通过验收不合理。" if selected_segments == 0 else "严格动态段已通过门禁，仍需结合独立验证决定能否验收。")
        + f"当前训练/测试 R² 为 {train_r2:.3f}/{r2:.3f}、RMSE 为 {train_rmse:.3f}/{test_rmse:.3f}。"
        "降级数据可能导致激励不足、选择偏差、参数方差增大、共线变量系数不稳定，以及测试结果对少量窗口过度敏感。要升级为可验收模型，应在安全约束内增加阶跃或PRBS激励，取得多个独立炉次的严格动态段，执行滚动时间验证，并用Bootstrap或重复辨识给出参数置信区间。"
        if dynamic_score is not None and train and test else
        "当前严格动态段、动态性或训练/测试证据不完整，降级结果只能用于流程验证，不能用于参数确认或模型验收。需要补充独立激励、严格动态段、滚动验证和参数置信区间。"
    )
    sampling_answer = (
        f"当前数据按 {sampling_seconds:g} 秒统一规整，共 {cleaning.get('cleaned_row_count', '—')} 行。采样周期是否足够不能只看点数：应与过程主时间常数比较，并保证关注动态约有 10–20 个采样点；当前最强相关峰约 {abs(float(lag_samples) * sampling_seconds):g} 秒，可作为时间尺度线索，但不能代替真实工艺时间常数。当前快照没有采集端抗混叠滤波器参数，因此不能证明不存在混叠。"
        if sampling_seconds is not None and isinstance(lag_samples, (int, float)) else
        f"当前任务规整后 {cleaning.get('cleaned_row_count', '—')} 行，但没有可核验的采样周期与过程主时间常数，无法判断采样是否充分或是否存在混叠。"
    )
    cleaning_answer = (
        f"当前质量评分 {cleaning.get('overall_score', '—')}，清洗日志共标记 {anomaly_count} 个变量级异常点，并采用插值修复。线性插值可能压低局部方差、削弱尖峰并制造过于平滑的响应，从而改变动态评分、互相关和模型误差；因此不能仅凭清洗后 R² 判断处理有效。应保留异常掩码，对比不插值、因果前向插值和鲁棒模型三组结果，并单独报告插值点上的残差。"
        if cleaning else "当前任务未保存清洗统计与异常掩码，无法判断插值是否制造了平滑动态或影响模型指标。"
    )
    standardization_answer = (
        f"当前识别场景为{scenario_name}，必需字段覆盖率 " + (f"{float(required_coverage):.1%}" if required_coverage is not None else "未记录") + f"、待人工复核字段 {review_fields if review_fields is not None else '未记录'} 个，数据决策为 {decision_status}。字段名匹配并不自动证明量纲正确；如果 gas_flow、air_flow 的单位换算或变量角色映射错误，后续时滞、相关系数、VIF和ARX系数都会失去物理解释。进入建模前应核对原始单位、标准单位、换算公式、量程和角色，并把人工确认记录写入审计链。"
        if standardization else "当前任务没有字段映射和单位校验证据，后续时滞、共线性和建模结果不能进行物理解释。"
    )
    delivery_answer = (
        f"当前任务保存 {len(snapshot.get('artifacts') or {})} 类流水线产物，分析报告状态为“{results.get('report', {}).get('summary') or results.get('review', {}).get('conclusion') or '未记录'}”。可下载不等于可复现；正式交付还应为输入CSV、模型、参数和报告生成校验和，并绑定代码版本、依赖版本与审批记录。"
    )
    answers = {
        "sampling": sampling_answer,
        "snr": f"系统不是用单点幅值判断信噪比，而是在滑动窗口内比较有效动态变化与局部噪声尺度，并与完整性、异常率和输出响应联合评分。当前选出 {selected_segments} 个严格优质段、建模使用 {selected_rows} 行。若严格段为 0，说明当前阈值下证据不足，系统只会标记候选兜底，不会宣称它们是高质量动态段。",
        "excitation": f"可辨识性要求输入在目标频段提供足够独立激励，仅有长时间稳态数据并不能保证模型可靠。当前严格动态段 {selected_segments} 个、建模数据 {selected_rows} 行。要形成更强证据，还应检查输入矩阵秩、频谱覆盖和不同 MV 的独立变化；现有快照未保存完整谱矩阵时，Agent 会把它列为待验证项。",
        "degraded_modeling": degraded_modeling_answer,
        "leakage": "当前模型数据按时间顺序切分，避免了随机打乱造成的直接泄漏；但现有流水线在模型切分前完成清洗与插值，仅凭任务快照还不能证明所有插值都没有利用缺口后的未来邻点。要闭合证据，需要记录每个预处理器的拟合时间范围，并在训练段拟合后冻结应用到验证段。",
        "residual": residual_answer,
        "stability": "离散 ARX 模型应把特征多项式根检查在单位圆内，并结合自由运行响应判断是否发散。一步预测表现好不等于闭环可用；还要检查极点裕度、长步预测和工况切换。当前页面提供频率与阶跃响应作为工程解释，但最终上线仍需控制器闭环仿真和安全联锁验证。",
        "frequency": "频率特性由辨识模型计算：Bode 图观察增益和相位随频率变化，Nyquist 图辅助判断稳定裕度，阶跃响应给出上升时间、调节时间和超调量。若当前辨识结果缺少可转换的完整系数，页面会明确使用示例传递函数，示例曲线不能作为当前设备的验收证据。",
        "lag": lag_answer,
        "collinearity": collinearity_answer,
        "causality": "互相关和时滞只能提供时间先后与统计关联，不能单独证明因果。要避免把共同扰动误判成因果，应在共线降维后进一步做条件相关或偏相关、残差—输入互相关，并利用独立激励或自然实验验证方向；还要核对工艺机理、操纵权限、外生扰动和闭环反馈。出现负时滞时应优先检查时钟对齐、反馈耦合和共同扰动，而不是直接解释成输出领先输入。",
        "generalization": generalization_answer,
        "order": order_answer,
        "optimization": optimization_answer,
        "reproducibility": f"每次对话会生成 skill_run_id，记录目标、实体、参数、Skill 拓扑、逐步输入输出和证据引用；流水线任务 {snapshot.get('run_id')} 同时保存中间 CSV、指标、寻优记录和报告。要完全复现还应固定代码版本、依赖版本和随机种子，不能只保存最终模型文件。",
        "deployment": f"当前评审结论是“{results.get('review', {}).get('conclusion', '待评审')}”，它仅代表通过本地演示门禁，不等于可以直接投运。生产上线至少还需独立工况验证、控制器闭环仿真、约束与联锁检查、人工审批、回退策略和在线漂移监测；Agent 不会绕过这些安全环节自动下发控制参数。",
        "transfer": "30 个 Skill 的编排框架可复用于其他塔、炉和反应器，但模型参数不能直接迁移。新设备必须重新完成场景识别、字段/单位映射、变量角色确认、动态数据筛选和独立验证；若数据字典或工艺约束不足，系统应停在待确认状态。",
        "drift": "当前系统以离线任务和版本对比为主，不会在无人审批时自动改写生产模型。可通过输入分布、残差、拟合度和工况占比监测漂移；触发阈值后创建新实验，与基线模型对比并经过评审，再决定是否替换。",
        "cleaning": cleaning_answer,
        "standardization": standardization_answer,
        "delivery": delivery_answer,
    }
    if model_config.get("protocol") == "chronological_60_20_20_v2":
        diagnostic = modeling.get("diagnostics", {})
        td = diagnostic.get("test", {})
        snr = cleaning.get("snr", {})
        answers["snr"] = (
            f"当前训练分区达标窗口 {selected_segments} 个，候选训练数据 {selected_rows} 行。"
            "窗口SNR是稳健二阶差分估计的白噪声代理值，阈值10 dB；信号功率和噪声功率保存在snr_estimates.csv。"
            "该方法假设局部信号平滑且噪声近似白噪声，未做仪表标定，不提供伪造置信等级。"
            "窗口重叠，不能把达标窗口数当作独立激励次数。")
        final_vif = recommendations.get("final_vif") or []
        final_max_vif = max((float(row.get("vif") or 0) for row in final_vif), default=None)
        answers["collinearity"] = (
            f"剔除前最大VIF为{max_vif:.2f}（{max_vif_name}）；保留{kept_text}，剔除{dropped_text}。"
            + (f"保留变量重新计算后的最大VIF为{final_max_vif:.2f}。" if final_max_vif is not None else "当前缺少剔除后VIF复算。")
            + "变量筛选只说明线性冗余降低，不证明因果方向；条件相关和独立激励仍需补充。")
        answers["leakage"] = (
            "本任务采用先分区后清洗的60%/20%/20%时间协议；每区仅有限前向填充输入，异常或缺失输出不填成真值。"
            "时滞、共线性和系数只学习训练数据，所有候选使用相同验证目标哈希；最终选中后仅评估一次测试集。"
            "滞后项按连续段分组，负时滞不进入预测特征。分区和评估目标证据见split_manifest.json与diagnostics.json。")
        answers["cleaning"] = (
            "本任务没有双向插值或居中滤波。输入缺失/异常仅前向填充最多6点，输出缺失/异常保留为空并排除出评估真值。"
            "各分区清洗独立执行，仍需检查异常检测是否误伤真实动态；评估仅适用于保留的有效样本。")
        answers["stability"] = (
            f"当前模型为{model_config.get('family')}，AR极点稳定检查={diagnostic.get('stable_ar_poles')}，"
            f"最大极点模={diagnostic.get('max_pole_magnitude')}。"
            f"独立测试自由仿真：{td.get('free_simulation')}。一步预测好不等于自由运行或闭环可用。")
        answers["residual"] = f"独立测试残差诊断：{td.get('residual')}。已计算ACF，但未完成Ljung–Box显著性检验、残差—输入独立性检验；不能宣称残差为白噪声。"
        answers["generalization"] = generalization_answer + (
            f" 当前最终测试仅执行一次；单步RMSE相较持续值基线改善 {td.get('rmse_improvement_over_persistence_pct')}%。"
            f"10步预测证据：{td.get('multi_step')}。这些指标不能替代跨炉次外部验证。")
        answers["order"] = (
            f"实际比较AR与ARX的1/2/3阶，共{len(modeling.get('order_search', []))}个结构候选，采用共同验证集RMSE选择。"
            f"胜出模型为{model_config.get('family')}，阶次{output_order}；候选训练AIC/BIC与验证误差保存在order_search.json。"
            "AIC/BIC只比较相同训练样本口径；当前仍缺少参数置信区间。")
        answers["optimization"] = (
            f"本任务完成{len(completed_rounds)}轮候选，第{best_round}轮在本次范围内验证综合得分最高。"
            "每轮记录实际训练CSV与行数、时滞请求与有效上限、相同验证目标哈希。覆盖率分母是训练分区，测试不参与选参。"
            f"选中候选参数：{optimization.get('best_parameters')}；验证指标：{optimization.get('best_metrics')}；"
            f"最终测试指标：{test}。这是离线预处理反馈搜索，不是控制器闭环投运。")
        answers["reproducibility"] = "已保存输入与产物SHA-256、代码文件SHA-256、依赖版本和固定时间分区清单；拟合系数与结构搜索表可下载。Skill记录区分规划、流水线取证和缺失证据；取证不代表独立重跑。"
        answers["delivery"] = f"当前交付的是可审计候选结果，评审：{results.get('review', {}).get('conclusion')}；阻断原因：{results.get('review', {}).get('blockers')}。产物可下载不等于模型通过验证。"
    names = {item["key"]: item["name"] for item in EXPERT_TOPICS}
    selected_topics = topics
    if "degraded_modeling" in selected_topics:
        selected_topics = [topic for topic in selected_topics if topic not in {"snr", "excitation", "generalization"}]
    sections = [f"{index}.【{names[topic]}】{answers[topic]}" for index, topic in enumerate(selected_topics, 1)]
    gaps_by_topic = {
        "sampling": "原始采集端抗混叠滤波参数和过程主时间常数基准",
        "snr": "窗口级信号功率、噪声功率及不同阈值下的敏感性结果",
        "excitation": "输入谱矩阵、数值秩和各操纵变量的频段覆盖证据",
        "degraded_modeling": "严格动态段下的重复辨识、参数置信区间和独立炉次验收结果",
        "leakage": "预处理器拟合区间与插值邻点来源记录",
        "residual": "Ljung–Box、残差ACF及残差—输入互相关统计量",
        "generalization": ("未参与调参的锁定测试集、滚动窗口验证和独立炉次" if train else "训练/验证指标差距和未参与调参的锁定测试集"),
        "order": "候选阶次表、AIC/BIC和参数置信区间",
        "deployment": "独立工况、闭环仿真、联锁、回退和人工审批证据",
        "stability": "离散极点、稳定裕度和长步自由运行检验",
        "lag": ("测点/执行器时钟同步记录和工艺停留时间基准" if sampling_seconds is not None else "采样周期、测点/执行器时钟同步记录和工艺停留时间基准"),
        "collinearity": "剔除变量后的 VIF 复算、条件相关或偏相关检验",
        "causality": "独立激励或自然实验，以及残差—输入互相关和闭环方向证据",
        "optimization": "目标权重敏感性、候选得分不确定性和独立数据复验",
        "frequency": "可追溯的模型系数、极点与基于当前模型生成的频响数据",
        "reproducibility": "代码提交版本、依赖锁定文件、随机种子和输入文件校验和",
        "transfer": "目标设备的数据字典、量程、运行窗口和独立验收数据",
        "drift": "漂移基线、报警阈值、监测窗口和模型替换审批记录",
        "cleaning": "异常掩码、插值点残差及不同修复策略的对照实验",
        "standardization": "原始/标准单位、换算公式、量程和人工复核签名",
        "delivery": "输入与产物校验和、代码/依赖版本和审批签名",
    }
    if model_config.get("protocol") == "chronological_60_20_20_v2":
        gaps_by_topic.update({"snr": "仪表噪声标定、有色噪声验证和阈值敏感性试验",
            "leakage": "外部独立批次复验及原始采集时钟核验",
            "order": "参数置信区间与更广结构族对比",
            "cleaning": "异常掩码复核、真实动态误删率与其他因果清洗策略对照"})
    gaps = [gaps_by_topic[topic] for topic in selected_topics if topic in gaps_by_topic]
    answer = answers[selected_topics[0]] if len(selected_topics) == 1 else "这个问题包含多个需要分开核对的专业项：\n\n" + "\n\n".join(sections)
    if gaps:
        answer += "\n\n证据边界：以上是当前任务数据支持的诊断，不等同于因果证明或上线结论；当前证据不足，仍缺少：" + "；".join(gaps) + "。"
    return {
        "topic": selected_topics[0],
        "topics": selected_topics,
        "topic_name": "、".join(names[topic] for topic in selected_topics),
        "answer_intent": answer_intent,
        "answer": answer,
        "cards": [
            {"label": "专业主题", "value": f"{len(selected_topics)} 项"},
            {"label": "当前任务", "value": snapshot.get("run_id")},
            {"label": "当前 R²", "value": f"{r2:.3f}" if test.get("r2") is not None else "未保存"},
            {"label": "证据缺口", "value": len(gaps)},
        ],
        "suggestions": ["当前数据还缺哪些验证证据", "这个结论的适用边界是什么", "给出下一步工程验证建议"],
    }
