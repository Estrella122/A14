from core.skills.core_executors import VisualizationExecutor
from core.skills.md_adapter import output, persist


def execute(context, inputs, parameters):
    result = VisualizationExecutor().execute('visualization', [context['skill_id']], context['task_spec'],
        context['data_context'], inputs, context)
    if result['status'] != 'success':
        return output(context, {}, [], status='unavailable', warnings=result.get('limitations', []))
    charts = result['metrics']['charts']
    ref = persist(context, 'ENGINEERING_PLOTS', {'charts': charts}, 'charts.json')
    refs = [ref]
    for index, chart in enumerate(charts):
        refs.append(context['resolver'].register(f'ENGINEERING_PLOT_{index}', chart['path'], context['skill_id'],
            context['execution_id'], metadata={key: value for key, value in chart.items() if key != 'path'}).public())
    return {**output(context, result['metrics'], result['evidence'], artifacts=refs,
                     warnings=result['warnings'], algorithm='render_real_series'), 'facts': result['facts']}
