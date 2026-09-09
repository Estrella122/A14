<script setup>
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { mockTransferFunction } from '../data/mockData'
import { useEChart } from '../composables/useEChart'

const props = defineProps({ model: { type: Object, default: null } })
const bodeChart = ref(null)
const nyquistChart = ref(null)
const stepChart = ref(null)

const transfer = computed(() => {
  const candidate = props.model?.transfer_function
  if (candidate?.numerator?.length && candidate?.denominator?.length === 3) return { ...candidate, label: candidate.label ?? '辨识模型传递函数' }
  // TODO(mock): 当前建模 API 未返回 ARX 系数，暂用二阶对象；后端补充 transfer_function 后自动使用真实模型。
  return mockTransferFunction
})

function responseAt(omega) {
  const [a2, a1, a0] = transfer.value.denominator
  const gain = Number(transfer.value.numerator.at(-1) ?? 1)
  const real = a0 - a2 * omega * omega
  const imaginary = a1 * omega
  const denominator = real * real + imaginary * imaginary
  return { real: gain * real / denominator, imaginary: -gain * imaginary / denominator }
}
const frequencyResponse = computed(() => Array.from({ length: 160 }, (_, index) => {
  const omega = 10 ** (-2 + index / 159 * 4)
  const value = responseAt(omega)
  return { omega, ...value, magnitude: 20 * Math.log10(Math.max(Math.hypot(value.real, value.imaginary), 1e-12)), phase: Math.atan2(value.imaginary, value.real) * 180 / Math.PI }
}))
const stepResponse = computed(() => {
  const [a2, a1, a0] = transfer.value.denominator.map(Number)
  const gain = Number(transfer.value.numerator.at(-1) ?? 1)
  const dt = .02
  let y = 0
  let velocity = 0
  return Array.from({ length: 1001 }, (_, index) => {
    const acceleration = (gain - a1 * velocity - a0 * y) / a2
    velocity += acceleration * dt
    y += velocity * dt
    return [Number((index * dt).toFixed(2)), y]
  })
})
const stepMetrics = computed(() => {
  const rows = stepResponse.value
  const final = Number(transfer.value.numerator.at(-1) ?? 1) / Number(transfer.value.denominator.at(-1) ?? 1)
  const t10 = rows.find(([, value]) => value >= final * .1)?.[0] ?? 0
  const t90 = rows.find(([, value]) => value >= final * .9)?.[0] ?? 0
  const peak = Math.max(...rows.map(([, value]) => value))
  let settling = rows.at(-1)[0]
  for (let index = 0; index < rows.length; index += 1) {
    if (rows.slice(index).every(([, value]) => Math.abs(value - final) <= Math.abs(final) * .02)) { settling = rows[index][0]; break }
  }
  return { rise: Math.max(0, t90 - t10), settling, overshoot: Math.max(0, (peak - final) / Math.max(Math.abs(final), 1e-9) * 100), final }
})
const commonText = { color: '#64748b', fontSize: 10 }
const bodeOption = computed(() => ({
  animationDuration: 500, tooltip: { trigger: 'axis' },
  grid: [{ left: 55, right: 22, top: 28, height: '34%' }, { left: 55, right: 22, top: '57%', height: '31%' }],
  xAxis: [{ type: 'log', gridIndex: 0, min: .01, max: 100, axisLabel: { show: false }, splitLine: { show: true, lineStyle: { color: '#edf2f7' } } }, { type: 'log', gridIndex: 1, min: .01, max: 100, name: '角频率 ω (rad/s)', nameLocation: 'middle', nameGap: 25, axisLabel: commonText, splitLine: { show: true, lineStyle: { color: '#edf2f7' } } }],
  yAxis: [{ type: 'value', gridIndex: 0, name: '幅值 (dB)', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } }, { type: 'value', gridIndex: 1, name: '相位 (°)', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } }],
  series: [{ name: '幅频', type: 'line', xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, data: frequencyResponse.value.map((item) => [item.omega, item.magnitude]), lineStyle: { color: '#2563eb', width: 2 } }, { name: '相频', type: 'line', xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, data: frequencyResponse.value.map((item) => [item.omega, item.phase]), lineStyle: { color: '#8b5cf6', width: 2 } }],
}))
const nyquistOption = computed(() => ({
  animationDuration: 550, tooltip: { trigger: 'item', formatter: ({ value }) => `Re ${Number(value[0]).toFixed(3)}<br>Im ${Number(value[1]).toFixed(3)}` },
  grid: { left: 55, right: 25, top: 25, bottom: 42 }, xAxis: { type: 'value', name: '实部', nameLocation: 'middle', nameGap: 25, scale: true, axisLine: { onZero: true }, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } }, yAxis: { type: 'value', name: '虚部', nameTextStyle: commonText, scale: true, axisLine: { onZero: true }, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  series: [{ type: 'line', showSymbol: false, data: [...frequencyResponse.value.map((item) => [item.real, item.imaginary]), ...frequencyResponse.value.slice().reverse().map((item) => [item.real, -item.imaginary])], lineStyle: { color: '#0f9f72', width: 2 }, markPoint: { data: [{ coord: [-1, 0], name: '-1+j0' }], symbolSize: 26, label: { formatter: '-1', fontSize: 8 }, itemStyle: { color: '#dc2626' } } }],
}))
const stepOption = computed(() => ({
  animationDuration: 550, tooltip: { trigger: 'axis' }, grid: { left: 52, right: 24, top: 26, bottom: 42 },
  xAxis: { type: 'value', name: '时间 (s)', nameLocation: 'middle', nameGap: 27, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } }, yAxis: { type: 'value', name: '输出', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  series: [{ type: 'line', showSymbol: false, data: stepResponse.value, lineStyle: { color: '#f97316', width: 2.2 }, areaStyle: { color: 'rgba(249,115,22,.08)' }, markLine: { symbol: 'none', label: { fontSize: 9 }, lineStyle: { type: 'dashed', color: '#94a3b8' }, data: [{ yAxis: stepMetrics.value.final, name: '稳态值' }, { xAxis: stepMetrics.value.settling, name: '调节时间' }] } }],
}))
useEChart(bodeChart, bodeOption)
useEChart(nyquistChart, nyquistOption)
useEChart(stepChart, stepOption)
</script>

