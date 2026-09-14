def execute(context, inputs, parameters):
    from core.skills.stage_adapters import select_segments
    return select_segments(context, inputs, parameters)
