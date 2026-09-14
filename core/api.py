import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import (
    AgentReview,
    CleaningRecord,
    CollinearityResult,
    DataFile,
    DynamicSegment,
    ExportRecord,
    LagAnalysisResult,
    ModelResult,
    OptimizationRun,
    ScenarioTemplate,
    StandardCheck,
    VariableMapping,
)
from .services.scene_registry import list_scene_configs


MODEL_CONFIG = {
    'scenario-templates': {
        'model': ScenarioTemplate,
        'fields': [
            'scenario_name',
            'industry_type',
            'input_variables',
            'output_variables',
            'controllable_variables',
            'disturbance_variables',
            'quality_variables',
            'modeling_objective',
            'evaluation_metrics',
            'variable_unit_rules',
            'outlier_rules',
            'report_template',
        ],
    },
    'data-files': {
        'model': DataFile,
        'fields': [
            'file_name',
            'scenario_id',
            'row_count',
            'variable_count',
            'time_range',
            'sampling_period',
            'missing_value_ratio',
            'outlier_ratio',
            'file_path',
            'processing_status',
        ],
    },
    'variable-mappings': {
        'model': VariableMapping,
        'fields': [
            'scenario_id',
            'original_field_name',
            'standard_variable_name',
            'variable_role',
            'variable_unit',
            'upper_limit',
            'lower_limit',
            'is_required',
            'description',
        ],
    },
    'standard-checks': {
        'model': StandardCheck,
        'fields': [
            'file_id',
            'check_item',
            'check_result',
            'problem_description',
            'repair_suggestion',
        ],
    },
    'cleaning-records': {
        'model': CleaningRecord,
        'fields': [
            'file_id',
            'missing_value_method',
            'outlier_threshold',
            'resampling_period',
            'before_cleaning_count',
            'after_cleaning_count',
            'missing_value_ratio',
            'outlier_ratio',
            'cleaning_status',
        ],
    },
    'dynamic-segments': {
        'model': DynamicSegment,
        'fields': [
            'file_id',
            'start_time',
            'end_time',
            'dynamic_score',
            'snr_score',
            'integrity_score',
            'abnormal_ratio',
            'overall_score',
            'selected_for_modeling',
        ],
    },
    'lag-analysis-results': {
        'model': LagAnalysisResult,
        'fields': [
            'file_id',
            'input_variable',
            'output_variable',
            'optimal_lag',
            'correlation_score',
            'compensation_method',
        ],
    },
    'collinearity-results': {
        'model': CollinearityResult,
        'fields': [
            'file_id',
            'variable_a',
            'variable_b',
            'correlation_coefficient',
            'collinearity_level',
            'processing_method',
            'is_retained',
        ],
    },
    'model-results': {
        'model': ModelResult,
        'fields': [
            'file_id',
            'model_type',
            'training_data_source',
            'r2',
            'rmse',
            'mae',
            'fitting_degree',
            'model_parameters',
            'model_file_path',
        ],
    },
    'optimization-runs': {
        'model': OptimizationRun,
        'fields': [
            'file_id',
            'round_number',
            'dynamic_segment_threshold',
            'outlier_threshold',
            'collinearity_threshold',
            'lag_search_range',
            'min_segment_length',
            'model_r2',
            'rmse',
            'overall_score',
            'review_result',
        ],
    },
    'agent-reviews': {
        'model': AgentReview,
        'fields': [
            'file_id',
            'execution_agent_output',
            'review_agent_conclusion',
            'data_quality_result',
            'dynamic_segment_validity_result',
            'lag_compensation_result',
            'collinearity_processing_result',
            'model_fitting_result',
            'report_integrity_result',
            'modification_suggestions',
            'is_passed',
        ],
    },
    'export-records': {
        'model': ExportRecord,
        'fields': [
            'file_id',
            'export_type',
            'export_file_name',
            'export_path',
            'export_status',
        ],
    },
}


def api_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})


@require_http_methods(['GET', 'OPTIONS'])
def scene_registry(request):
    return api_response({'ok': True, 'data': list_scene_configs()})


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'请求体不是合法 JSON：{exc}')


