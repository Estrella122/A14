def execute(context, inputs, parameters):
    from integrations.identification.collinearity import correlation_matrix, compute_vif, recommend_variables
    from core.skills.md_adapter import output, persist
    resolver = context["resolver"]
    frame = resolver.load_frame("DELAY_COMPENSATED_DATA")
    delays = resolver.load_frame("TIME_DELAY_ESTIMATES")
    if frame is None or delays is None or delays.empty:
        return output(context, {}, [], status="unavailable", warnings=["缺少时滞补偿训练数据或时滞证据"])
    target = str(delays.iloc[0]["output"])
    columns = [str(name) + "_aligned" for name in delays["input"]]
    data = frame.dropna(subset=columns + [target])
    if len(data) < 20:
        return output(context, {}, [], status="unavailable", warnings=["时滞对齐后完整训练样本不足 20"])
    from core.services.pipeline import INTEGRATIONS_DIR, _module_path
    with _module_path(INTEGRATIONS_DIR / "identification"):
        from validated_modeling import select_training_variables
        correlation, vif, _, recommendation = select_training_variables(
            frame, columns, target, context["policy_receipt"]["effective_parameters"]["decoupling"])
    metrics = {"recommendation": recommendation, "vif": vif.to_dict("records"), "correlation": correlation.to_dict(), "sample_count": len(data)}
    artifact = persist(context, "COLLINEARITY_REPORT", metrics, "collinearity.json")
    result = output(context, metrics, [{"method": "Pearson and VIF", "training_only": True,
        "output": target, "input_fields": columns, "sample_count": len(data)}], artifacts=[artifact],
        warnings=["剔除为建议，不覆盖原始字段；相关性不证明因果"], algorithm="collinearity.recommend_variables + compute_vif")
    result["findings"] = [f"保留 {len(recommendation['keep'])} 个输入，建议剔除 {len(recommendation['drop'])} 个输入。"]
    return result
