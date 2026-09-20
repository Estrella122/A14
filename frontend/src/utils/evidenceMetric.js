export function evidenceMetric(value, digits = 3) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '未计算/指标不可定义'
}
