<script setup>
import { computed, nextTick, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import IntegratedEvidencePanel from '../components/IntegratedEvidencePanel.vue'
import FrequencyAnalysisPanel from '../components/FrequencyAnalysisPanel.vue'
import { announcePipelineUpdate, rerunPipeline } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate'])

const modelType = computed(() => liveModel.value?.config?.family ?? '等待运行')
const training = ref(false)
const comparisonOpen = ref(false)
const correlationDetailOpen = ref(false)
const activeAnalysisTab = ref('identification')
const { latestRun } = useLatestPipelineRun()
const liveModel = computed(() => latestRun.value?.results?.modeling ?? null)
const liveMetrics = computed(() => liveModel.value?.metrics?.test ?? null)
const mimoOutputs = computed(() => liveModel.value?.mimo?.outputs ?? [])
const optimization = computed(() => latestRun.value?.results?.optimization ?? {})
const modelComparisons = computed(() => {
  const rows = optimization.value.iterations ?? optimization.value.history ?? []
  if (rows.length) return rows.filter(row => row.status === 'completed').map(row => ({ ...row, selected: row.round === optimization.value.best_round })).sort((a, b) => b.score - a.score).slice(0, 6)
  if (!liveModel.value) return []
  return [{ round: '当前', r2: liveMetrics.value?.r2, rmse: liveMetrics.value?.rmse, mae: liveMetrics.value?.mae, selected: true }]
})
const demoMatrixLabels = [props.project.targetTag, props.project.mvTag, 'AIR_RATIO', 'ZONE_PRESS', props.project.disturbanceTag]
const demoMatrix = [
  [1, 0.82, 0.76, 0.44, -0.69],
  [0.82, 1, 0.91, 0.35, -0.41],
  [0.76, 0.91, 1, 0.38, -0.36],
  [0.44, 0.35, 0.38, 1, -0.22],
  [-0.69, -0.41, -0.36, -0.22, 1],
]
const matrixLabels = computed(() => liveModel.value?.collinearity?.labels?.length ? liveModel.value.collinearity.labels : demoMatrixLabels)
const matrix = computed(() => liveModel.value?.collinearity?.matrix?.length ? liveModel.value.collinearity.matrix : demoMatrix)

const demoLagRows = computed(() => [
  { input: props.project.mvTag, output: props.project.targetTag, lagSamples: 24, lag: '24 点', corr: 0.82, method: '段内历史输入补偿', action: '保留主变量' },
  { input: 'AIR_FUEL_RATIO', output: props.project.targetTag, lagSamples: 18, lag: '18 点', corr: 0.76, method: '段内历史输入补偿', action: '保留' },
  { input: 'ZONE_PRESSURE', output: props.project.targetTag, lagSamples: 10, lag: '10 点', corr: 0.44, method: '低权重补偿', action: '降权' },
  { input: props.project.disturbanceTag, output: props.project.targetTag, lagSamples: 31, lag: '31 点', corr: -0.69, method: '段内历史输入补偿', action: '保留扰动' },
])
const lagRows = computed(() => liveModel.value?.lags?.length ? liveModel.value.lags.map((row) => ({
  input: row.input,
  output: row.output,
  lagSamples: Number(row.delay_samples),
  lag: `${Number(row.delay_samples)} 点`,
  corr: Number(row.correlation).toFixed(3),
  method: Number(row.delay_samples) >= 0 ? '使用历史输入，段内对齐' : '历史任务负时滞，需重跑',
  action: row.boundary_hit ? '命中上界，复核' : '训练段估计',
})) : demoLagRows.value)
const lagAxisMax = computed(() => Math.max(
  1,
  Number(liveModel.value?.config?.max_lag ?? 0),
  ...lagRows.value.map(row => Number(row.lagSamples) || 0),
))
const lagAxisTicks = computed(() => Array.from({ length: 5 }, (_, index) =>
  `${Math.round(lagAxisMax.value * index / 4)} 点`))
const lagPercent = row => `${Math.min(100, Math.max(0, Number(row.lagSamples) / lagAxisMax.value * 100))}%`

const variableActions = computed(() => {
  const vifRows = liveModel.value?.collinearity?.vif ?? []
  const dropped = new Set(liveModel.value?.collinearity?.recommendations?.drop ?? [])
  return vifRows.slice(0, 6).map((row) => ({
    variable: row.variable,
    pair: '其他输入',
    corr: Number(row.r_squared ?? 0).toFixed(3),
    vif: Number(row.vif ?? 0).toFixed(2),
    action: dropped.has(row.variable) ? '剔除' : '保留',
    reason: dropped.has(row.variable) ? 'VIF或相关性超过阈值' : '满足当前共线性准入规则',
  }))
})

const testDiagnostic = computed(() => liveModel.value?.diagnostics?.test ?? {})
function formatMetric(value) { return value == null ? '—' : Number(value).toFixed(4) }
const plot = computed(() => {
  const rows = (liveModel.value?.prediction_preview ?? []).filter(row => Number.isFinite(row.y_true) && Number.isFinite(row.y_pred))
  if (!rows.length) return { points: 0 }
  const values = rows.flatMap(row => [row.y_true, row.y_pred])
  const min = Math.min(...values), max = Math.max(...values)
  const times = rows.map(row => new Date(row.timestamp).getTime())
  const start = times[0], span = Math.max(1, times.at(-1) - start)
  const path = key => rows.map((row, i) => `${i ? 'L' : 'M'}${(55 + 760 * (times[i] - start) / span).toFixed(2)} ${(255 - 220 * (row[key] - min) / Math.max(.001, max - min)).toFixed(2)}`).join(' ')
  return { points: rows.length, actual: path('y_true'), predicted: path('y_pred'), min: min.toFixed(1), max: max.toFixed(1), start: rows[0].timestamp.slice(11), end: rows.at(-1).timestamp.slice(11) }
})

async function trainModel() {
  if (training.value) return
  training.value = true
  try {
    const latest = latestRun.value
    if (!latest) throw new Error('当前场景尚无运行数据，请先在“数据资产”页面上传CSV。')
    const snapshot = await rerunPipeline(latest.run_id, { maxLag: 60 })
    latestRun.value = snapshot
    announcePipelineUpdate(snapshot)
    const metrics = snapshot.results?.modeling?.metrics?.test ?? {}
    emit('notify', { tone: snapshot.results?.review?.passed ? 'success' : 'warning', title: `${snapshot.results?.modeling?.config?.family ?? '候选'} 训练完成`, message: `独立测试 R² ${Number(metrics.r2 ?? 0).toFixed(3)}，RMSE ${Number(metrics.rmse ?? 0).toFixed(3)}。` })
  } catch (error) {
    emit('notify', { tone: 'warning', title: '模型训练失败', message: error.message })
  } finally {
    training.value = false
  }
}

function heatColor(value) {
  const strength = Math.abs(value)
  if (value < 0) return `rgba(124, 58, 237, ${0.12 + strength * 0.72})`
  return `rgba(14, 116, 217, ${0.1 + strength * 0.78})`
}

async function showFrequencyAnalysis() {
  activeAnalysisTab.value = 'frequency'
  await nextTick()
  window.dispatchEvent(new CustomEvent('processpilot:charts-visible'))
}
</script>

<template>
  <div class="view-stack modeling-view">
    <PageHeader
      eyebrow="Lag Decoupling & System Identification"
      title="时滞解耦与系统辨识"
      description="自动估算多变量时间滞后、检测共线性并执行智能降维，使用优选数据完成模型训练、验证与可解释评价。"
    >
      <template #actions>
        <button class="btn btn-secondary" type="button" :aria-expanded="comparisonOpen" @click="comparisonOpen = !comparisonOpen">{{ comparisonOpen ? '收起模型对比' : '比较模型版本' }}</button>
        <button class="btn btn-primary" type="button" :disabled="training" @click="trainModel"><AppIcon :name="training ? 'loop' : 'play'" :class="{ spinning: training }" />{{ training ? '训练与验证中…' : '训练并验证模型' }}</button>
      </template>
    </PageHeader>

    <IntegratedEvidencePanel module="modeling" />

    <div class="model-analysis-tabs" role="tablist" aria-label="模型分析视图">
      <button type="button" role="tab" :aria-selected="activeAnalysisTab === 'identification'" :class="{ 'is-active': activeAnalysisTab === 'identification' }" @click="activeAnalysisTab = 'identification'"><AppIcon name="model" :size="16" />时域辨识与解耦</button>
      <button type="button" role="tab" :aria-selected="activeAnalysisTab === 'frequency'" :class="{ 'is-active': activeAnalysisTab === 'frequency' }" @click="showFrequencyAnalysis"><AppIcon name="segments" :size="16" />频率特性分析</button>
    </div>

    <div v-show="activeAnalysisTab === 'identification'" class="view-stack">

    <section v-if="comparisonOpen" class="panel model-comparison-panel">
      <div class="section-heading compact"><div><span class="section-kicker">当前任务真实产物</span><h2>模型版本与候选轮次对比</h2></div><StatusPill :tone="modelComparisons.length ? 'success' : 'neutral'">{{ modelComparisons.length }} 个记录</StatusPill></div>
      <div v-if="modelComparisons.length" class="table-wrap compact-table-wrap">
        <table class="data-table"><thead><tr><th>轮次/版本</th><th>验证 R²</th><th>验证 RMSE</th><th>验证 MAE</th><th>结论</th></tr></thead><tbody>
          <tr v-for="(row, index) in modelComparisons" :key="row.round ?? row.iteration ?? index"><td><strong>{{ row.round ?? row.iteration ?? index + 1 }}</strong></td><td>{{ Number(row.r2 ?? row.score ?? 0).toFixed(3) }}</td><td>{{ Number(row.rmse ?? 0).toFixed(3) }}</td><td>{{ Number(row.mae ?? 0).toFixed(3) }}</td><td><StatusPill :tone="row.selected ? 'success' : 'neutral'">{{ row.selected ? '验证选中' : '候选' }}</StatusPill></td></tr>
        </tbody></table>
      </div>
      <p v-else class="empty-state">尚无真实模型记录，请先上传 CSV 并运行辨识流水线。</p>
    </section>

    <section class="metric-grid five-col">
      <article class="metric-card compact-card"><span class="metric-label">输入变量</span><div class="metric-value">{{ liveModel?.input_cols?.length ?? '—' }} → {{ liveModel?.selected_inputs?.length ?? '—' }}</div><p>共线性筛选结果</p></article>
      <article class="metric-card compact-card"><span class="metric-label">最大辨识时滞</span><div class="metric-value">{{ liveModel?.config?.max_lag ?? '—' }} <small>点</small></div><p>真实任务搜索范围</p></article>
      <article class="metric-card compact-card accent-blue"><span class="metric-label">独立测试 R²</span><div class="metric-value">{{ liveMetrics ? Number(liveMetrics.r2).toFixed(3) : '—' }}</div><p>测试集真实指标</p></article>
      <article class="metric-card compact-card"><span class="metric-label">RMSE / MAE</span><div class="metric-value metric-value-text">{{ liveMetrics ? `${Number(liveMetrics.rmse).toFixed(3)} / ${Number(liveMetrics.mae).toFixed(3)}` : '—' }}</div><p>测试集误差</p></article>
      <article class="metric-card compact-card"><span class="metric-label">候选模型</span><div class="metric-value metric-value-text">{{ modelType }}</div><p>{{ liveModel?.output_col ?? '等待运行' }}</p></article>
    </section>

    <section v-if="mimoOutputs.length > 1" class="panel">
      <div class="section-heading compact"><div><span class="section-kicker">MIMO RESPONSE EVIDENCE</span><h2>共享输入的多输出 ARX 模型组</h2></div><StatusPill :tone="liveModel?.mimo?.response_ready_outputs === liveModel?.mimo?.requested_outputs?.length ? 'success' : 'warning'">{{ liveModel?.mimo?.response_ready_outputs ?? 0 }}/{{ liveModel?.mimo?.requested_outputs?.length }} 输出响应就绪</StatusPill></div>
      <div class="table-wrap compact-table-wrap">
        <table class="data-table"><thead><tr><th>输出</th><th>模型</th><th>外部输入</th><th>测试 R²</th><th>RMSE</th><th>10步 R²</th><th>自由仿真 R²</th><th>状态</th></tr></thead><tbody>
          <tr v-for="row in mimoOutputs" :key="row.output_col"><td><code>{{ row.output_col }}</code><small v-if="row.primary"> 主输出</small></td><td>{{ row.family ?? '—' }}</td><td>{{ row.fitted_inputs?.length ?? 0 }}</td><td>{{ formatMetric(row.test?.r2) }}</td><td>{{ formatMetric(row.test?.rmse) }}</td><td>{{ formatMetric(row.response?.multi_step?.metrics?.r2) }}</td><td>{{ formatMetric(row.response?.free_simulation?.metrics?.r2) }}</td><td><StatusPill :tone="row.status === 'completed' ? 'success' : 'danger'">{{ row.status === 'completed' ? '完成' : '失败' }}</StatusPill></td></tr>
        </tbody></table>
      </div>
    </section>
    <div class="content-grid content-grid-5-7">
      <section class="panel correlation-panel">
        <div class="section-heading compact"><div><span class="section-kicker">变量相关性热力图</span><h2>共线性结构</h2></div><StatusPill tone="warning">2 对高共线</StatusPill></div>
        <div class="heatmap-wrap" role="table" aria-label="变量相关性矩阵">
          <div class="heatmap-corner"></div>
          <div v-for="label in matrixLabels" :key="`col-${label}`" class="heatmap-label col-label" role="columnheader">{{ label }}</div>
          <template v-for="(row, rowIndex) in matrix" :key="`row-${rowIndex}`">
            <div class="heatmap-label row-label" role="rowheader">{{ matrixLabels[rowIndex] }}</div>
            <div v-for="(value, colIndex) in row" :key="`${rowIndex}-${colIndex}`" class="heatmap-cell" role="cell" :style="{ background: heatColor(value), color: Math.abs(value) > .56 ? '#fff' : '#1e293b' }">{{ value.toFixed(2) }}</div>
          </template>
        </div>
        <div class="heatmap-scale"><span>-1.0 负相关</span><i></i><span>0</span><b></b><span>+1.0 正相关</span></div>
        <div class="agent-tip"><span><AppIcon name="spark" /></span><p><strong>Agent 发现</strong>本次任务从 {{ liveModel?.input_cols?.length ?? 0 }} 个候选输入中保留 {{ liveModel?.selected_inputs?.length ?? 0 }} 个特征；具体共线性证据已写入模型产物。</p></div>
      </section>

      <section class="panel lag-panel">
        <div class="section-heading compact"><div><span class="section-kicker">多变量时滞估算</span><h2>相对 {{ project.targetTag }} 的最佳补偿</h2></div><button class="text-button" type="button" :aria-expanded="correlationDetailOpen" @click="correlationDetailOpen = !correlationDetailOpen">{{ correlationDetailOpen ? '收起相关证据' : '查看互相关证据' }} <AppIcon name="arrow" :size="15" /></button></div>
        <div class="lag-visual">
          <div class="lag-axis"><span v-for="tick in lagAxisTicks" :key="tick">{{ tick }}</span></div>
          <div v-for="row in lagRows" :key="row.input" class="lag-row">
            <span>{{ row.input }}</span><div><i :style="{ left: lagPercent(row) }"></i><b :style="{ width: lagPercent(row) }"></b></div><strong>{{ row.lag }}</strong>
          </div>
        </div>
        <div class="table-wrap compact-table-wrap">
          <table class="data-table">
            <caption class="visually-hidden">变量时滞估算与补偿方案</caption>
            <thead><tr><th>输入变量</th><th>相关度</th><th>补偿方案</th><th>决策</th></tr></thead>
            <tbody><tr v-for="row in lagRows" :key="row.input"><td><code>{{ row.input }}</code></td><td><strong>{{ row.corr }}</strong></td><td>{{ row.method }}</td><td><StatusPill :tone="row.action === '降权' ? 'warning' : 'success'">{{ row.action }}</StatusPill></td></tr></tbody>
          </table>
        </div>
        <div v-if="correlationDetailOpen" class="correlation-evidence" aria-label="互相关峰值证据">
          <div v-for="row in lagRows" :key="`corr-${row.input}`"><span>{{ row.input }}</span><i><b :style="{ width: `${Math.min(100, Math.abs(Number(row.corr)) * 100)}%` }"></b></i><strong>{{ row.corr }}</strong><small>峰值时滞 {{ row.lag }}</small></div>
        </div>
      </section>
    </div>

    <div class="content-grid content-grid-4-8">
      <section class="panel reduction-panel">
        <div class="section-heading compact"><div><span class="section-kicker">智能降维</span><h2>变量处理建议</h2></div><StatusPill tone="success">已应用</StatusPill></div>
        <div class="dimension-summary"><div class="dimension-number"><strong>{{ liveModel?.input_cols?.length ?? 0 }}</strong><span>候选输入</span></div><div class="dimension-arrow"><AppIcon name="arrow" /></div><div class="dimension-number is-final"><strong>{{ liveModel?.selected_inputs?.length ?? 0 }}</strong><span>模型特征</span></div></div>
        <div class="variable-actions">
          <article v-for="item in variableActions" :key="item.variable"><div><code>{{ item.variable }}</code><span>↔ {{ item.pair }}</span></div><StatusPill :tone="item.action === '剔除' ? 'danger' : item.action === '合并' ? 'warning' : 'success'">{{ item.action }}</StatusPill><p>回归 R²={{ item.corr }} · VIF={{ item.vif }} · {{ item.reason }}</p></article>
        </div>
      </section>

      <section class="panel identification-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">系统辨识与验证</span><h2>{{ project.target }}：独立测试单步预测</h2></div>
          <div class="model-controls"><strong>{{ modelType }} · {{ liveModel?.config?.output_order ?? '—' }} 阶</strong><span>训练 60% / 验证 20% / 测试 20%</span></div>
        </div>
        <p>曲线来自选中模型的独立测试产物；测试指标不参与寻优。实际外部输入 {{ liveModel?.fitted_inputs?.length ?? '—' }} 个。</p>
        <div v-if="plot.points" class="chart-legend"><span>实测值</span><span>单步预测值</span></div>
        <svg v-if="plot.points" class="line-chart identification-chart" viewBox="0 0 840 300" role="img" aria-label="独立测试真实预测曲线">
          <g class="chart-grid"><path d="M55 35H815M55 145H815M55 255H815" /></g>
          <path class="chart-line actual-line" :d="plot.actual" />
          <path class="chart-line predicted-line" :d="plot.predicted" />
          <g class="chart-labels"><text x="5" y="40">{{ plot.max }}</text><text x="5" y="255">{{ plot.min }}</text><text x="55" y="285">{{ plot.start }}</text><text x="700" y="285">{{ plot.end }}</text></g>
        </svg>
        <p v-else class="empty-state">当前任务没有真实预测曲线，请重跑新版流水线。</p>
        <div class="report-kpis">
          <div><span>持续值基线 RMSE</span><strong>{{ formatMetric(testDiagnostic.persistence?.rmse) }}</strong></div>
          <div><span>10步 RMSE</span><strong>{{ formatMetric(testDiagnostic.multi_step?.metrics?.rmse) }}</strong></div>
          <div><span>自由仿真 R²</span><strong>{{ formatMetric(testDiagnostic.free_simulation?.metrics?.r2) }}</strong></div>
        </div>
        <div class="model-result-row">
          <div><span>训练 R²</span><strong>{{ liveModel ? Number(liveModel.metrics?.train?.r2 ?? 0).toFixed(3) : '—' }}</strong><small>训练集</small></div>
          <div><span>测试 R²</span><strong>{{ liveMetrics ? Number(liveMetrics.r2).toFixed(3) : '—' }}</strong><small>独立测试集</small></div>
          <div><span>RMSE</span><strong>{{ liveMetrics ? Number(liveMetrics.rmse).toFixed(3) : '—' }}</strong><small>真实输出单位</small></div>
          <div><span>MAE</span><strong>{{ liveMetrics ? Number(liveMetrics.mae).toFixed(3) : '—' }}</strong><small>真实输出单位</small></div>
          <StatusPill :tone="latestRun?.results?.review?.passed ? 'success' : 'warning'"><AppIcon :name="latestRun?.results?.review?.passed ? 'check' : 'alert'" :size="14" /> {{ latestRun?.results?.review?.conclusion ?? '等待Agent评审' }}</StatusPill>
        </div>
      </section>
    </div>

    <div class="model-footer-card">
      <div><span class="model-ready-icon"><AppIcon name="check" /></span><p><strong>任务 {{ latestRun?.run_id ?? '—' }} 的 {{ modelType }} 候选已完成评估</strong><small>测试 R² {{ liveMetrics ? Number(liveMetrics.r2).toFixed(3) : '—' }}，评审结论：{{ latestRun?.results?.review?.conclusion ?? '等待评审' }}。</small></p></div>
      <button class="btn btn-primary" type="button" @click="emit('navigate', '/closed-loop-optimization/')">进入闭环寻优 <AppIcon name="arrow" /></button>
    </div>
    </div>

    <FrequencyAnalysisPanel v-show="activeAnalysisTab === 'frequency'" :model="liveModel" />
  </div>
</template>

<style scoped>
.model-comparison-panel { overflow: hidden; }
.empty-state { padding: 22px; color: #64748b; text-align: center; }
.correlation-evidence { display: grid; gap: 9px; margin-top: 14px; padding: 14px; border: 1px solid #dbeafe; border-radius: 7px; background: #f8fbff; }
.correlation-evidence > div { display: grid; grid-template-columns: minmax(100px, 1.2fr) minmax(90px, 2fr) 55px minmax(110px, 1fr); align-items: center; gap: 9px; font-size: 12px; }
.correlation-evidence i { height: 7px; overflow: hidden; border-radius: 4px; background: #e2e8f0; }
.correlation-evidence b { display: block; height: 100%; background: #2563eb; }
.correlation-evidence small { color: #64748b; }
.model-analysis-tabs { display: inline-flex; align-self: flex-start; gap: 4px; padding: 4px; border: 1px solid var(--line); border-radius: 9px; background: #eef3f9; }
.model-analysis-tabs button { display: inline-flex; align-items: center; gap: 7px; min-height: 36px; padding: 0 13px; color: #5f7186; font-size: 11px; font-weight: 650; border: 0; border-radius: 6px; background: transparent; }
.model-analysis-tabs button.is-active { color: #174f9b; background: #fff; box-shadow: 0 2px 8px rgba(32,64,99,.08); }
@media (max-width: 680px) { .correlation-evidence > div { grid-template-columns: 1fr 1fr; } }
</style>
