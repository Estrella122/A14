export function normalizeExperimentRun(run, index = 0, annotations = {}) {
  const result = run?.results ?? {}
  const model = result.modeling ?? {}
  const metrics = model.metrics?.test ?? {}
  const config = model.config ?? {}
  const preview = (model.prediction_preview ?? []).filter((item) => item.split === 'test')
  const started = run?.created_at ? new Date(run.created_at).getTime() : 0
  const finished = run?.updated_at ? new Date(run.updated_at).getTime() : started
  const id = run?.run_id ?? run?.id ?? `run-${index + 1}`
  return {
    id,
    time: run?.updated_at ? new Date(run.updated_at).toLocaleString('zh-CN', { hour12: false }) : '—',
    dataset: run?.original_name ?? '未记录',
    preprocessing: `${result.cleaning?.config?.resample_rule ?? '—'} / 因果清洗`,
    algorithm: config.family ?? '—',
    order: config.output_order ? `na=${config.output_order}, nb=${config.input_order ?? '—'}, nk=${config.input_delay ?? '—'}` : '—',
    r2: Number.isFinite(Number(metrics.r2)) ? Number(metrics.r2) : null,
    aic: Number.isFinite(Number(metrics.aic)) ? Number(metrics.aic) : null,
    duration: Math.max(0, (finished - started) / 1000),
    status: run?.status ?? 'completed',
    actual: preview.map((item) => Number(item.y_true)).filter(Number.isFinite),
    predicted: preview.map((item) => Number(item.y_pred)).filter(Number.isFinite),
    residuals: preview.map((item) => Number(item.residual)).filter(Number.isFinite),
    tag: annotations[id]?.tag ?? '',
    note: annotations[id]?.note ?? '',
  }
}
