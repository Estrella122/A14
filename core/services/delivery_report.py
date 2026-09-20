"""Versioned, self-contained reports over frozen evidence; never runs algorithms."""
import base64
import hashlib
import html
import io
import json
from pathlib import Path
from uuid import uuid4

from .evidence_values import final_result_view, clean_facts


def artifact_manifest(snapshot):
    from .pipeline import RUNS_DIR
    root = (RUNS_DIR / snapshot['run_id']).resolve()
    entries = {}
    for key in set(snapshot.get('artifacts', {})) | {'analysis_report_html', 'modeling_csv', 'optimization_json', 'review_json'}:
        relative = snapshot.get('artifacts', {}).get(key)
        path = (root / relative).resolve() if relative else None
        ready = bool(path and root in path.parents and path.is_file())
        entries[key] = {'state': 'ready' if ready else 'missing' if relative else 'not_generated',
                        'path': relative, 'source_run': snapshot['run_id']}
    optimization = snapshot.get('results', {}).get('optimization', {})
    if optimization and optimization.get('best_round') is None and entries['modeling_csv']['state'] == 'ready':
        entries['modeling_csv'].update(state='partial_not_winner', reason='初始筛选数据；没有合法赢家，不作为最佳数据导出')
    report = snapshot.get('results', {}).get('report', {})
    if report.get('status') in {'generating', 'failed'}:
        entries['analysis_report_html']['state'] = report['status']
    return entries


