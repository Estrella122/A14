import csv
import json
import math
import re
import time
from collections.abc import Mapping
from decimal import Decimal

from django.db import IntegrityError, OperationalError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .api import api_response, parse_json_body
from .models import OptimizationRun, OptimizationStudy
from .services.optimization import (
    DEFAULT_CONSTRAINTS,
    DEFAULT_INITIAL_CANDIDATE,
    DEFAULT_OBJECTIVE_WEIGHTS,
    DEFAULT_SEARCH_SPACE,
    benchmark_snapshot_id,
    evaluate_candidate,
    normalize_candidate,
    normalize_constraints,
    normalize_search_space,
    normalize_weights,
    suggest_candidate,
)


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def iteration_to_dict(run):
    payload = run.candidate_parameters or {}
    params = payload.get('params', {})
    diagnostics = payload.get('diagnostics', {})
    failures = payload.get('constraint_failures', [])
    return {
        'id': run.pk,
        'round': run.round_number,
        'params': params,
        'metrics': {
            'fit': _number(run.model_fit),
            'r2': _number(run.model_r2),
            'rmse': _number(run.rmse),
            'coverage': _number(run.coverage_ratio),
            'cost': _number(run.cost_score),
            'overall_score': _number(run.overall_score),
        },
        'diagnostics': diagnostics,
        'score_components': payload.get('score_components', {}),
        'constraint_checks': payload.get('constraint_checks', {}),
        'constraint_failures': failures,
        'decision': run.review_result,
        'decision_code': payload.get('decision_code', 'unknown'),
        'decision_reason': payload.get('decision_reason', run.review_result),
        'change_summary': payload.get('change_summary', '首轮基线评价'),
        'search_reason': payload.get('search_reason', '建立可比较的基线'),
        'delta_vs_previous': payload.get('delta_vs_previous', {}),
        'candidate_source': payload.get('candidate_source', 'feedback_search'),
        'equivalent_to_round': payload.get('equivalent_to_round'),
        'is_best': run.is_best,
        'duration_ms': run.duration_ms,
        'created_at': run.created_at.isoformat(),
    }


