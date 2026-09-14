def execute(context, inputs, parameters):
    from core.skills.stage_adapters import clean
    return clean(context, inputs, parameters)