def _render_report(snapshot):
    from .pipeline import RUNS_DIR, _write_json
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    frozen = final_result_view(snapshot)
    root = (RUNS_DIR / frozen['run_id']).resolve()
    version = uuid4().hex[:12]
    folder = root / '07_delivery' / version
    folder.mkdir(parents=True, exist_ok=True)
    results = frozen.get('results', {})
    manifest = {'source_run': frozen['run_id'], 'winner_round': results.get('optimization', {}).get('best_round'),
                'version': version, 'sources': {}, 'charts': [], 'missing_charts': [], 'numeric_executions': 0}
    def read(key):
        relative = frozen.get('artifacts', {}).get(key)
        path = (root / relative).resolve() if relative else None
        if not path or root not in path.parents or not path.is_file():
            return None
        raw = path.read_bytes()
        manifest['sources'][key] = {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
        return pd.read_csv(io.BytesIO(raw)) if path.suffix == '.csv' else None
    pictures = []
    def chart(name, draw):
        fig, ax = plt.subplots(figsize=(9, 3.5), layout='constrained')
        try:
            if not draw(ax):
                manifest['missing_charts'].append({'chart': name, 'reason': '对应当前运行数据未生成或不足'})
                return
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=110)
            raw = buffer.getvalue()
            filename = name + '.png'
            (folder / filename).write_bytes(raw)
            manifest['charts'].append({'name': name, 'path': filename, 'sha256': hashlib.sha256(raw).hexdigest()})
            pictures.append('<figure><figcaption>' + html.escape(name) + '</figcaption><img alt="' + name + '" src="data:image/png;base64,' + base64.b64encode(raw).decode() + '"></figure>')
        finally:
            plt.close(fig)
    model_data = read('modeling_csv')
    read('source_csv')  # provenance hash of the immutable upload
    source = read('standardized_csv')
    training = read('train_csv')
    cleaned = read('cleaned_csv')
    def comparison(ax):
        if source is None or cleaned is None:
            return False
        columns = [c for c in source.select_dtypes('number') if c in cleaned.select_dtypes('number')]
        if not columns:
            return False
        col = columns[0]
        ax.plot(source[col].to_numpy(), label='before cleaning (standardized units)', alpha=.5)
        ax.plot(cleaned[col].to_numpy(), label='cleaned', alpha=.7)
        ax.set_title(str(col)); ax.legend(); return True
    def correlation(ax):
        if model_data is None:
            return False
        values = model_data.select_dtypes('number').drop(columns=['_segment_id'], errors='ignore')
        if values.shape[1] < 2:
            return False
        values = values.iloc[:, :16]
        ax.imshow(values.corr(), vmin=-1, vmax=1, cmap='coolwarm')
        ax.set_xticks(range(len(values.columns)), values.columns, rotation=70, fontsize=7)
        ax.set_yticks(range(len(values.columns)), values.columns, fontsize=7); return True
    def candidates(ax):
        rows = [r for r in results.get('optimization', {}).get('iterations', []) if r.get('status') == 'completed']
        if not rows:
            return False
        ax.plot([r['round'] for r in rows], [r['score'] for r in rows], marker='o')
        winner = manifest['winner_round']
        if winner is not None: ax.axvline(winner, color='green', linestyle='--', label='winner'); ax.legend()
        ax.set_xlabel('Round'); ax.set_ylabel('Validation objective'); return True
    def selected(ax):
        receipt = results.get('best_selection_receipt', {})
        rows = receipt.get('selected_row_ids')
        if not rows:
            return False
        if training is None or 'timestamp' not in training:
            return False
        columns = list(training.select_dtypes('number').columns)
        if not columns:
            return False
        variable = results.get('modeling', {}).get('fitted_inputs', [None])
        variable = variable[0] if variable and variable[0] in columns else columns[0]
        timestamps = pd.to_datetime(training['timestamp'])
        included = timestamps.isin(pd.to_datetime(rows))
        ax.plot(timestamps, training[variable], color='#9ca3af', linewidth=.8, label='training')
        ax.scatter(timestamps[included], training.loc[included, variable], s=3, color='#12806a', label='winner selection')
        ax.set_title(variable); ax.legend(); return True
    for name, draw in [('cleaning_comparison', comparison), ('selected_dynamic_rows', selected), ('variable_correlation', correlation), ('candidate_scores', candidates)]:
        chart(name, draw)
    sections = []
    for name, value in [('数据来源', {'run_id': frozen['run_id'], 'file': frozen.get('original_name'), 'source_type': frozen.get('source_type', 'upload'), 'status': frozen.get('status')}),
                        ('初始基线策略（胜者覆盖参数见下节）', frozen.get('policy_receipt')), ('胜者生效策略', results.get('best_selection_receipt', {}).get('effective_policy')), ('胜者选择回执', results.get('best_selection_receipt')),
                        ('清洗与分段', results.get('cleaning')), ('实际模型与分区指标', results.get('modeling')),
                        ('候选比较', results.get('optimization')), ('工程限制与下一步', results.get('review'))]:
        sections.append('<h2>' + name + '</h2><pre>' + html.escape(json.dumps(clean_facts(value), ensure_ascii=False, indent=2) if value else '尚未生成对应证据；本次报告未补跑算法。') + '</pre>')
    body = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>A14 工程报告</title><style>body{max-width:1100px;margin:40px auto;font:15px sans-serif;line-height:1.7}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:18px}img{max-width:100%}</style><h1>A14 当前运行工程报告</h1><p>本报告仅使用已保存的当前运行证据。验证集用于选型；测试集仅用于最终评价。未通过工程门禁的结果不可投运。</p>'
    from .optimization_state import readable_stop
    stop = readable_stop(snapshot)
    if stop:
        body = body.replace('A14 当前运行工程报告', 'A14 部分诊断报告').replace('A14 工程报告', 'A14 部分诊断报告')
        body += '<p>' + html.escape(stop) + '</p><p>正式模型评审未执行；本报告不构成生产准入或完整成功验收。</p>'
        manifest['report_scope'] = 'partial_diagnostic'
    body += ''.join(pictures + sections) + '<h2>缺图原因</h2><pre>' + html.escape(json.dumps(manifest['missing_charts'], ensure_ascii=False, indent=2)) + '</pre></html>'
    path = folder / 'analysis_report.html'
    path.write_text(body, encoding='utf-8')
    manifest['report_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(folder / 'manifest.json', manifest)
    import zipfile
    package = folder / 'report_package.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for item in sorted(folder.iterdir()):
            if item != package and item.is_file(): bundle.write(item, item.name)
    snapshot.setdefault('artifacts', {})['report_package_zip'] = str(package.relative_to(root))
    snapshot.setdefault('artifacts', {}).update(analysis_report_html=str(path.relative_to(root)), report_manifest_json=str((folder / 'manifest.json').relative_to(root)))
    snapshot.setdefault('results', {})['report'] = {'status': 'ready', 'source_run': frozen['run_id'], 'version': version, 'path': str(path.relative_to(root)), 'manifest': manifest}
    snapshot['artifact_availability'] = artifact_manifest(snapshot)
    _write_json(root / 'snapshot.json', snapshot)
    return snapshot


import threading
_REPORT_LOCKS = {}
_REPORT_LOCKS_GUARD = threading.Lock()


def generate_report(snapshot):
    from .pipeline import RUNS_DIR, _write_json
    run_id = snapshot['run_id']
    with _REPORT_LOCKS_GUARD:
        lock = _REPORT_LOCKS.setdefault(run_id, threading.Lock())
    if not lock.acquire(blocking=False):
        from .pipeline import PipelineError
        raise PipelineError('当前任务报告正在生成，请稍后刷新。')
    try:
        snapshot.setdefault('results', {})['report'] = {'status': 'generating', 'source_run': run_id}
        _write_json(RUNS_DIR / run_id / 'snapshot.json', snapshot)
        try:
            return _render_report(snapshot)
        except Exception:
            snapshot['results']['report'] = {'status': 'failed', 'source_run': run_id, 'reason': 'report_generation_failed'}
            _write_json(RUNS_DIR / run_id / 'snapshot.json', snapshot)
            raise
    finally:
        lock.release()
