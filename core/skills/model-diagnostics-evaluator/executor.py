def execute(context, inputs, parameters):
    from core.skills.stage_adapters import diagnose
    return diagnose(context, inputs, parameters)
