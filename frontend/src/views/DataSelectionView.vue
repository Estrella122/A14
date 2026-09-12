<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import DataQualityDashboard from '../components/DataQualityDashboard.vue'
import { artifactUrl } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate'])
const { latestRun } = useLatestPipelineRun()
const liveCleaning = computed(() => latestRun.value?.results?.cleaning ?? {})
const seriesPreview = computed(() => liveCleaning.value.timeseries_preview ?? {})
const seriesPoints = computed(() => (seriesPreview.value.points ?? []).filter((item) => Number.isFinite(Number(item.input)) && Number.isFinite(Number(item.output))))
const inputMeta = computed(() => seriesPreview.value.input ?? { label: props.project.mv, unit: props.project.mvUnit })
const outputMeta = computed(() => seriesPreview.value.output ?? { label: props.project.target, unit: props.project.targetUnit })

const weights = ref({ dynamic: 38, snr: 27, integrity: 20, coverage: 15 })
const selectedIds = ref([])
const scoringApplied = ref(false)
const segmentFilter = ref('all')
const segments = computed(() => {
  const rows = liveCleaning.value.segments_preview ?? []
  if (!rows.length) return []
  return rows.map((row, index) => {
    const start = new Date(row.start_time)
    const end = new Date(row.end_time)
    return {
      id: `SEG-${String(index + 1).padStart(3, '0')}`,
      time: `${row.start_time} — ${row.end_time}`,
      duration: `${Math.max(0, (end - start) / 60000).toFixed(1)} min`,
      type: row.level,
      dynamic: Number(row.input_change_score ?? 0),
      snr: Number(row.snr_db ?? 0),
      integrity: Number(row.completeness_score ?? 0),
      score: Number(row.segment_score ?? 0),
      reason: `${row.level}；异常健康度 ${Number(row.anomaly_score ?? 0).toFixed(1)}，平滑度 ${Number(row.smoothness_score ?? 0).toFixed(1)}`,
    }
  })
})
const scoredSegments = computed(() => segments.value.map((item) => ({
  ...item,
  score: scoringApplied.value
    ? (item.dynamic * weights.value.dynamic + item.snr * weights.value.snr + item.integrity * weights.value.integrity + Number(item.score) * weights.value.coverage) / Math.max(weights.value.dynamic + weights.value.snr + weights.value.integrity + weights.value.coverage, 1)
    : item.score,
})).sort((left, right) => right.score - left.score))
const visibleSegments = computed(() => scoredSegments.value.filter((item) => {
  if (segmentFilter.value === 'dynamic') return item.dynamic >= 80
  if (segmentFilter.value === 'review') return item.score < 80 || String(item.type).includes('异常')
  return true
}))
function buildSeriesPath(key) {
  const points = seriesPoints.value
  if (!points.length) return ''
  const values = points.map((item) => Number(item[key]))
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const span = Math.max(maximum - minimum, 1e-9)
  return points.map((item, index) => {
    const x = 60 + index * 1030 / Math.max(points.length - 1, 1)
    const y = 235 - (Number(item[key]) - minimum) / span * 170
    return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}
const outputPath = computed(() => buildSeriesPath('output'))
const inputPath = computed(() => buildSeriesPath('input'))
const chartStart = computed(() => seriesPoints.value.length ? new Date(seriesPoints.value[0].timestamp).getTime() : 0)
const chartEnd = computed(() => seriesPoints.value.length ? new Date(seriesPoints.value.at(-1).timestamp).getTime() : 0)
function timelineRatio(value) {
  const timestamp = new Date(value).getTime()
  return Math.max(0, Math.min(1, (timestamp - chartStart.value) / Math.max(chartEnd.value - chartStart.value, 1)))
}
const segmentBands = computed(() => (liveCleaning.value.segments_preview ?? []).map((item, index) => {
  const left = timelineRatio(item.start_time)
  const right = timelineRatio(item.end_time)
  const rejected = String(item.level ?? '').includes('异常') || Number(item.anomaly_score ?? 100) < 60
  const selected = item.level === '优质动态段'
  return {
    id: `SEG-${String(index + 1).padStart(3, '0')}`,
    score: Number(item.segment_score ?? 0),
    x: 60 + left * 1030,
    width: Math.max(3, (right - left) * 1030),
    left: left * 100,
    widthPercent: Math.max(0.4, (right - left) * 100),
    tone: rejected ? 'rejected' : selected ? 'selected' : 'candidate',
  }
}))
const chartTimeTicks = computed(() => {
  const points = seriesPoints.value
  if (!points.length) return []
  return Array.from({ length: 6 }, (_, index) => {
    const pointIndex = Math.round(index * (points.length - 1) / 5)
    const date = new Date(points[pointIndex].timestamp)
    return { x: 60 + index * 1030 / 5, label: date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replaceAll('/', '-') }
  })
})
watch(segments, (rows) => { selectedIds.value = rows.filter((item) => item.type === '优质动态段').map((item) => item.id) }, { immediate: true })
const selectedCount = computed(() => Number(liveCleaning.value.selected_segment_count ?? selectedIds.value.length))
const candidateCount = computed(() => segments.value.length)
const modelingRate = computed(() => Number(liveCleaning.value.modeling_row_count ?? 0) / Math.max(Number(liveCleaning.value.cleaned_row_count ?? 0), 1))
const averageScore = computed(() => scoredSegments.value.length ? scoredSegments.value.reduce((sum, item) => sum + item.score, 0) / scoredSegments.value.length : 0)

function rescoreSegments() {
  if (!latestRun.value) { emit('notify', { tone: 'warning', title: '尚无真实任务', message: '请先上传并运行 CSV；系统不会用演示片段替代真实结果。' }); return }
  scoringApplied.value = true
  emit('notify', { tone: 'success', title: '动态段已重新评分', message: `已按 ${weights.value.dynamic}/${weights.value.snr}/${weights.value.integrity}/${weights.value.coverage} 权重重算并排序。` })
}

function saveScoreTemplate() {
  window.localStorage.setItem('processpilot-segment-weights', JSON.stringify(weights.value))
  emit('notify', { tone: 'success', title: '评分模板已保存', message: '当前四项权重已保存到本地项目配置。' })
}

function toggleSegment(id) {
  selectedIds.value = selectedIds.value.includes(id) ? selectedIds.value.filter((item) => item !== id) : [...selectedIds.value, id]
}

function freezeDataset() {
  if (!latestRun.value) { emit('notify', { tone: 'warning', title: '无法冻结', message: '当前没有真实优选结果。' }); return }
  emit('notify', { tone: 'success', title: '当前优选结果已确认', message: `任务 ${latestRun.value?.run_id ?? '—'} 的 ${selectedCount.value} 个训练达标窗口已记录。` })
}
</script>

<template>
  <div class="view-stack selection-view">
    <PageHeader
      eyebrow="High-SNR Dynamic Segmentation"
      title="高信噪比动态数据优选"
      description="在无标签时序数据中自动识别阶跃与扰动响应，剔除低信息稳态段，并按动态性、信噪比、完整性和工况覆盖度进行排序。"
    >
      <template #actions>
        <StatusPill :tone="latestRun ? 'success' : 'neutral'" dot>{{ latestRun ? '真实任务数据' : '等待真实数据' }}</StatusPill>
        <button class="btn btn-secondary" type="button" :disabled="!latestRun" @click="rescoreSegments"><AppIcon name="spark" />重新智能评分</button>
        <button class="btn btn-primary" type="button" :disabled="!latestRun" @click="freezeDataset"><AppIcon name="check" />冻结优选数据集</button>
      </template>
    </PageHeader>

    <DataQualityDashboard :latest-run="latestRun" />

    <section class="metric-grid four-col">
      <article class="metric-card"><span class="metric-label">检测候选段</span><div class="metric-value">{{ candidateCount }} <small>段</small></div><p>当前任务 {{ latestRun?.run_id ?? '等待运行' }}</p><span class="metric-trend neutral">真实滑动窗口结果</span></article>
      <article class="metric-card accent-cyan"><span class="metric-label">训练达标窗口</span><div class="metric-value">{{ selectedCount }} <small>段</small></div><p>建模数据 {{ liveCleaning.modeling_row_count ?? '—' }} 行</p><span class="metric-trend positive">动态分≥80且SNR代理≥10 dB</span></article>
      <article class="metric-card"><span class="metric-label">建模数据保留率</span><div class="metric-value">{{ (modelingRate * 100).toFixed(1) }}%</div><p>规整后 {{ liveCleaning.cleaned_row_count ?? '—' }} 行</p><span class="metric-trend positive">候选不足时使用Top窗口兜底</span></article>
      <article class="metric-card"><span class="metric-label">候选质量均分</span><div class="metric-value">{{ averageScore.toFixed(1) }}</div><p>综合五维动态评分</p><span class="metric-trend positive">来自本次CSV</span></article>
    </section>

    <section class="panel segment-chart-panel">
      <div class="section-heading compact">
        <div><span class="section-kicker">全时域动态检测</span><h2>{{ inputMeta.label }} → {{ outputMeta.label }}</h2></div>
        <div class="chart-legend"><span><i class="legend-dot target"></i>{{ outputMeta.label }}{{ outputMeta.unit ? ` (${outputMeta.unit})` : '' }}</span><span><i class="legend-dot mv"></i>{{ inputMeta.label }}{{ inputMeta.unit ? ` (${inputMeta.unit})` : '' }}</span><span><i class="legend-block selected"></i>优质动态段</span><span><i class="legend-block rejected"></i>异常剔除</span></div>
      </div>
      <svg class="line-chart segment-chart" viewBox="0 0 1120 300" role="img" :aria-label="`${inputMeta.label}到${outputMeta.label}的真实全时域波形与动态段`">
        <g class="chart-grid"><path d="M60 35H1090M60 95H1090M60 155H1090M60 215H1090M60 255H1090" /><path d="M60 35V255M266 35V255M472 35V255M678 35V255M884 35V255M1090 35V255" /></g>
        <g class="segment-bands"><rect v-for="band in segmentBands" :key="band.id" :x="band.x" y="36" :width="band.width" height="218" rx="4" :class="`${band.tone}-band`" /></g>
        <path v-if="outputPath" class="chart-line target-line" :d="outputPath" />
        <path v-if="inputPath" class="chart-line mv-line" :d="inputPath" />
        <g class="segment-labels"><text v-for="band in segmentBands.filter((item) => item.width > 38)" :key="band.id" :x="band.x + 4" y="55">{{ band.id }} · {{ band.score.toFixed(1) }}</text></g>
        <g class="chart-labels"><text v-for="tick in chartTimeTicks" :key="tick.x" :x="tick.x" y="282" :text-anchor="tick.x === 60 ? 'start' : tick.x === 1090 ? 'end' : 'middle'">{{ tick.label }}</text></g>
        <text v-if="!seriesPoints.length" x="560" y="150" text-anchor="middle" class="empty-chart-label">当前任务尚无真实波形预览，请由总控重新运行该 CSV</text>
      </svg>
      <div class="timeline-overview"><span v-for="band in segmentBands" :key="band.id" :class="band.tone === 'rejected' ? 'timeline-rejected' : band.tone === 'selected' ? 'timeline-selected' : 'timeline-candidate'" :style="{ left: `${band.left}%`, width: `${band.widthPercent}%` }"></span></div>
    </section>

    <div class="content-grid content-grid-3-9">
      <section class="panel scoring-panel">
        <div class="section-heading compact"><div><span class="section-kicker">可解释质量评分</span><h2>评分权重</h2></div><StatusPill tone="brand">Agent 推荐</StatusPill></div>
        <div class="weight-controls">
          <label><span>动态信息量 <strong>{{ weights.dynamic }}%</strong></span><input v-model="weights.dynamic" type="range" min="10" max="50" /></label>
          <label><span>信噪比 SNR <strong>{{ weights.snr }}%</strong></span><input v-model="weights.snr" type="range" min="10" max="50" /></label>
          <label><span>响应完整性 <strong>{{ weights.integrity }}%</strong></span><input v-model="weights.integrity" type="range" min="10" max="40" /></label>
          <label><span>工况覆盖度 <strong>{{ weights.coverage }}%</strong></span><input v-model="weights.coverage" type="range" min="5" max="30" /></label>
        </div>
        <div class="score-formula"><span>Overall Score</span><code>0.38D + 0.27S + 0.20I + 0.15C</code><p>异常密度超过 3% 时触发降权；工艺越界直接进入人工复核。</p></div>
        <button class="btn btn-secondary btn-block" type="button" @click="saveScoreTemplate">保存为评分模板</button>
      </section>

      <section class="panel segment-table-panel">
        <div class="section-heading compact"><div><span class="section-kicker">候选片段排序</span><h2>有效建模数据段</h2></div><div class="table-tools"><button :class="{ 'is-active': segmentFilter === 'all' }" type="button" @click="segmentFilter = 'all'">综合得分</button><button :class="{ 'is-active': segmentFilter === 'dynamic' }" type="button" @click="segmentFilter = 'dynamic'">高动态</button><button :class="{ 'is-active': segmentFilter === 'review' }" type="button" @click="segmentFilter = 'review'">待复核</button></div></div>
        <div class="table-wrap">
          <table class="data-table segment-table">
            <caption class="visually-hidden">候选动态数据段质量评分与选择</caption>
            <thead><tr><th>数据段</th><th>时间与类型</th><th>评分构成</th><th>综合分</th><th>Agent 说明</th><th>建模选择</th></tr></thead>
            <tbody>
              <tr v-for="segment in visibleSegments" :key="segment.id" :class="{ 'is-selected-row': selectedIds.includes(segment.id) }">
                <td><strong>{{ segment.id }}</strong><small>{{ segment.duration }}</small></td>
                <td><span>{{ segment.time }}</span><StatusPill :tone="segment.type === '异常扰动' ? 'warning' : 'neutral'">{{ segment.type }}</StatusPill></td>
                <td><div class="mini-score-bars"><span title="动态性"><i :style="{ width: `${segment.dynamic}%` }"></i></span><span title="信噪比"><i :style="{ width: `${segment.snr}%` }"></i></span><span title="完整性"><i :style="{ width: `${segment.integrity}%` }"></i></span></div></td>
                <td><strong class="large-score" :class="{ 'is-low': segment.score < 80 }">{{ Number(segment.score).toFixed(1) }}</strong></td>
                <td class="reason-cell">{{ segment.reason }}</td>
                <td><button class="segment-toggle" :class="{ 'is-on': selectedIds.includes(segment.id) }" type="button" :aria-pressed="selectedIds.includes(segment.id)" @click="toggleSegment(segment.id)"><span></span>{{ selectedIds.includes(segment.id) ? '已入选' : '未入选' }}</button></td>
              </tr>
              <tr v-if="!visibleSegments.length"><td colspan="6">当前筛选条件下没有数据段。</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div class="selection-footer-card">
      <div class="dataset-freeze"><span><AppIcon name="database" /></span><div><strong>优选数据集 {{ latestRun?.run_id ?? '等待运行' }}</strong><p>{{ selectedCount }} 个训练达标窗口 · {{ liveCleaning.modeling_row_count ?? 0 }} 行建模数据</p></div></div>
      <div class="dataset-gains"><span>建模保留率<strong>{{ (modelingRate * 100).toFixed(1) }}%</strong></span><span>质量评分<strong>{{ liveCleaning.overall_score ?? '—' }}</strong></span><a v-if="latestRun" :href="artifactUrl(latestRun.run_id, 'modeling_csv')">下载优选CSV</a></div>
      <button class="btn btn-primary" type="button" @click="emit('navigate', '/identification-modeling/')">进入解耦辨识 <AppIcon name="arrow" /></button>
    </div>
  </div>
</template>
