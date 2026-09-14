def execute(context, inputs, parameters):
    from core.skills.stage_adapters import assemble
    return assemble(context, inputs, parameters)
