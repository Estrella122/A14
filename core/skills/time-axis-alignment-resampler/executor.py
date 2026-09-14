def execute(context, inputs, parameters):
    from core.skills.stage_adapters import align
    return align(context, inputs, parameters)
