<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import { listPipelineRuns } from '../api/pipeline'
import { useEChart } from '../composables/useEChart'
import { mockExperimentsByScenario } from '../data/mockData'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify'])
const experiments = ref([])
const loading = ref(true)
const error = ref('')
const source = ref('mock')
const selectedIds = ref([])
const comparisonOpen = ref(false)
const algorithmFilter = ref('all')
const datasetFilter = ref('all')
const sortBy = ref('time')
const fitChart = ref(null)
const predictionChart = ref(null)
const residualChart = ref(null)
let controller
const scenarioMocks = computed(() => mockExperimentsByScenario[props.project.scenarioId] ?? mockExperimentsByScenario.blast_furnace)

const annotations = (() => { try { return JSON.parse(window.localStorage.getItem('processpilot-experiment-annotations') || '{}') } catch { return {} } })()
function withAnnotations(row) { return { ...row, tag: annotations[row.id]?.tag ?? row.tag ?? '', note: annotations[row.id]?.note ?? row.note ?? '' } }

const algorithms = computed(() => [...new Set(experiments.value.map((item) => item.algorithm).filter(Boolean))])
const datasets = computed(() => [...new Set(experiments.value.map((item) => item.dataset).filter(Boolean))])
const filteredRows = computed(() => experiments.value.filter((item) => (algorithmFilter.value === 'all' || item.algorithm === algorithmFilter.value) && (datasetFilter.value === 'all' || item.dataset === datasetFilter.value)).slice().sort((left, right) => sortBy.value === 'r2' ? right.r2 - left.r2 : String(right.time).localeCompare(String(left.time))))
const comparisonRows = computed(() => selectedIds.value.map((id) => experiments.value.find((item) => item.id === id)).filter(Boolean))
const canCompare = computed(() => selectedIds.value.length >= 2 && selectedIds.value.length <= 4)