def study_to_dict(study, include_iterations=True):
    iterations = list(study.iterations.order_by('round_number')) if include_iterations else []
    uses_multistep_evaluator = not iterations or any(
        '18 步自由运行' in ((run.candidate_parameters or {}).get('diagnostics', {}).get('evaluator', ''))
        for run in iterations
    )
    best = None
    if study.best_run_id:
        best_run = next((run for run in iterations if run.pk == study.best_run_id), study.best_run)
        best = iteration_to_dict(best_run)
    project_prefix = ''.join(character for character in study.project_code.split('-')[0].upper() if character.isalnum())[:4] or 'APC'
    strategy_version = f'OPT-{project_prefix}-S{study.pk:03d}-R{study.best_run.round_number:02d}' if study.best_run_id else None
    dataset_snapshot = benchmark_snapshot_id(study.project_code, study.random_seed)
    completed = study.status in ('completed', 'accepted')
    return {
        'contract_version': 'clso.study.v2',
        'id': study.pk,
        'project_code': study.project_code,
        'project_name': study.project_name,
        'dataset_mode': study.dataset_mode,
        'dataset_source': '内置加热炉阶跃仿真测试集 v3（可复现）',
        'input_artifact': {
            'artifact_type': study.dataset_mode,
            'snapshot_id': dataset_snapshot,
            'project_code': study.project_code,
            'sampling_period_seconds': 10,
            'variable_roles': {
                'manipulated': ['gas_flow', 'air_flow'],
                'disturbance': ['slab_speed', 'inlet_temperature', 'furnace_pressure'],
                'controlled': ['outlet_temperature'],
            },
            'evaluator': 'ARX(1,1) · 18-step-free-run-v2',
        },
        'evaluation_profile': {
            'dataset_snapshot': dataset_snapshot,
            'validation_method': '分段时序留出 · 18 步自由运行',
            'trust_level': 'simulation_validated',
            'trust_label': '仿真验证级',
            'production_ready': False,
            'production_gate': '接入现场 CSV 并通过多时段、多批次复验后，才可进入生产审批。',
        },
        'algorithm_version': 'CLSO-2.0' if uses_multistep_evaluator else 'CLSO-1.0',
        'is_legacy': not uses_multistep_evaluator,
        'status': study.status,
        'total_rounds': study.total_rounds,
        'current_round': study.current_round,
        'progress': 100 if completed else round(study.current_round / study.total_rounds * 100) if study.total_rounds else 0,
        'round_progress': round(study.current_round / study.total_rounds * 100) if study.total_rounds else 0,
        'run_mode': study.run_mode,
        'stopping': {
            'min_rounds': study.min_rounds,
            'max_rounds': study.total_rounds,
            'patience': study.early_stopping_patience,
            'min_score_improvement': _number(study.min_improvement),
        },
        'no_improvement_rounds': study.no_improvement_rounds,
        'stop_reason': study.stop_reason or ('历史任务达到设定轮次' if completed else ''),
        'early_stopped': study.early_stopped,
        'search_space': study.search_space,
        'objective_weights': study.objective_weights,
        'constraints': study.constraints,
        'initial_candidate': study.initial_candidate,
        'random_seed': study.random_seed,
        'best_iteration': best,
        'accepted_iteration_id': study.accepted_run_id,
        'strategy_version': strategy_version,
        'accepted_strategy': {
            'contract_version': 'clso.accepted-strategy.v1',
            'strategy_version': strategy_version,
            'algorithm_version': 'CLSO-2.0' if uses_multistep_evaluator else 'CLSO-1.0',
            'dataset_snapshot': dataset_snapshot,
            'iteration': best,
            'accepted_at': study.accepted_at.isoformat() if study.accepted_at else None,
        } if study.accepted_run_id and best else None,
        'error_message': study.error_message,
        'started_at': study.started_at.isoformat() if study.started_at else None,
        'finished_at': study.finished_at.isoformat() if study.finished_at else None,
        'accepted_at': study.accepted_at.isoformat() if study.accepted_at else None,
        'created_at': study.created_at.isoformat(),
        'updated_at': study.updated_at.isoformat(),
        'iterations': [iteration_to_dict(run) for run in iterations],
    }


def _get_study(study_id):
    return OptimizationStudy.objects.select_related('best_run', 'accepted_run').get(pk=study_id)


