<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { mockQualityDimensions } from '../data/mockData'
import { useEChart } from '../composables/useEChart'

const props = defineProps({ latestRun: { type: Object, default: null } })
const chartElement = ref(null)
const selectedKey = ref('dynamic')
const dimensions = computed(() => {
  const cleaning = props.latestRun?.results?.cleaning
  // TODO(mock): 没有流水线统计时使用集中示例评分；真实任务会即时覆盖全部六个维度。
  if (!cleaning) return mockQualityDimensions
  const scores = cleaning.dimension_scores ?? {}
  const vif = props.latestRun?.results?.modeling?.collinearity?.vif ?? []
  const maxVif = Math.max(1, ...vif.map((row) => Number(row.vif ?? row.VIF ?? 1)))
  const overrides = {
    completeness: Number(scores.completeness ?? 0), consistency: Number(scores.consistency ?? 0),
    snr: Number(scores.smoothness ?? 0), dynamic: Number(scores.dynamic ?? 0),
    collinearity: Math.max(0, Math.min(100, 110 - maxVif * 8)), anomaly: Number(scores.validity ?? 0),
  }
  return mockQualityDimensions.map((item) => ({ ...item, score: Number(overrides[item.key].toFixed(1)), value: item.key === 'collinearity' ? `最大 VIF ${maxVif.toFixed(2)}` : item.key === 'anomaly' ? `异常健康度 ${Number(scores.validity ?? 0).toFixed(1)}%` : `当前评分 ${Number(overrides[item.key]).toFixed(1)}` }))
})
const selected = computed(() => dimensions.value.find((item) => item.key === selectedKey.value) ?? dimensions.value[0])
const overall = computed(() => Number((dimensions.value.reduce((sum, item) => sum + item.score, 0) / Math.max(dimensions.value.length, 1)).toFixed(1)))
const grade = computed(() => overall.value >= 90 ? '优秀' : overall.value >= 80 ? '良好' : overall.value >= 65 ? '一般' : '较差')
const tone = computed(() => overall.value >= 80 ? 'success' : overall.value >= 65 ? 'warning' : 'danger')
const lowest = computed(() => dimensions.value.slice().sort((a, b) => a.score - b.score).slice(0, 3))
const positions = [['17%', '35%'], ['50%', '35%'], ['83%', '35%'], ['17%', '78%'], ['50%', '78%'], ['83%', '78%']]
const palette = ['#0ea5e9', '#2563eb', '#8b5cf6', '#f59e0b', '#14b8a6', '#10b981']
const qualityOption = computed(() => ({
  animationDuration: 600,
  tooltip: { trigger: 'item', formatter: ({ seriesName, value }) => `${seriesName}<br/><b>${value} / 100</b>` },
  series: dimensions.value.map((item, index) => ({
    name: item.label, type: 'gauge', center: positions[index], radius: '28%', min: 0, max: 100, startAngle: 90, endAngle: -270,
    pointer: { show: false }, progress: { show: true, roundCap: true, width: 9, itemStyle: { color: palette[index] } },
    axisLine: { lineStyle: { width: 9, color: [[1, '#e7edf4']] } }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
    anchor: { show: false }, title: { show: true, offsetCenter: [0, '72%'], color: '#52647a', fontSize: 11 }, detail: { valueAnimation: true, offsetCenter: [0, '-4%'], color: '#173b67', fontSize: 20, fontWeight: 750, formatter: '{value}' },
    data: [{ value: item.score, name: item.label }],
  })),
}))
const chartApi = useEChart(chartElement, qualityOption)

onMounted(() => window.setTimeout(() => chartApi.getChart()?.on('click', (params) => {
  const item = dimensions.value.find((dimension) => dimension.label === params.seriesName)
  if (item) selectedKey.value = item.key
}), 0))
</script>

