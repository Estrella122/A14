def execute(context, inputs, parameters):
    from core.services.pipeline import INTEGRATIONS_DIR, _module_path
    from core.skills.md_adapter import output, persist
    resolver = context["resolver"]
    train = resolver.load_frame("MODEL_READY_DATASET")
    validation = resolver.load_frame("CLEANED_VALIDATION")
    delays = resolver.load_frame("TIME_DELAY_ESTIMATES")
    collinearity = resolver.load_json("COLLINEARITY_REPORT")
    if train is None or validation is None or delays is None or not collinearity:
        return output(context, {}, [], status="unavailable", warnings=["缺少训练、独立验证或上游诊断产物"])
    train, validation = train.reset_index(), validation.reset_index()
    if "timestamp" not in train or "timestamp" not in validation:
        return output(context, {}, [], status="unavailable", warnings=["缺少真实时间轴"])
    if train.timestamp.max() >= validation.timestamp.min():
        return output(context, {}, [], status="unavailable", warnings=["训练与验证时间范围重叠"])
    delay_map = dict(zip(delays["input"], delays["delay_samples"].astype(int)))
    target = str(delays.iloc[0]["output"])
    selected = [name.removesuffix("_aligned") for name in collinearity["recommendation"]["keep"]]
    seconds = float(train.timestamp.diff().dt.total_seconds().dropna().median())
    guard = max(delay_map.values()) + 3
    with _module_path(INTEGRATIONS_DIR / "identification"):
        from validated_modeling import search_structure_orders
        candidates, fitted = search_structure_orders(train, validation, target, list(delay_map), selected, delay_map, seconds, guard)
    artifact = persist(context, "ARX_ORDER_SEARCH", candidates, "order_search.json")
    if not fitted:
        return output(context, {"order_search": candidates}, [{"selection": "validation BIC", "test_accessed": False}],
            artifacts=[artifact], status="unavailable", warnings=["所有结构候选未通过稳定性及自由仿真门禁"], algorithm="validated_modeling.search_structure_orders")
    _, state, train_metrics, validation_metrics, diagnostics, *_ = min(fitted, key=lambda row: row[3]["bic"])
    metrics = {"family": state["family"], "order": state["order"], "regularization_alpha": state["regularization_alpha"],
               "train": train_metrics, "validation": validation_metrics, "candidate_count": len(candidates),
               "selected_inputs": selected, "selection_criterion": "minimum_validation_bic_with_stability_and_simulation_gate"}
    chosen = next(row for row in candidates if row.get("family") == state["family"] and row.get("order") == state["order"] and row.get("regularization_alpha") == state["regularization_alpha"])
    diagnostics["stable_ar_poles"] = chosen["stable_ar_poles"]
    artifact2 = persist(context, "ARX_SELECTED_STRUCTURE", {"metrics": metrics, "fitted_state": state, "guard_samples": guard, "diagnostics": diagnostics, "validation_end": str(validation.timestamp.max())}, "selected_structure.json")
    result = output(context, metrics, [{"method": "AR/ARX orders 1..3 with ridge candidates", "guard_samples": guard,
        "test_accessed": False, "training_rows": len(train), "validation_rows": len(validation),
        "snr_evidence": resolver.load_json("SNR_ESTIMATES")}], artifacts=[artifact, artifact2],
        warnings=["仅选择结构；不代表模型已通过生产准入"], algorithm="validated_modeling.search_structure_orders")
    result["findings"] = [f"选择 {state['family']} {state['order']} 阶，验证 RMSE={validation_metrics['rmse']:.4g}；比较了 {len(candidates)} 个候选。"]
    return result
