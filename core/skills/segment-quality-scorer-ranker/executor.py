def execute(context, inputs, parameters):
    from core.skills.stage_adapters import rank
    return rank(context, inputs, parameters)