@csrf_exempt
@require_http_methods(['GET', 'POST', 'OPTIONS'])
def study_collection(request):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})

    if request.method == 'GET':
        queryset = OptimizationStudy.objects.select_related('best_run', 'accepted_run')
        project_code = request.GET.get('project_code')
        if project_code:
            queryset = queryset.filter(project_code=project_code)
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        studies = list(queryset[:20])
        return api_response({
            'ok': True,
            'count': queryset.count(),
            'results': [study_to_dict(study) for study in studies],
        })

    try:
        payload = parse_json_body(request)
        if not isinstance(payload, Mapping):
            raise ValueError('请求体必须是 JSON 对象')
        project_code = str(payload.get('project_code', '')).strip()
        project_name = str(payload.get('project_name', '')).strip()
        if not project_code or not project_name:
            raise ValueError('project_code 和 project_name 为必填项')
        if len(project_code) > 120 or '\r' in project_code or '\n' in project_code:
            raise ValueError('project_code 最多 120 个字符且不能包含换行')
        if len(project_name) > 200:
            raise ValueError('project_name 最多 200 个字符')
        dataset_mode = payload.get('dataset_mode', 'synthetic_benchmark')
        if dataset_mode != 'synthetic_benchmark':
            raise ValueError('当前闭环仅支持 synthetic_benchmark；CSV 数据适配将在数据资产接入后启用')
        total_rounds = int(payload.get('total_rounds', 12))
        if total_rounds < 2 or total_rounds > 16:
            raise ValueError('total_rounds 必须在 2 到 16 之间')
        search_space = normalize_search_space(payload.get('search_space') or DEFAULT_SEARCH_SPACE)
        initial_candidate = normalize_candidate(payload.get('initial_candidate') or DEFAULT_INITIAL_CANDIDATE, search_space)
        weights = normalize_weights(payload.get('objective_weights') or DEFAULT_OBJECTIVE_WEIGHTS)
        constraints = normalize_constraints(payload.get('constraints') or DEFAULT_CONSTRAINTS)
        random_seed = int(payload.get('random_seed', 20260731))
        if random_seed < 0 or random_seed > 2_147_483_647:
            raise ValueError('random_seed 超出允许范围')
        run_mode = str(payload.get('run_mode', 'auto_converge'))
        if run_mode not in ('auto_converge', 'fixed'):
            raise ValueError('run_mode 仅支持 auto_converge 或 fixed')
        stopping = payload.get('stopping') or {}
        if not isinstance(stopping, Mapping):
            raise ValueError('stopping 必须是 JSON 对象')
        min_rounds = int(stopping.get('min_rounds', min(8, total_rounds)))
        patience = int(stopping.get('patience', 3))
        min_improvement = float(stopping.get('min_score_improvement', 0.2))
        if min_rounds < 2 or min_rounds > total_rounds:
            raise ValueError('最少轮次必须在 2 与最大轮次之间')
        if patience < 2 or patience > 8:
            raise ValueError('连续无改善轮数必须在 2 到 8 之间')
        if not math.isfinite(min_improvement) or min_improvement <= 0 or min_improvement > 5:
            raise ValueError('最小有效改善必须在 0 到 5 分之间')
        study = OptimizationStudy.objects.create(
            project_code=project_code,
            project_name=project_name,
            dataset_mode=dataset_mode,
            status='ready',
            total_rounds=total_rounds,
            run_mode=run_mode,
            min_rounds=min_rounds,
            early_stopping_patience=patience,
            min_improvement=min_improvement,
            search_space=search_space,
            objective_weights=weights,
            constraints=constraints,
            initial_candidate=initial_candidate,
            random_seed=random_seed,
        )
        return api_response({'ok': True, 'message': '闭环寻优任务已创建', 'data': study_to_dict(study)}, status=201)
    except (TypeError, ValueError, OverflowError) as exc:
        return api_response({'ok': False, 'message': str(exc)}, status=400)


@require_http_methods(['GET', 'OPTIONS'])
def study_detail(request, study_id):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})
    try:
        return api_response({'ok': True, 'data': study_to_dict(_get_study(study_id))})
    except OptimizationStudy.DoesNotExist:
        return api_response({'ok': False, 'message': '寻优任务不存在'}, status=404)


def _is_better(result, previous_best):
    if previous_best is None:
        return True
    new_valid = not result['constraint_failures']
    old_payload = previous_best.candidate_parameters or {}
    old_valid = not old_payload.get('constraint_failures', [])
    if new_valid != old_valid:
        return new_valid
    return result['metrics']['overall_score'] > float(previous_best.overall_score)


def _change_summary(previous_run, candidate):
    if previous_run is None:
        return '使用当前参数建立首轮基线'
    previous = (previous_run.candidate_parameters or {}).get('params', {})
    labels = {
        'dynamic_threshold': '动态阈值',
        'outlier_sigma': '异常阈值',
        'collinearity_threshold': '共线阈值',
        'lag_max_seconds': '时滞上限',
        'min_segment_minutes': '最小段长',
    }
    changes = []
    for key, label in labels.items():
        before = previous.get(key)
        after = candidate.get(key)
        if before == after or before is None:
            continue
        direction = '上调' if float(after) > float(before) else '下调'
        changes.append(f'{label}{direction}')
    return '、'.join(changes) if changes else '围绕当前最优解复核等效参数'