const colors = ['#2563eb', '#0f9f72', '#f59e0b', '#8b5cf6']
const chartText = { color: '#64748b', fontSize: 10 }
const fitOption = computed(() => ({
  grid: { left: 45, right: 20, top: 28, bottom: 45 },
  tooltip: { trigger: 'axis', valueFormatter: (value) => Number(value).toFixed(3) },
  xAxis: { type: 'category', data: comparisonRows.value.map((item) => item.id.slice(-9)), axisLabel: { ...chartText, rotate: 12 } },
  yAxis: { type: 'value', min: Math.max(0, Math.min(...comparisonRows.value.map((item) => item.r2), .75) - .05), max: 1, axisLabel: chartText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  series: [{ type: 'bar', data: comparisonRows.value.map((item, index) => ({ value: item.r2, itemStyle: { color: colors[index], borderRadius: [5, 5, 0, 0] } })), barMaxWidth: 54, label: { show: true, position: 'top', formatter: ({ value }) => Number(value).toFixed(3), color: '#334155', fontSize: 10 } }],
}))
const predictionOption = computed(() => {
  const rows = comparisonRows.value
  return {
    color: ['#172033', ...colors], grid: { left: 48, right: 18, top: 38, bottom: 32 }, tooltip: { trigger: 'axis' },
    legend: { top: 2, textStyle: chartText },
    xAxis: { type: 'category', boundaryGap: false, data: Array.from({ length: rows[0]?.actual?.length ?? 0 }, (_, index) => index), axisLabel: chartText },
    yAxis: { type: 'value', scale: true, axisLabel: chartText, splitLine: { lineStyle: { color: '#edf2f7' } } },
    series: [
      { name: '实测值', type: 'line', data: rows[0]?.actual ?? [], symbol: 'none', lineStyle: { width: 2.5 } },
      ...rows.map((item) => ({ name: `${item.id.slice(-4)} 预测`, type: 'line', data: item.predicted, symbol: 'none', lineStyle: { width: 1.7 } })),
    ],
  }
})

function quantile(sorted, fraction) {
  if (!sorted.length) return 0
  const position = (sorted.length - 1) * fraction
  const base = Math.floor(position)
  const rest = position - base
  return sorted[base] + (sorted[base + 1] === undefined ? 0 : rest * (sorted[base + 1] - sorted[base]))
}
function boxData(values) {
  const sorted = [...values].map(Number).sort((a, b) => a - b)
  return [sorted[0] ?? 0, quantile(sorted, .25), quantile(sorted, .5), quantile(sorted, .75), sorted.at(-1) ?? 0]
}
const residualOption = computed(() => ({
  color: colors, grid: { left: 48, right: 18, top: 24, bottom: 40 }, tooltip: { trigger: 'item' },
  xAxis: { type: 'category', data: comparisonRows.value.map((item) => item.id.slice(-9)), axisLabel: chartText },
  yAxis: { type: 'value', name: '残差', nameTextStyle: chartText, axisLabel: chartText, splitLine: { lineStyle: { color: '#edf2f7' } } },
  series: [{ type: 'boxplot', data: comparisonRows.value.map((item, index) => ({ value: boxData(item.residuals ?? []), itemStyle: { color: `${colors[index]}33`, borderColor: colors[index] } })) }],
}))
useEChart(fitChart, fitOption)
useEChart(predictionChart, predictionOption)
useEChart(residualChart, residualOption)

function normalizeRun(run, index) {
  const fallback = scenarioMocks.value[index % scenarioMocks.value.length]
  const result = run.results ?? {}
  const model = result.modeling ?? {}
  const metrics = model.metrics?.test ?? {}
  return withAnnotations({
    ...fallback,
    id: run.run_id ?? run.id ?? fallback.id,
    time: run.updated_at ? new Date(run.updated_at).toLocaleString('zh-CN', { hour12: false }) : fallback.time,
    dataset: run.original_name ?? run.dataset ?? fallback.dataset,
    preprocessing: `${result.cleaning?.config?.resample_rule ?? '5s'} / Hampel`,
    algorithm: model.model_type ?? 'ARX',
    order: model.order ?? fallback.order,
    r2: Number(metrics.r2 ?? fallback.r2),
    aic: Number(metrics.aic ?? fallback.aic),
    duration: Number(run.duration_seconds ?? fallback.duration),
    status: run.status ?? 'completed',
  })
}

async function loadRuns() {
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''
  try {
    const payload = await listPipelineRuns({ signal: controller.signal, scenarioId: props.project.scenarioId })
    const rows = Array.isArray(payload) ? payload : payload?.results ?? payload?.runs ?? []
    if (!rows.length) throw new Error('后端尚无历史运行记录')
    experiments.value = rows.map(normalizeRun)
    source.value = 'api'
  } catch (requestError) {
    if (requestError.name === 'AbortError') return
    // TODO(mock): 历史列表接口失败或无记录时保留此分支，作为离线演示降级。
    experiments.value = scenarioMocks.value.map(withAnnotations)
    source.value = 'mock'
    error.value = `${requestError.message}，已切换为演示实验记录`
  } finally { loading.value = false }
}

function toggleSelection(id) {
  if (selectedIds.value.includes(id)) selectedIds.value = selectedIds.value.filter((item) => item !== id)
  else if (selectedIds.value.length < 4) selectedIds.value = [...selectedIds.value, id]
  else emit('notify', { tone: 'warning', title: '最多对比 4 条记录', message: '请先取消一条已选实验。' })
}
async function openComparison() {
  if (!canCompare.value) return
  comparisonOpen.value = true
  await nextTick()
  window.dispatchEvent(new CustomEvent('processpilot:charts-visible'))
  window.setTimeout(() => document.querySelector('.experiment-comparison')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
}
function isDifferent(key) { return new Set(comparisonRows.value.map((item) => String(item[key]))).size > 1 }

watch(experiments, (rows) => {
  const values = Object.fromEntries(rows.map((row) => [row.id, { tag: row.tag, note: row.note }]))
  try { window.localStorage.setItem('processpilot-experiment-annotations', JSON.stringify(values)) } catch { /* optional */ }
}, { deep: true })
onMounted(loadRuns)
onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <div class="view-stack experiment-view">
    <PageHeader eyebrow="Experiment Tracking & Model Registry" title="实验追踪与版本对比" description="统一记录每次数据预处理、辨识与闭环寻优结果，在相同评价口径下定位真正可复现的最佳模型。">
      <template #actions><StatusPill :tone="source === 'api' ? 'success' : 'warning'" dot>{{ source === 'api' ? '后端历史记录' : '离线演示数据' }}</StatusPill><button class="btn btn-primary" type="button" :disabled="!canCompare" @click="openComparison"><AppIcon name="model" />对比选中项（{{ selectedIds.length }}）</button></template>
    </PageHeader>

    <div v-if="error" class="experiment-notice"><AppIcon name="alert" :size="15" />{{ error }}<button type="button" @click="loadRuns"><AppIcon name="loop" :size="13" />重试</button></div>
    <section class="panel experiment-table-panel" :aria-busy="loading">
      <div class="section-heading compact"><div><span class="section-kicker">Run Registry</span><h2>历史运行记录</h2></div><div class="experiment-filters"><select v-model="datasetFilter"><option value="all">全部数据集</option><option v-for="item in datasets" :key="item">{{ item }}</option></select><select v-model="algorithmFilter"><option value="all">全部算法</option><option v-for="item in algorithms" :key="item">{{ item }}</option></select><select v-model="sortBy"><option value="time">按时间排序</option><option value="r2">按拟合度排序</option></select></div></div>
      <div v-if="loading" class="experiment-loading"><AppIcon name="loop" class="spinning" />正在读取历史实验…</div>
      <div v-else-if="filteredRows.length" class="table-wrap"><table class="data-table experiment-table"><thead><tr><th>选择</th><th>运行 ID / 时间</th><th>数据集</th><th>预处理参数</th><th>算法 / 阶次</th><th>R²</th><th>AIC</th><th>耗时</th><th>状态</th><th>标签与备注</th></tr></thead><tbody>
        <tr v-for="row in filteredRows" :key="row.id" :class="{ 'is-selected-row': selectedIds.includes(row.id) }"><td><input type="checkbox" :checked="selectedIds.includes(row.id)" :aria-label="`选择 ${row.id}`" @change="toggleSelection(row.id)" /></td><td><code>{{ row.id }}</code><small>{{ row.time }}</small></td><td>{{ row.dataset }}</td><td><code>{{ row.preprocessing }}</code></td><td><strong>{{ row.algorithm }}</strong><small>{{ row.order }}</small></td><td><strong class="experiment-r2">{{ row.r2.toFixed(3) }}</strong></td><td>{{ row.aic.toFixed(1) }}</td><td>{{ row.duration.toFixed(1) }} s</td><td><StatusPill :tone="row.status === 'completed' ? 'success' : 'warning'">{{ row.status === 'completed' ? '已完成' : row.status }}</StatusPill></td><td><div class="annotation-cell"><select v-model="row.tag"><option value="">无标签</option><option>最佳结果</option><option>基线</option><option>候选</option><option>尝试1</option><option>尝试2</option></select><input v-model="row.note" type="text" placeholder="添加备注" /></div></td></tr>
      </tbody></table></div>
      <div v-else class="empty-state">当前筛选条件下没有实验记录。</div>
    </section>

    <section v-show="comparisonOpen" class="experiment-comparison view-stack">
      <section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Parameter Diff</span><h2>参数差异对比</h2></div><button class="text-button" type="button" @click="comparisonOpen = false">收起对比</button></div><div class="table-wrap"><table class="data-table parameter-diff"><thead><tr><th>参数</th><th v-for="row in comparisonRows" :key="row.id">{{ row.id.slice(-9) }}</th></tr></thead><tbody>
        <tr :class="{ different: isDifferent('dataset') }"><td>数据集</td><td v-for="row in comparisonRows" :key="row.id">{{ row.dataset }}</td></tr>
        <tr :class="{ different: isDifferent('preprocessing') }"><td>预处理</td><td v-for="row in comparisonRows" :key="row.id">{{ row.preprocessing }}</td></tr>
        <tr :class="{ different: isDifferent('algorithm') }"><td>辨识算法</td><td v-for="row in comparisonRows" :key="row.id">{{ row.algorithm }}</td></tr>
        <tr :class="{ different: isDifferent('order') }"><td>模型阶次</td><td v-for="row in comparisonRows" :key="row.id">{{ row.order }}</td></tr>
        <tr class="different"><td>R²</td><td v-for="row in comparisonRows" :key="row.id"><strong>{{ row.r2.toFixed(3) }}</strong></td></tr><tr class="different"><td>AIC</td><td v-for="row in comparisonRows" :key="row.id">{{ row.aic.toFixed(1) }}</td></tr>
      </tbody></table></div></section>
      <div class="comparison-chart-grid"><section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Goodness of Fit</span><h2>拟合度 R²</h2></div></div><div ref="fitChart" class="experiment-chart"></div></section><section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Residual Diagnostics</span><h2>残差分布箱线图</h2></div></div><div ref="residualChart" class="experiment-chart"></div></section></div>
      <section class="panel"><div class="section-heading compact"><div><span class="section-kicker">Multi-run Prediction</span><h2>预测值 vs 实测值</h2></div><StatusPill tone="brand">{{ comparisonRows.length }} 个版本叠加</StatusPill></div><div ref="predictionChart" class="prediction-chart"></div></section>
    </section>
  </div>
</template>

<style scoped>
.experiment-notice { display: flex; align-items: center; gap: 8px; padding: 10px 13px; color: #8b5d0b; font-size: 11px; border: 1px solid #f3d59a; border-radius: 8px; background: #fffaf0; }.experiment-notice button { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; color: inherit; border: 0; background: transparent; }
.experiment-filters { display: flex; gap: 7px; }.experiment-filters select { min-height: 32px; padding: 0 8px; color: #475569; font-size: 10px; border: 1px solid var(--line); border-radius: 7px; background: #fff; }.experiment-loading { display: flex; justify-content: center; align-items: center; gap: 8px; min-height: 260px; color: var(--muted); }
.experiment-table { min-width: 1160px; }.experiment-table td { font-size: 10px; }.experiment-table td small, .experiment-table td code { display: block; }.experiment-table td small { margin-top: 4px; color: var(--muted); font-size: 8px; }.experiment-r2 { color: #1769c2; font-size: 13px; }.annotation-cell { display: grid; grid-template-columns: 85px 150px; gap: 5px; }.annotation-cell select, .annotation-cell input { min-width: 0; height: 29px; padding: 0 6px; font-size: 9px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
.parameter-diff { min-width: 650px; }.parameter-diff tr.different td { background: #fff8e7; }.parameter-diff tr.different td:first-child { color: #9a6100; font-weight: 700; }.comparison-chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.experiment-chart { height: 285px; }.prediction-chart { height: 350px; }
@media (max-width: 800px) { .experiment-filters { width: 100%; overflow-x: auto; }.comparison-chart-grid { grid-template-columns: 1fr; }.page-heading-actions .status-pill { display: none; } }
</style>