<template>
  <section class="panel quality-dashboard">
    <div class="quality-score-card"><span>DATA QUALITY INDEX</span><strong>{{ overall }}</strong><StatusPill :tone="tone">{{ grade }}</StatusPill><p>{{ latestRun ? `来自任务 ${latestRun.run_id}` : '暂无真实统计，当前为演示评分' }}</p></div>
    <div class="quality-main"><div class="section-heading compact"><div><span class="section-kicker">Six-dimensional Quality Profile</span><h2>数据质量综合评分卡</h2></div><span class="quality-hint">点击环形评分查看计算方法</span></div><div ref="chartElement" class="quality-chart"></div></div>
    <aside class="quality-detail"><div><span class="section-kicker">Dimension Detail</span><h3>{{ selected?.label }}</h3><strong>{{ selected?.score }}<small> / 100</small></strong></div><dl><dt>计算方法</dt><dd>{{ selected?.method }}</dd><dt>当前数值</dt><dd>{{ selected?.value }}</dd></dl><div class="quality-suggestion"><AppIcon name="spark" :size="16" /><p><strong>改进建议</strong>{{ selected?.suggestion }}</p></div><div class="quality-priorities"><span>优先改进</span><button v-for="item in lowest" :key="item.key" type="button" @click="selectedKey = item.key"><i :style="{ width: `${item.score}%` }"></i><strong>{{ item.label }}</strong><small>{{ item.score }}</small></button></div></aside>
  </section>
</template>

<style scoped>
.quality-dashboard { display: grid; grid-template-columns: 145px minmax(480px, 1fr) 250px; gap: 16px; align-items: stretch; padding: 16px; }.quality-score-card { display: grid; place-content: center; justify-items: center; padding: 14px; color: #dcecff; text-align: center; border-radius: 11px; background: radial-gradient(circle at 50% 35%, rgba(37,99,235,.44), transparent 38%), linear-gradient(150deg, #0b1b31, #12375e); }.quality-score-card > span { color: #6c91b8; font: 8px monospace; letter-spacing: .08em; }.quality-score-card > strong { margin: 10px 0 6px; color: #fff; font-size: 42px; line-height: 1; }.quality-score-card > p { margin-top: 12px; color: #6d8baa; font-size: 8px; line-height: 1.45; }.quality-main { min-width: 0; }.quality-hint { color: var(--muted); font-size: 9px; }.quality-chart { height: 330px; margin: -18px 0 -12px; cursor: pointer; }
.quality-detail { padding: 14px; border: 1px solid #dce7f3; border-radius: 10px; background: #f8fbff; }.quality-detail h3 { margin-top: 5px; font-size: 15px; }.quality-detail > div:first-child > strong { display: block; margin-top: 6px; color: #1d5fae; font-size: 27px; }.quality-detail > div:first-child small { color: var(--muted); font-size: 9px; }.quality-detail dl { display: grid; gap: 4px; margin-top: 12px; }.quality-detail dt { margin-top: 6px; color: #7d8ca0; font-size: 8px; }.quality-detail dd { color: #3f536b; font-size: 10px; line-height: 1.5; }.quality-suggestion { display: grid; grid-template-columns: 22px 1fr; gap: 6px; margin-top: 12px; padding: 9px; color: #2d5c8d; border-radius: 7px; background: #eaf3ff; }.quality-suggestion p { font-size: 9px; line-height: 1.45; }.quality-suggestion strong { display: block; margin-bottom: 2px; }.quality-priorities { display: grid; gap: 5px; margin-top: 12px; }.quality-priorities > span { color: #7d8ca0; font-size: 8px; }.quality-priorities button { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 5px; padding: 6px 7px; overflow: hidden; color: #52647a; font-size: 8px; text-align: left; border: 1px solid #e2e8f0; border-radius: 5px; background: #fff; }.quality-priorities button i { position: absolute; inset: 0 auto 0 0; z-index: 0; background: #eaf3ff; }.quality-priorities strong, .quality-priorities small { z-index: 1; }
@media (max-width: 1100px) { .quality-dashboard { grid-template-columns: 130px minmax(440px, 1fr); }.quality-detail { grid-column: 1 / -1; display: grid; grid-template-columns: 150px 1fr 1fr; gap: 12px; }.quality-detail dl { margin-top: 0; }.quality-suggestion { margin-top: 0; } }
@media (max-width: 720px) { .quality-dashboard { grid-template-columns: 1fr; }.quality-score-card { min-height: 180px; }.quality-main { overflow-x: auto; }.quality-chart { min-width: 620px; }.quality-detail { display: block; }.quality-detail dl, .quality-suggestion { margin-top: 12px; } }
</style>