def _search_reason(previous_best):
    if previous_best is None:
        return '建立可比较的初始基线'
    payload = previous_best.candidate_parameters or {}
    failures = payload.get('constraint_failures', [])
    diagnostics = payload.get('diagnostics', {})
    params = payload.get('params', {})
    if '动态覆盖不足' in failures or '有效片段不足' in failures:
        return '上一最优候选的数据覆盖或有效片段不足，优先调整动态筛选范围'
    if '拟合度未达目标' in failures:
        if diagnostics.get('optimal_lag_seconds', 0) >= params.get('lag_max_seconds', 0) - 10:
            return '最优时滞命中搜索边界，扩大时滞范围后重新辨识'
        return '多步仿真 Fit 未达目标，增强异常抑制并局部探索'
    return '所有硬约束已满足，在可行域内围绕当前最优策略精细搜索'


def _delta_vs_previous(previous_run, result):
    if previous_run is None:
        return {}
    previous = iteration_to_dict(previous_run)['metrics']
    current = result['metrics']
    return {
        'fit': round(current['fit'] - previous['fit'], 4),
        'coverage': round(current['coverage'] - previous['coverage'], 4),
        'rmse': round(current['rmse'] - previous['rmse'], 4),
        'cost': round(current['cost'] - previous['cost'], 4),
        'overall_score': round(current['overall_score'] - previous['overall_score'], 4),
    }


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def study_step(request, study_id):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})
    started = time.perf_counter()
    requested_round = None
    try:
        with transaction.atomic():
            study = (
                OptimizationStudy.objects
                .select_for_update()
                .select_related('best_run', 'accepted_run')
                .get(pk=study_id)
            )
            if study.status in ('completed', 'accepted') or study.current_round >= study.total_rounds:
                return api_response({'ok': True, 'message': '寻优任务已完成', 'data': study_to_dict(study)})
            if study.status == 'failed':
                return api_response({'ok': False, 'message': '失败任务不能继续执行，请创建新任务'}, status=409)

            round_number = study.current_round + 1
            requested_round = round_number
            previous_runs = list(study.iterations.order_by('round_number'))
            previous_run = previous_runs[-1] if previous_runs else None
            signatures = {
                (run.candidate_parameters or {}).get('diagnostics', {}).get('effective_signature'): run.round_number
                for run in previous_runs
            }
            signatures.pop(None, None)
            equivalent_to_round = None
            candidate_attempt = 0
            for candidate_attempt in range(6):
                candidate = suggest_candidate(study, round_number, candidate_attempt)
                result = evaluate_candidate(
                    study.project_code,
                    study.random_seed,
                    candidate,
                    study.objective_weights,
                    study.constraints,
                    study.search_space,
                )
                signature = result['diagnostics']['effective_signature']
                equivalent_to_round = signatures.get(signature)
                if equivalent_to_round is None:
                    break
            duration_ms = max(1, round((time.perf_counter() - started) * 1000))
            previous_best = study.best_run
            is_best = _is_better(result, study.best_run)
            previous_best_valid = previous_best is not None and not (previous_best.candidate_parameters or {}).get('constraint_failures', [])
            current_valid = not result['constraint_failures']
            score_improvement = result['metrics']['overall_score'] - float(previous_best.overall_score) if previous_best else result['metrics']['overall_score']
            fit_improvement = result['metrics']['fit'] - float(previous_best.model_fit) if previous_best else result['metrics']['fit']
            meaningful_improvement = previous_best is None or (current_valid and not previous_best_valid) or (
                is_best and (score_improvement >= float(study.min_improvement) or fit_improvement >= 0.003)
            )
            if equivalent_to_round is not None:
                # An effective signature represents the selected samples, cleaning
                # result, lag and feature structure.  A repeated signature is the
                # same modelling evidence and must never replace the original best,
                # even if a parameter-only cost term makes its score look higher.
                is_best = False
                decision_code = 'equivalent'
                decision = '等效候选'
                decision_reason = f'与第 {equivalent_to_round:02d} 轮产生相同有效数据与模型结构，不重复推荐'
                meaningful_improvement = False
            elif result['constraint_failures']:
                decision_code = 'infeasible'
                decision = '约束未通过'
                decision_reason = '；'.join(result['constraint_failures']) + '，不进入可交付候选集'
            elif is_best:
                decision_code = 'new_best'
                decision = '刷新最优'
                decision_reason = '全部硬约束通过，且在可行候选中综合分最高'
            else:
                decision_code = 'not_improved'
                decision = '未改善'
                decision_reason = '硬约束通过，但综合分未超过当前最优策略'

            result.update({
                'candidate_source': 'initial_baseline' if round_number == 1 else 'space_filling' if round_number <= 6 else 'feedback_search',
                'candidate_attempt': candidate_attempt + 1,
                'change_summary': _change_summary(previous_run, candidate),
                'search_reason': _search_reason(previous_best),
                'delta_vs_previous': _delta_vs_previous(previous_run, result),
                'equivalent_to_round': equivalent_to_round,
                'decision_code': decision_code,
                'decision_reason': decision_reason,
                'score_improvement_vs_best': round(score_improvement, 4),
                'fit_improvement_vs_best': round(fit_improvement, 4),
                'meaningful_improvement': meaningful_improvement,
            })

            if is_best and study.best_run_id:
                OptimizationRun.objects.filter(pk=study.best_run_id).update(is_best=False)
            run = OptimizationRun.objects.create(
                study=study,
                round_number=round_number,
                dynamic_segment_threshold=result['params']['dynamic_threshold'],
                outlier_threshold=f"{result['params']['outlier_sigma']:.1f}σ",
                collinearity_threshold=result['params']['collinearity_threshold'],
                lag_search_range=f"0–{result['params']['lag_max_seconds']} s",
                min_segment_length=f"{result['params']['min_segment_minutes']} min",
                model_r2=result['metrics']['r2'],
                model_fit=result['metrics']['fit'],
                rmse=result['metrics']['rmse'],
                coverage_ratio=result['metrics']['coverage'],
                cost_score=result['metrics']['cost'],
                overall_score=result['metrics']['overall_score'],
                review_result=decision,
                candidate_parameters=result,
                is_best=is_best,
                duration_ms=duration_ms,
            )
            study.current_round = round_number
            study.no_improvement_rounds = 0 if meaningful_improvement else study.no_improvement_rounds + 1
            best_after_run = run if is_best else study.best_run
            best_is_valid = bool(best_after_run) and not (best_after_run.candidate_parameters or {}).get('constraint_failures', [])
            reached_limit = round_number >= study.total_rounds
            converged = (
                study.run_mode == 'auto_converge'
                and round_number < study.total_rounds
                and round_number >= study.min_rounds
                and best_is_valid
                and study.no_improvement_rounds >= study.early_stopping_patience
                and not (best_after_run.candidate_parameters or {}).get('diagnostics', {}).get('lag_boundary_hit', False)
            )
            if converged:
                study.status = 'completed'
                study.early_stopped = True
                study.stop_reason = (
                    f'已执行最少 {study.min_rounds} 轮并满足全部硬约束；'
                    f'连续 {study.no_improvement_rounds} 轮综合分改善低于 {float(study.min_improvement):.2f} 分'
                )
            elif reached_limit:
                study.status = 'completed'
                study.early_stopped = False
                study.stop_reason = f'达到最大轮次 {study.total_rounds} 轮'
            else:
                study.status = 'running'
                study.stop_reason = ''
            study.started_at = study.started_at or timezone.now()
            study.finished_at = timezone.now() if study.status == 'completed' else None
            study.error_message = ''
            if is_best:
                study.best_run = run
            study.save()
            return api_response({
                'ok': True,
                'message': f'第 {round_number} 轮真实评价完成',
                'iteration': iteration_to_dict(run),
                'data': study_to_dict(study),
            })
    except OptimizationStudy.DoesNotExist:
        return api_response({'ok': False, 'message': '寻优任务不存在'}, status=404)
    except (OperationalError, IntegrityError):
        # A concurrent step can race on SQLite, where select_for_update does not
        # provide row-level locking.  Treat the conflict as recoverable and never
        # overwrite a successfully advanced task with a failed status.
        current = None
        for _ in range(3):
            try:
                current = _get_study(study_id)
                break
            except OperationalError:
                time.sleep(0.02)
            except OptimizationStudy.DoesNotExist:
                break
        if current is not None and requested_round is not None and current.current_round >= requested_round:
            return api_response({
                'ok': True,
                'message': f'第 {requested_round} 轮已由并发请求完成',
                'data': study_to_dict(current),
            })
        return api_response({
            'ok': False,
            'message': '当前轮正在执行，请稍后继续',
            'data': study_to_dict(current) if current is not None else None,
        }, status=409)
    except Exception as exc:  # Keep the task recoverable and expose a concise error to the UI.
        OptimizationStudy.objects.filter(pk=study_id).update(status='failed', error_message=str(exc), finished_at=timezone.now())
        return api_response({'ok': False, 'message': f'本轮计算失败：{exc}'}, status=500)


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def study_accept(request, study_id):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})
    try:
        with transaction.atomic():
            study = OptimizationStudy.objects.select_for_update().select_related('best_run').get(pk=study_id)
            if not study.best_run_id:
                return api_response({'ok': False, 'message': '任务尚无可采纳的策略'}, status=409)
            if study.status not in ('completed', 'accepted'):
                return api_response({'ok': False, 'message': '请等待全部寻优轮次完成'}, status=409)
            failures = (study.best_run.candidate_parameters or {}).get('constraint_failures', [])
            if failures:
                return api_response({
                    'ok': False,
                    'message': f"未找到满足全部硬约束的策略：{'、'.join(failures)}",
                }, status=409)
            study.accepted_run = study.best_run
            study.accepted_at = timezone.now()
            study.status = 'accepted'
            study.save()
            return api_response({
                'ok': True,
                'message': '最优演示策略已固化，可通过标准 JSON 契约交付',
                'data': study_to_dict(study),
            })
    except OptimizationStudy.DoesNotExist:
        return api_response({'ok': False, 'message': '寻优任务不存在'}, status=404)


