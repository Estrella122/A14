"""Expose only chart files actually recorded by this Skill execution."""
from urllib.parse import quote


def chart_artifacts(payload):
    charts = []
    for result in payload.get('core_skill_execution_results', []):
        if result.get('status') not in {'success', 'partial'}:
            continue
        registered = {item.get('path') if isinstance(item, dict) else item for item in result.get('artifacts', [])}
        for chart in result.get('metrics', {}).get('charts', []):
            if chart.get('path') in registered:
                charts.append(chart)
    return charts


def public_charts(skill_run_id, payload):
    return [{key: chart.get(key) for key in ('title', 'caption', 'source', 'source_rows', 'point_count', 'unit')} | {
        'url': f'/api/agent/skill-runs/{quote(skill_run_id, safe="")}/charts/{index}/',
    } for index, chart in enumerate(chart_artifacts(payload))]