def model_to_dict(instance):
    data = {'id': instance.pk}
    for field in instance._meta.fields:
        if field.name == 'id':
            continue
        if field.is_relation:
            data[field.attname] = getattr(instance, field.attname)
            continue
        value = getattr(instance, field.name)
        if hasattr(value, 'isoformat'):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        data[field.name] = value
    return data


def convert_value(model, field_name, value):
    if value in ('', None):
        return None

    try:
        field = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        if field_name.endswith('_id'):
            return int(value)
        raise

    internal_type = field.get_internal_type()
    if internal_type in ('IntegerField', 'PositiveIntegerField', 'BigIntegerField', 'PositiveBigIntegerField'):
        return int(value)
    if internal_type == 'DecimalField':
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f'{field_name} 不是合法数字') from exc
    if internal_type == 'BooleanField':
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('1', 'true', 'yes', 'y', '是')
    if internal_type == 'DateTimeField':
        parsed = parse_datetime(str(value))
        if parsed is None:
            raise ValueError(f'{field_name} 不是合法时间，示例：2026-07-07T08:00:00')
        return parsed
    return value


@require_http_methods(['GET', 'POST', 'OPTIONS'])
def table_collection(request, table_key):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})

    config = MODEL_CONFIG.get(table_key)
    if not config:
        return api_response({'ok': False, 'message': '未知 API 表名'}, status=404)

    model = config['model']

    if request.method == 'GET':
        records = model.objects.order_by('-id')[:100]
        return api_response({
            'ok': True,
            'table': model._meta.db_table,
            'count': model.objects.count(),
            'results': [model_to_dict(record) for record in records],
        })

    try:
        payload = parse_json_body(request)
        values = {}
        missing_fields = []

        for field_name in config['fields']:
            field = None
            required = True
            try:
                lookup_name = field_name[:-3] if field_name.endswith('_id') else field_name
                field = model._meta.get_field(lookup_name)
                required = not field.blank and not field.null and not field.has_default()
            except FieldDoesNotExist:
                required = True

            if field_name not in payload:
                if required:
                    missing_fields.append(field_name)
                continue

            values[field_name] = convert_value(model, field_name, payload[field_name])

        if missing_fields:
            return api_response({
                'ok': False,
                'message': '缺少必填字段',
                'missing_fields': missing_fields,
            }, status=400)

        instance = model.objects.create(**values)
        return api_response({
            'ok': True,
            'message': '新增成功',
            'table': model._meta.db_table,
            'data': model_to_dict(instance),
        }, status=201)
    except (ValueError, TypeError, ValidationError, IntegrityError) as exc:
        return api_response({'ok': False, 'message': str(exc)}, status=400)


@require_http_methods(['GET', 'OPTIONS'])
def api_index(request):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})
    return api_response({
        'ok': True,
        'message': 'APC Agent 工作台数据 API',
        'workflows': {
            'closed_loop_optimization': {
                'create_or_list': '/api/optimization/studies/',
                'detail': '/api/optimization/studies/{id}/',
                'run_next_round': '/api/optimization/studies/{id}/step/',
                'accept_strategy': '/api/optimization/studies/{id}/accept/',
                'export': '/api/optimization/studies/{id}/export/?format=csv|json',
            },
        },
        'endpoints': {
            key: {
                'url': f'/api/{key}/',
                'methods': ['GET', 'POST'],
                'table': config['model']._meta.db_table,
                'fields': config['fields'],
            }
            for key, config in MODEL_CONFIG.items()
        },
    })


@ensure_csrf_cookie
@require_http_methods(['GET'])
def security_session(request):
    return api_response({
        'ok': True,
        'auth_required': bool(getattr(settings, 'PROCESSPILOT_REQUIRE_AUTH', False)),
        'authenticated': bool(request.user.is_authenticated),
        'username': request.user.get_username() if request.user.is_authenticated else None,
        'login_url': '/admin/login/?next=/overview/',
    })