@require_http_methods(['GET', 'OPTIONS'])
def study_export(request, study_id):
    if request.method == 'OPTIONS':
        return api_response({'ok': True})
    try:
        study = _get_study(study_id)
    except OptimizationStudy.DoesNotExist:
        return api_response({'ok': False, 'message': '寻优任务不存在'}, status=404)

    export_format = request.GET.get('format', 'json').lower()
    safe_project_code = re.sub(r'[^A-Za-z0-9._-]+', '_', study.project_code).strip('._-') or 'project'
    filename = f'{safe_project_code}_optimization_{study.pk}'
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response.write('\ufeff')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            '轮次', '搜索阶段', '本轮改动', '动态阈值', '异常阈值σ', '共线阈值',
            '时滞上限s', '最小段长min', 'Fit', 'R2', 'RMSE', '覆盖率', '成本', '综合分',
            '约束状态', '决策', '决策原因', '有效签名',
        ])
        for run in study.iterations.order_by('round_number'):
            row = iteration_to_dict(run)
            params = row['params']
            metrics = row['metrics']
            writer.writerow([
                row['round'], row['candidate_source'], row['change_summary'],
                params['dynamic_threshold'], params['outlier_sigma'],
                params['collinearity_threshold'], params['lag_max_seconds'],
                params['min_segment_minutes'], metrics['fit'], metrics['r2'],
                metrics['rmse'], metrics['coverage'], metrics['cost'],
                metrics['overall_score'], '全部通过' if not row['constraint_failures'] else '；'.join(row['constraint_failures']),
                row['decision'], row['decision_reason'], row['diagnostics'].get('effective_signature', ''),
            ])
    elif export_format == 'json':
        payload = json.dumps(study_to_dict(study), ensure_ascii=False, indent=2)
        response = HttpResponse(payload, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
    else:
        return api_response({'ok': False, 'message': 'format 仅支持 json 或 csv'}, status=400)

    response['Access-Control-Allow-Origin'] = '*'
    return response
