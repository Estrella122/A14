"""Durable search progress and read-only recovery of older per-run evidence."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from time import monotonic
import json


def now():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')


def counts(rows, planned=None):
    evaluated = sum(r.get('status') == 'completed' for r in rows)
    feasible = sum(r.get('status') == 'completed' and r.get('feasible') is True for r in rows)
    groups = {'feasible': feasible, 'infeasible': sum(r.get('status') == 'infeasible' or r.get('status') == 'completed' and r.get('feasible') is not True for r in rows),
              'failed': sum(r.get('status') == 'failed' for r in rows),
              'cancelled': sum(r.get('status') == 'cancelled' for r in rows),
              'timed_out': sum(r.get('status') == 'timed_out' for r in rows),
              'running': sum(r.get('status') == 'running' for r in rows)}
    return {'planned': planned, 'attempted': len(rows), 'evaluated': evaluated, 'fitted': sum(bool(r.get('model_fitted')) or r.get('status') == 'completed' for r in rows), **groups,
            'not_executed': max(0, planned-len(rows)) if planned is not None else None}


class SearchStopped(RuntimeError):
    def __init__(self, outcome, message):
        super().__init__(message)
        self.outcome = outcome


class SearchJournal:
    def __init__(self, run_dir, write, on_progress=None, cancel_check=None, timeout_seconds=300):
        self.run_dir, self.write, self.on_progress = run_dir, write, on_progress
        self.cancel_check, self.deadline = cancel_check, monotonic()+timeout_seconds if timeout_seconds else None
        self.rows = []
        self.report = {'status': 'running', 'execution_status': 'running', 'optimization_outcome': 'searching',
                       'model_quality': 'not_evaluated', 'best_round': None, 'iterations': [], 'test_evaluations': 0,
                       'test_used_for_search': False, 'updated_at': now(), 'progress_events': [],
                       'stopping': {'max_rounds': 16}, 'artifacts': {'optimization_json': '05_optimization/optimization_report.json'}}

    def check(self):
        if self.cancel_check and self.cancel_check():
            raise SearchStopped('cancelled', '任务已取消；此前候选结果已保留。')
        if self.deadline is not None and monotonic() >= self.deadline:
            raise SearchStopped('timed_out', '候选搜索超过执行时限；此前结果已保留。')

    def save(self, event):
        self.report['iterations'] = [{k: v for k, v in row.items() if k != 'model'} for row in self.rows]
        self.report['candidate_counts'] = counts(self.rows, self.report['stopping'].get('max_rounds'))
        self.report['updated_at'] = now()
        self.report['progress_events'].append({'sequence': len(self.report['progress_events'])+1, 'event_type': event,
            'timestamp': self.report['updated_at'], 'round_id': self.rows[-1].get('round_id') if self.rows else None,
            'status': self.report['execution_status'], 'candidate_counts': dict(self.report['candidate_counts'])})
        self.report['available_artifacts'] = self.report['artifacts']
        self.write(self.run_dir/'05_optimization/optimization_report.json', self.report)
        # The report and snapshot/DB are persisted before consumers receive progress.
        if self.on_progress:
            self.on_progress(deepcopy(self.report))

    def start(self, candidate):
        self.check()
        row = {**candidate, 'round_id': f"{self.run_dir.name}:round:{candidate['round']}", 'candidate_index': len(self.rows)+1,
               'requested_parameters': {'top_k': candidate['top_k'], 'max_lag': candidate['max_lag']},
               'effective_parameters': None, 'started_at': now(), 'finished_at': None, 'status': 'running',
               'feasible': None, 'validation_metrics': None, 'reason_code': None, 'reason_message': None, 'artifact_refs': {}}
        self.rows.append(row)
        self.save('candidate_started')
        return row

    def finish(self, row, result):
        row.update(result)
        row['finished_at'] = now()
        row.setdefault('reason_code', None)
        row['reason_message'] = row.get('reason_message') or row.get('rejection_reason')
        self.save('candidate_finished')
        self.check()
        return row

    def stop(self, outcome, message, error=None):
        execution = 'completed' if outcome == 'no_feasible_candidate' else 'blocked' if outcome == 'insufficient_input' else outcome
        self.report.update(status='blocked' if execution in {'completed','blocked'} else execution,
                           execution_status=execution, optimization_outcome=outcome, stop_reason=message,
                           reason=outcome, model_quality='no_qualified_winner', best_round=None)
        self.report['stopping']['stop_reason'] = message
        if error: self.report['error'] = {'type': type(error).__name__, 'message': str(error)}
        for row in self.rows:
            if row['status'] == 'running':
                row.update(status=execution if execution in {'cancelled','timed_out'} else 'failed', finished_at=now(),
                           feasible=False, reason_code=outcome, reason_message=message, error=message)
        self.save('optimization_stopped')


def readable_stop(snapshot):
    optimization = snapshot.get('results', {}).get('optimization') or {}
    if not optimization and (snapshot.get('error') or {}).get('stage') != 'optimization' and snapshot.get('current_stage') != 'optimization':
        return None
    outcome = optimization.get('optimization_outcome')
    if outcome in {None, 'searching', 'qualified_candidate', 'best_available_candidate'} and snapshot.get('status') not in {'failed', 'needs_review', 'cancelled', 'timed_out'}:
        return None
    attempted = optimization.get('candidate_counts', {}).get('attempted')
    reason = optimization.get('stop_reason') or optimization.get('reason_message') or (snapshot.get('error') or {}).get('message') or '历史记录不完整，暂未取得停止原因。'
    reasons = list(dict.fromkeys(row.get('reason_message') or row.get('rejection_reason') or row.get('error') for row in optimization.get('iterations', []) if row.get('reason_message') or row.get('rejection_reason') or row.get('error')))
    detail = (' 已记录原因示例：' + '；'.join(reasons[:3]) + '。') if reasons else ''
    count = f'已尝试{attempted}组候选' if attempted is not None else '候选尝试数暂未取得记录'
    if (snapshot.get('error') or {}).get('stage') not in {None, 'optimization'}:
        return None
    return f"本次在闭环寻优阶段停止：{reason} {count}。{detail}已保留的清洗结果和候选记录可查看；后续正式模型评审未执行。可先查看候选原因和当前约束，明确要求重试时将创建新任务，不覆盖原记录。"


def recover_snapshot(snapshot, runs_dir):
    """Enrich a copy only, never overwrite the original failed run or infer zero."""
    result = deepcopy(snapshot)
    run_id = result.get('run_id', '')
    if not run_id or not run_id.replace('_', '').isalnum(): return result
    optimization = result.get('results', {}).get('optimization')
    if not optimization and (result.get('error') or {}).get('stage') == 'optimization':
        path = (Path(runs_dir)/run_id/'05_optimization/optimization_report.json')
        try:
            optimization = json.loads(path.read_text())
            if not isinstance(optimization, dict) or ('iterations' in optimization and (not isinstance(optimization['iterations'], list) or not all(isinstance(row, dict) for row in optimization['iterations']))):
                raise ValueError('历史候选记录结构不完整')
            optimization['recovered_from'] = '05_optimization/optimization_report.json'
        except (OSError, ValueError):
            optimization = {'optimization_outcome': 'unknown', 'execution_status': 'unknown', 'best_round': None,
                            'candidate_counts': {'attempted': None}, 'stop_reason': (result.get('error') or {}).get('message') or '历史候选记录不完整，暂未取得原因。'}
        result.setdefault('results', {})['optimization'] = optimization
    if optimization:
        if 'candidate_counts' not in optimization:
            optimization['candidate_counts'] = counts(optimization['iterations']) if 'iterations' in optimization else {'attempted': None}
        if optimization.get('reason') == 'no_feasible_candidate':
            optimization.setdefault('execution_status', 'completed')
            optimization.setdefault('optimization_outcome', 'no_feasible_candidate')
            optimization.setdefault('stop_reason', (result.get('error') or {}).get('message') or '搜索已结束，没有满足当前约束的候选。')
        for row in optimization.get('iterations', []):
            row.setdefault('candidate_index', row.get('round'))
            row.setdefault('started_at', None)
            row.setdefault('finished_at', None)
            if row.get('status') == 'completed' and row.get('feasible') is False and not row.get('reason_message'):
                constraints = result.get('policy_receipt', {}).get('effective_parameters', {}).get('optimization', {}).get('constraints', {})
                reasons = []
                for metric, bound, label in [('coverage', 'min_coverage', '训练覆盖率'), ('r2', 'min_r2', '验证 R²')]:
                    if row.get(metric) is not None and constraints.get(bound) is not None and row[metric] < constraints[bound]:
                        reasons.append(f"{label} {row[metric]:g} < {constraints[bound]:g}")
                row['reason_message'] = '；'.join(reasons) or row.get('rejection_reason') or '当前约束未满足；历史未记录细项'
            row.setdefault('reason_message', row.get('error') or row.get('rejection_reason'))
        result.update(execution_status=optimization.get('execution_status', 'unknown'),
                      optimization_outcome=optimization.get('optimization_outcome', 'unknown'))
        if optimization.get('recovered_from'):
            for stage in result.get('stages', []):
                if stage.get('key') == 'optimization' and optimization.get('optimization_outcome') == 'no_feasible_candidate':
                    stage.update(historical_status=stage.get('status'), status='partial', message=optimization.get('stop_reason'))
            result['historical_status'] = result.get('status')
            result.setdefault('artifacts', {})['optimization_json'] = optimization['recovered_from']
        if optimization.get('best_round') is None:
            result.setdefault('artifact_labels', {})['modeling_csv'] = '初始筛选数据（非胜者）'
        model = result.get('results', {}).get('modeling', {})
        if model.get('status') == 'pending_candidate_search':
            fitted = optimization.get('candidate_counts', {}).get('fitted', optimization.get('candidate_counts', {}).get('evaluated'))
            model['status'] = 'fitted_no_winner' if fitted else 'not_fitted' if result.get('status') != 'running' else 'pending_candidate_search'
            for stage in result.get('stages', []):
                if stage['key'] == 'modeling':
                    stage.update(status='partial' if fitted else 'blocked' if result.get('status') != 'running' else 'pending',
                                 message='已有候选拟合结果，但没有合格赢家' if fitted else '准备完成；尚未取得有效拟合产物')
    return result
