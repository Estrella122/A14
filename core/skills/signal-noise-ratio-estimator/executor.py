def execute(context, inputs, parameters):
    from integrations.data_cleaning.src.data_cleaning_agent import DataCleaningSelectionAgent
    from core.skills.md_adapter import output, persist
    report = context["resolver"].load_json("SEGMENTATION_REPORT")
    if report and report.get("artifacts", {}).get("snr_csv") and not parameters.get("columns"):
        import pandas as pd
        from statistics import median
        rows = pd.read_csv(report["artifacts"]["snr_csv"]).where(lambda frame: frame.notna(), None).to_dict("records")
        finite = [row["snr_db"] for row in rows if pd.notna(row.get("snr_db"))]
        metrics = {"per_variable_snr": rows, "summary_snr": median(finite) if finite else None,
                   "estimated_fields": len(finite), "scope": "training_windows", "recomputed": False}
        ref = persist(context, "SNR_ESTIMATES", metrics, "snr_metrics.json")
        return output(context, metrics, [{"method": "reuse segmentation SNR", "source": context["resolver"].resolve("SEGMENTATION_REPORT").public(), "recomputed": False}], artifacts=[ref], status="read")
    frame = context["resolver"].load_frame("CLEANED_TRAIN")
    if frame is None:
        return output(context, {}, [], status="unavailable", warnings=["缺少 CLEANED_TRAIN"])
    scene = context.get("scene_context", {})
    roles = [*scene.get("input_columns", []), scene.get("target_column")]
    numeric = list(frame.select_dtypes(include="number").columns)
    columns = parameters.get("columns") or ([name for name in roles if name in numeric] if any(roles) else numeric)
    if not columns or any(column not in frame for column in columns):
        return output(context, {}, [], status="unavailable", warnings=["没有可估计的数值字段"])
    rows = [{"field": column, **DataCleaningSelectionAgent.snr_details(frame[column], parameters.get("min_valid_samples", 15))} for column in columns]
    valid = sum(row["snr_db"] is not None for row in rows)
    artifact = persist(context, "SNR_ESTIMATES", rows, "snr_metrics.json")
    from statistics import median
    finite = [row["snr_db"] for row in rows if row["snr_db"] is not None]
    result = output(context, {"fields": rows, "per_variable_snr": rows, "summary_snr": median(finite) if finite else None, "estimated_fields": valid, "sample_count": len(frame)},
        [{"method": "robust_second_difference_white_noise_proxy", "assumptions": "白噪声二阶差分代理；非仪表标定", "fields": rows}],
        artifacts=[artifact], status="success" if valid == len(rows) else "partial" if valid else "unavailable",
        warnings=[] if valid == len(rows) else ["常量、样本不足或噪声不可估计的字段保留 null"],
        algorithm="DataCleaningSelectionAgent.snr_details")
    result["findings"] = [f"{row['field']}：SNR {row['snr_db']:.3f} dB" if row['snr_db'] is not None else f"{row['field']}：SNR 不可估计" for row in rows]
    result["limitations"] = ["这是白噪声假设下的代理估计，不是仪表标定值。"]
    return result