<template>
  <div class="view-stack frequency-analysis">
    <section class="frequency-summary"><div><span><AppIcon name="model" :size="22" /></span><p><small>当前分析对象</small><strong>{{ transfer.label }}</strong></p></div><StatusPill :tone="model?.transfer_function ? 'success' : 'warning'">{{ model?.transfer_function ? '辨识参数' : '二阶示例模型' }}</StatusPill><p>频域分析用于检查带宽、相位滞后与闭环稳定裕度；正式上线仍需结合采样周期和控制器参数复核。</p></section>
    <div class="frequency-grid"><section class="panel bode-panel"><div class="section-heading compact"><div><span class="section-kicker">Frequency Response</span><h2>伯德图</h2></div><StatusPill tone="brand">对数频率</StatusPill></div><div ref="bodeChart" class="frequency-chart tall"></div></section><section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Complex Plane</span><h2>奈奎斯特图</h2></div></div><div ref="nyquistChart" class="frequency-chart tall"></div></section></div>
    <section class="panel step-panel"><div class="section-heading compact"><div><span class="section-kicker">Time-domain Characteristics</span><h2>单位阶跃响应</h2></div><div class="step-metrics"><span>上升时间<strong>{{ stepMetrics.rise.toFixed(2) }} s</strong></span><span>调节时间<strong>{{ stepMetrics.settling.toFixed(2) }} s</strong></span><span>超调量<strong>{{ stepMetrics.overshoot.toFixed(1) }}%</strong></span></div></div><div ref="stepChart" class="frequency-chart"></div></section>
  </div>
</template>

<style scoped>
.frequency-summary { display: grid; grid-template-columns: auto auto minmax(240px, 1fr); gap: 14px; align-items: center; padding: 14px 17px; border: 1px solid #cfe0f5; border-radius: 11px; background: linear-gradient(90deg, #f4f8ff, #fff); }.frequency-summary > div { display: flex; align-items: center; gap: 10px; }.frequency-summary > div > span { display: grid; place-items: center; width: 40px; height: 40px; color: #2563eb; border-radius: 9px; background: #e4eeff; }.frequency-summary small, .frequency-summary strong { display: block; }.frequency-summary small { color: var(--muted); font-size: 9px; }.frequency-summary strong { margin-top: 3px; font: 700 12px monospace; }.frequency-summary > p { color: #66788e; font-size: 10px; line-height: 1.55; }
.frequency-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 12px; }.frequency-chart { height: 330px; }.frequency-chart.tall { height: 430px; }.step-metrics { display: flex; gap: 8px; }.step-metrics span { min-width: 90px; padding: 7px 9px; color: var(--muted); font-size: 8px; border: 1px solid var(--line-soft); border-radius: 7px; background: #fbfdff; }.step-metrics strong { display: block; margin-top: 3px; color: #1f4e85; font-size: 11px; }
@media (max-width: 900px) { .frequency-grid { grid-template-columns: 1fr; }.frequency-summary { grid-template-columns: 1fr auto; }.frequency-summary > p { grid-column: 1 / -1; }.step-metrics { width: 100%; overflow-x: auto; } }
</style>
