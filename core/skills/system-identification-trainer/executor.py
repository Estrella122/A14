def execute(context, inputs, parameters):
    from core.skills.stage_adapters import train
    return train(context, inputs, parameters)
