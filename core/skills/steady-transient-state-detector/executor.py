def execute(context, inputs, parameters):
    from core.skills.stage_adapters import segment
    return segment(context, inputs, parameters)
