<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { useEChart } from '../composables/useEChart'

const props = defineProps({ model: { type: Object, default: null } })
const frequencyChart = ref(null)
const stepChart = ref(null)
const selectedKey = ref('')

const channels = computed(() => {
  const outputModels = props.model?.mimo?.outputs?.length
    ? props.model.mimo.outputs
    : [{ output_col: props.model?.output_col, response_analysis: props.model?.response_analysis }]
  return outputModels.flatMap((output) => (output.response_analysis?.channels ?? []).map((channel) => ({
    ...channel,
    output: channel.output ?? output.output_col,
    key: `${channel.output ?? output.output_col}::${channel.input}`,
  })))
})
watch(channels, (rows) => {
  if (!rows.some((row) => row.key === selectedKey.value)) selectedKey.value = rows[0]?.key ?? ''
}, { immediate: true })
const selected = computed(() => channels.value.find((row) => row.key === selectedKey.value) ?? null)
const commonText = { color: '#64748b', fontSize: 10 }
const frequencyOption = computed(() => ({
  animationDuration: 450,
  tooltip: { trigger: 'axis' },
  grid: [{ left: 58, right: 22, top: 25, height: '34%' }, { left: 58, right: 22, top: '57%', height: '30%' }],
  xAxis: [
    { type: 'log', gridIndex: 0, axisLabel: { show: false }, splitLine: { lineStyle: { color: '#edf2f7' } } },
    { type: 'log', gridIndex: 1, name: '频率 (Hz)', nameLocation: 'middle', nameGap: 27, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  ],
  yAxis: [
    { type: 'value', gridIndex: 0, name: '幅值 (dB)', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
    { type: 'value', gridIndex: 1, name: '相位 (°)', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  ],
  series: [
    { name: '幅值', type: 'line', xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, data: (selected.value?.frequency ?? []).filter((row) => row.hz > 0 && row.magnitude_db != null).map((row) => [row.hz, row.magnitude_db]), lineStyle: { color: '#2563eb', width: 2 } },
    { name: '相位', type: 'line', xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, data: (selected.value?.frequency ?? []).filter((row) => row.hz > 0 && row.phase_degrees != null).map((row) => [row.hz, row.phase_degrees]), lineStyle: { color: '#8b5cf6', width: 2 } },
  ],
}))
const stepOption = computed(() => ({
  animationDuration: 450,
  tooltip: { trigger: 'axis' },
  grid: { left: 58, right: 24, top: 25, bottom: 45 },
  xAxis: { type: 'value', name: '时间 (s)', nameLocation: 'middle', nameGap: 28, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  yAxis: { type: 'value', name: '输出偏差', nameTextStyle: commonText, axisLabel: commonText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  series: [{ name: '单位阶跃响应', type: 'line', showSymbol: false, data: (selected.value?.step ?? []).map((row) => [row.seconds, row.value]), lineStyle: { color: '#f97316', width: 2.2 }, areaStyle: { color: 'rgba(249,115,22,.08)' } }],
}))
useEChart(frequencyChart, frequencyOption)
useEChart(stepChart, stepOption)
</script>

<template>
  <div class="view-stack frequency-analysis">
    <section v-if="channels.length" class="frequency-summary">
      <div><span><AppIcon name="model" :size="22" /></span><p><small>本次辨识的真实 ARX 通道</small><strong>{{ selected?.input }} → {{ selected?.output }}</strong></p></div>
      <select v-model="selectedKey" aria-label="选择输入输出响应通道"><option v-for="channel in channels" :key="channel.key" :value="channel.key">{{ channel.input }} → {{ channel.output }}</option></select>
      <StatusPill tone="success">辨识参数</StatusPill>
      <p>离散响应由本次 ARX 系数与因果时滞直接计算；其他输入保持零偏差，不将其表述为现场闭环响应。</p>
    </section>
    <section v-if="channels.length" class="channel-grid" aria-label="输入输出通道矩阵">
      <article v-for="channel in channels" :key="`summary-${channel.key}`" :class="{ active: channel.key === selectedKey }" @click="selectedKey = channel.key"><span>{{ channel.input }} → {{ channel.output }}</span><strong>K={{ channel.dc_gain == null ? '—' : Number(channel.dc_gain).toPrecision(4) }}</strong><small>时滞 {{ channel.delay_seconds }} s</small></article>
    </section>
    <template v-if="selected">
      <div class="frequency-grid"><section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Identified Frequency Response</span><h2>离散频率响应</h2></div><StatusPill tone="brand">至奈奎斯特频率</StatusPill></div><div ref="frequencyChart" class="frequency-chart tall"></div></section><section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Identified Step Response</span><h2>单位阶跃响应</h2></div><div class="step-metrics"><span>静态增益<strong>{{ selected.dc_gain == null ? '—' : Number(selected.dc_gain).toPrecision(5) }}</strong></span><span>纯时滞<strong>{{ selected.delay_seconds }} s</strong></span></div></div><div ref="stepChart" class="frequency-chart tall"></div></section></div>
      <p class="response-note">方法：{{ model?.response_analysis?.method ?? 'discrete_arx_deviation_response' }}。响应用于离线模型审查，正式投运仍需受控阶跃、外部时段验证和联锁评审。</p>
    </template>
    <section v-else class="panel empty-state"><h2>暂无真实响应产物</h2><p>请重新运行新版辨识流水线。系统不会使用示例模型替代本次结果。</p></section>
  </div>
</template>

<style scoped>
.frequency-summary { display: flex; gap: 14px; align-items: center; padding: 14px 17px; border: 1px solid #cfe0f5; border-radius: 11px; background: linear-gradient(90deg, #f4f8ff, #fff); }.frequency-summary > div { display: flex; align-items: center; gap: 10px; }.frequency-summary > div > span { display: grid; place-items: center; width: 40px; height: 40px; color: #2563eb; border-radius: 9px; background: #e4eeff; }.frequency-summary small,.frequency-summary strong { display:block }.frequency-summary small { color:var(--muted);font-size:9px }.frequency-summary strong { margin-top:3px;font:700 11px monospace }.frequency-summary select { min-width:260px;padding:8px;border:1px solid var(--line);border-radius:7px;background:#fff }.frequency-summary > p { flex:1;color:#66788e;font-size:10px;line-height:1.55 }
.channel-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px }.channel-grid article { cursor:pointer;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:#fff }.channel-grid article.active { border-color:#60a5fa;background:#eff6ff }.channel-grid span,.channel-grid strong,.channel-grid small { display:block }.channel-grid span { font:600 10px monospace }.channel-grid strong { margin-top:6px;color:#1f4e85 }.channel-grid small { color:var(--muted) }
.frequency-grid { display:grid;grid-template-columns:1fr 1fr;gap:12px }.frequency-chart.tall { height:430px }.step-metrics { display:flex;gap:8px }.step-metrics span { min-width:90px;padding:7px 9px;color:var(--muted);font-size:8px;border:1px solid var(--line-soft);border-radius:7px }.step-metrics strong { display:block;margin-top:3px;color:#1f4e85;font-size:11px }.response-note,.empty-state { color:#64748b;font-size:10px }.empty-state { padding:40px;text-align:center }
@media (max-width:900px) { .frequency-grid { grid-template-columns:1fr }.frequency-summary { flex-wrap:wrap }.frequency-summary > p { flex-basis:100% }.frequency-summary select { min-width:0;flex:1 } }
</style>
