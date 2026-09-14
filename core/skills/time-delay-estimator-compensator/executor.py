def execute(context, inputs, parameters):
    import pandas as pd
    from core.skills.core_executors import TimeDelayCapabilityExecutor
    from core.skills.md_adapter import output
    frame = context["resolver"].load_frame("MODELING_DATASET")
    if frame is None or not isinstance(frame.index, pd.DatetimeIndex) or not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        return output(context, {}, [], status="unavailable", warnings=["时滞估计需要已排序且无重复的真实时间轴"])
    result = TimeDelayCapabilityExecutor().execute(context["skill_id"], [context["skill_id"]],
        context["task_spec"], context["data_context"], {**inputs, "parameters": parameters}, context)
    if result["status"] == "blocked":
        result["status"] = "unavailable"
        result["warnings"] += result.get("limitations", [])
    return result
