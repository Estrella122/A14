"""Bounded real-series plots. No pipeline stages are rerun to make a chart."""
from html import escape
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd

MAX_ROWS = 200_000
MAX_POINTS = 500


def render_svg(title, series, unit='', x_label='原始采样序号'):
    finite = [float(v) for _, values in series for v in values if pd.notna(v) and math.isfinite(float(v))]
    if not finite:
        return None
    low, high = min(finite), max(finite)
    span = high - low or max(abs(low) * .1, 1)
    if high == low:
        low -= span / 2
    size = max(len(values) for _, values in series)
    indices = np.unique(np.linspace(0, size - 1, min(size, MAX_POINTS), dtype=int))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 400" role="img">',
           '<rect width="900" height="400" fill="#fff"/>',
           f'<title>{escape(title)}</title><text x="70" y="30" font-family="sans-serif" font-size="18">{escape(title)}</text>',
           f'<text x="70" y="53" font-family="sans-serif" font-size="12" fill="#596b60">{escape(unit or "单位未提供")}</text>']
    for i in range(5):
        y = 75 + i * 62.5
        value = low + span * (1 - i / 4)
        svg += [f'<path d="M70 {y}H865" stroke="#e5eae6"/>', f'<text x="64" y="{y + 4}" text-anchor="end" font-family="sans-serif" font-size="11">{value:.3g}</text>']
    for n, (name, values) in enumerate(series):
        color = ['#287652', '#3969bf'][n % 2]
        previous = None
        for idx in indices:
            value = values[idx] if idx < len(values) else None
            valid = value is not None and pd.notna(value) and math.isfinite(float(value))
            x = 70 + int(idx) * 795 / max(size - 1, 1)
            y = 325 - (float(value) - low) * 250 / span if valid else 0
            if valid:
                # Do not bridge missing samples even when they were skipped by sampling.
                gap = previous is None or not np.isfinite(np.asarray(values[previous[0]:idx + 1], dtype=float)).all()
                if not gap:
                    svg.append(f'<path d="M{previous[1]:.2f} {previous[2]:.2f}L{x:.2f} {y:.2f}" stroke="{color}" stroke-width="1.8" fill="none"/>')
                svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.7" fill="{color}"/>')
                previous = (idx, x, y)
            else:
                previous = None
        svg.append(f'<text x="{90 + n * 260}" y="385" font-family="sans-serif" font-size="12" fill="{color}">{escape(name)}</text>')
    svg += [f'<text x="70" y="347" font-size="12">1</text><text x="865" y="347" text-anchor="end" font-size="12">{size}</text>',
            f'<text x="450" y="364" text-anchor="middle" font-family="sans-serif" font-size="12">{escape(x_label)}</text></svg>']
    return ''.join(svg), len(indices)


def build_charts(snapshot, task, data_context, output_dir, resolve_path):
    text = str(task.get('objective', '')) + str(task.get('user_message', ''))
    # The user message is retained in constraints by Task Understanding.
    text += str(task.get('constraints', {}).get('chart_request', ''))
    charts, warnings = [], []
    output_dir = Path(output_dir) / 'visualization'
    output_dir.mkdir(parents=True, exist_ok=True)

    def add(title, series, source, unit='', axis='原始采样序号'):
        result = render_svg(title, series, unit, axis)
        if result is None:
            warnings.append(f'{title} 没有有效数值，未生成占位图。')
            return
        svg, count = result
        path = output_dir / f'chart_{len(charts) + 1}.svg'
        path.write_text(svg, encoding='utf-8')
        charts.append({'title': title, 'path': str(path), 'source': source, 'unit': unit,
                       'source_rows': max(len(v) for _, v in series), 'point_count': count,
                       'caption': f'来源：{source}；横轴：{axis}。最多展示 {MAX_POINTS} 个原始采样点；缺失值断线，抽样可能遗漏局部极值。'})

    if re.search(r'预测|拟合|残差', text) or (not text and snapshot.get('results', {}).get('modeling', {}).get('prediction_preview')):
        preview = snapshot.get('results', {}).get('modeling', {}).get('prediction_preview', [])
        path = resolve_path(snapshot, 'test_predictions_csv')
        df = pd.read_csv(path, nrows=MAX_ROWS) if path else pd.DataFrame(preview)
        if {'y_true', 'y_pred'}.issubset(df.columns):
            true = pd.to_numeric(df.y_true, errors='coerce').to_numpy()
            pred = pd.to_numeric(df.y_pred, errors='coerce').to_numpy()
            series = [('残差', true - pred)] if '残差' in text else [('真实值', true), ('预测值', pred)]
            add('预测残差' if '残差' in text else '真实值与预测值对比', series, 'test_predictions_csv' if path else 'prediction_preview')
        else:
            warnings.append('缺少真实预测序列，不能生成预测对比图。')
    elif re.search(r'寻优|优化|轮次|得分', text):
        rows = snapshot.get('results', {}).get('optimization', {}).get('iterations', [])
        if rows:
            add('寻优候选得分', [('得分', pd.to_numeric(pd.Series([r.get('score') for r in rows]), errors='coerce').to_numpy())], 'optimization.iterations', 'score', '记录顺序（轮次详见寻优记录）')
        else:
            warnings.append('当前没有寻优轮次记录。')
    else:
        path = resolve_path(snapshot, 'standardized_csv') or resolve_path(snapshot, 'cleaned_csv')
        if path:
            # Inspect a bounded prefix for numeric columns, then load only three columns.
            head = pd.read_csv(path, nrows=1000)
            columns = [c for c in head.select_dtypes(include='number').columns if c.lower() not in {'timestamp', 'time', 'index'}]
            scene = data_context.get('scene_context', {})
            target = scene.get('target_column')
            specified = [c for c in columns if c.lower() in text.lower()]
            if specified:
                columns = specified
            elif target in columns:
                columns = [target] + [c for c in columns if c != target]
            columns = columns[:3]
            if columns:
                df = pd.read_csv(path, usecols=columns, nrows=MAX_ROWS + 1)
                if len(df) > MAX_ROWS:
                    warnings.append(f'数据超过 {MAX_ROWS} 行，本次只展示前 {MAX_ROWS} 行的抽样概览。')
                    df = df.iloc[:MAX_ROWS]
                for column in columns:
                    add(f'{column} · 数据趋势', [(column, pd.to_numeric(df[column], errors='coerce').to_numpy())], path.name, scene.get('units', {}).get(column, ''))
        else:
            warnings.append('当前没有可读取的标准化或清洗数据。')
    return charts, warnings
