<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import IntegratedEvidencePanel from '../components/IntegratedEvidencePanel.vue'
import { formatNumber } from '../data/projectData'
import { announcePipelineUpdate, artifactUrl, rerunPipeline, uploadPipelineFile } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildSceneState } from '../composables/useSceneBinding'
import { buildSimulationCsv } from '../utils/simulationCsv'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate', 'scene-detected'])

const fileInput = ref(null)
const isGenerating = ref(false)
const uploading = ref(false)
const dragActive = ref(false)
const generatedDataset = ref(null)
const { latestRun } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(props.project, latestRun.value))
const simulation = ref({ steady: 45, step: 18, noise: 3, anomalies: 12 })
const fileFilter = ref('all')
const chartRange = ref('6h')
const mappingDraft = ref({})
const reviewScenario = ref('')

function buildFiles(project) {
  if (project.scenarioId === 'blast_furnace') return [
    { id: 1, name: '1_blast_furnace_data_first_dataset.xlsx', source: 'Mendeley Data · 原始过程数据', rows: 29602, variables: 27, size: '公开数据', period: '2013-01-01 — 2016-05-18', quality: 100, status: '原始只读' },
    { id: 2, name: 'Si laboratory measurements', source: '同源实验室化验', rows: 16589, variables: 1, size: '非等间隔', period: '中位间隔约 99 min', quality: 100, status: '因果对齐' },
    { id: 3, name: 'blast_furnace_real_720h.csv', source: '真实数据演示切片', rows: 720, variables: 32, size: '约 160 KB', period: '2013-01-01 — 2013-01-30', quality: 97.6, status: '可直接运行', downloadUrl: project.source?.demoUrl },
  ]
  if (project.scenarioId === 'debutanizer_column') return [
    { id: 1, name: 'debutanizer_process_data.csv', source: 'Fortuna 等公开工业基准', rows: 2394, variables: 8, size: '授权后本地导入', period: '1 min 等间隔样本', quality: null, status: '待授权数据' },
  ]
  if (project.scenarioId === 'industrial_dryer') return [
    { id: 1, name: '工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv', source: '团队合成验收数据', rows: 867, variables: 6, size: '约 110 KB', period: '867 个连续采样点', quality: 96.8, status: '可直接运行' },
  ]
  return [
    { id: 1, name: `${project.code}_historian.csv`, source: 'DCS Historian', rows: project.rows, variables: project.variables, size: '18.6 MB', period: project.timeRange, quality: 96.4, status: '已解析' },
    { id: 2, name: `${project.code}_batch_context.csv`, source: 'MES', rows: 8640, variables: 8, size: '2.4 MB', period: project.timeRange, quality: 98.8, status: '已对齐' },
    { id: 3, name: `${project.code}_lab_quality.csv`, source: 'LIMS', rows: 1260, variables: 6, size: '684 KB', period: project.timeRange, quality: 94.1, status: '已对齐' },
  ]
}

const files = ref(buildFiles(props.project))
watch(() => props.project.id, () => { files.value = buildFiles(props.project) })

const totalRows = computed(() => files.value.reduce((sum, file) => sum + Number(file.rows || 0), 0))
const liveStandard = computed(() => latestRun.value?.results?.standardization ?? null)
const liveCleaning = computed(() => latestRun.value?.results?.cleaning ?? null)
const liveFieldCount = computed(() => liveStandard.value?.mapping?.mappings?.length ?? props.project.variables)
const visibleFiles = computed(() => {
  if (fileFilter.value === 'recent') return files.value.slice(0, 2)
  if (fileFilter.value === 'quality') return files.value.filter((file) => Number(file.quality ?? 0) >= 95)
  return files.value
})
const reviewMappings = computed(() => (liveStandard.value?.mapping?.mappings ?? []).filter((item) => item.status !== 'matched'))
const scenarioCandidates = computed(() => liveStandard.value?.detection?.candidates ?? [])
const dictionary = computed(() => liveStandard.value?.dictionary ?? [])

const dataSceneInfo = computed(() => sceneState.value.data_scene)
const mismatchText = computed(() => sceneState.value.is_mismatch ? sceneState.value.mismatch_text : '')

watch(liveStandard, (standard) => {
  reviewScenario.value = standard?.scenario?.scenario_id ?? ''
  mappingDraft.value = Object.fromEntries((standard?.mapping?.mappings ?? []).filter((item) => item.status !== 'matched').map((item) => [item.raw, item.standard ?? '__ignore__']))
}, { immediate: true })

function setFileFilter(filter) {
  fileFilter.value = filter
  emit('notify', { tone: 'info', title: '数据源筛选已更新', message: filter === 'recent' ? '显示最近更新的 2 个数据资产。' : filter === 'quality' ? '仅显示质量分不低于 95 的数据。' : '已显示全部数据源。' })
}

function setChartRange(range) {
  chartRange.value = range
  emit('notify', { tone: 'info', title: '时序窗口已切换', message: `当前预览范围：${range === '6h' ? '6 小时' : range === '24h' ? '24 小时' : '全量数据'}。` })
}

function chooseFile() {
  fileInput.value?.click()
}

function createPendingFile(file, overrides = {}) {
  return {
    id: Date.now(),
    name: file.name,
    source: overrides.source ?? '本地上传',
    rows: 0,
    variables: 0,
    size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
    period: '等待解析',
    quality: null,
    status: '执行中',
    ...overrides,
  }
}

async function runPipelineFile(file, pending = createPendingFile(file)) {
  if (!files.value.some((item) => item.id === pending.id)) files.value.unshift(pending)
  uploading.value = true
  try {
    latestRun.value = await uploadPipelineFile(file, { scenarioId: 'auto', projectSceneId: props.project.scenarioId, instruction: '请根据上传数据识别工业场景并执行APC建模', resampleRule: props.project.resampleRule, maxLag: props.project.maxLag })
    const standard = latestRun.value.results?.standardization
    const quality = latestRun.value.results?.cleaning?.overall_score
    pending.rows = latestRun.value.results?.cleaning?.cleaned_row_count ?? standard?.source_row_count ?? 0
    pending.variables = standard?.mapping?.mappings?.filter((item) => item.status === 'matched').length ?? 0
    pending.period = standard?.scenario?.scenario_name ?? '已自动识别场景'
    pending.quality = quality
    pending.status = latestRun.value.results?.review?.passed ? '流水线通过' : '需要复核'
    announcePipelineUpdate(latestRun.value)
    if (latestRun.value.status === 'needs_review') {
      emit('notify', {
        tone: 'warning',
        title: '数据未进入建模',
        message: latestRun.value.review_required?.message || `${file.name} 的场景或字段映射需要人工确认。`,
      })
    } else {
      emit('notify', { tone: 'success', title: '真实流水线执行完成', message: `${file.name} 已完成字段统一、清洗优选、系统辨识和Agent评审。` })
      const scenarioId = standard?.scenario?.scenario_id
      if (scenarioId) emit('scene-detected', { scenarioId, runId: latestRun.value.run_id, path: '/digital-twin/' })
    }
  } catch (error) {
    pending.status = '执行失败'
    emit('notify', { tone: 'warning', title: '流水线执行失败', message: error.message })
  } finally {
    uploading.value = false
  }
}

async function applyMappingReview() {
  if (!latestRun.value?.run_id || uploading.value) return
  uploading.value = true
  try {
    const scenarioChanged = reviewScenario.value !== liveStandard.value?.scenario?.scenario_id
    latestRun.value = await rerunPipeline(latestRun.value.run_id, {
      scenarioId: reviewScenario.value,
      overrides: scenarioChanged ? {} : mappingDraft.value,
    })
    announcePipelineUpdate(latestRun.value)
    emit('notify', { tone: latestRun.value.status === 'completed' ? 'success' : 'warning', title: scenarioChanged ? '场景字段已刷新' : '人工映射已应用', message: scenarioChanged ? '已按新场景刷新标准字段，请继续确认映射。' : latestRun.value.status === 'completed' ? '已使用审核后的映射重新执行流水线。' : '映射已保存到运行记录，仍有门禁项需要复核。' })
    if (latestRun.value.status === 'completed') {
      const scenarioId = latestRun.value.results?.standardization?.scenario?.scenario_id
      if (scenarioId) emit('scene-detected', { scenarioId, runId: latestRun.value.run_id, path: '/digital-twin/' })
    }
  } catch (error) {
    emit('notify', { tone: 'warning', title: '人工映射执行失败', message: error.message })
  } finally {
    uploading.value = false
  }
}

async function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await runPipelineFile(file)
  event.target.value = ''
}

async function handleDrop(event) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.csv')) {
    emit('notify', { tone: 'warning', title: '文件格式不支持', message: '请拖入 CSV 文件。' })
    return
  }
  await runPipelineFile(file)
}

function removeFile(file) {
  files.value = files.value.filter((item) => item.id !== file.id)
  emit('notify', { tone: 'neutral', title: '文件已移出项目', message: `${file.name} 的演示记录已删除。` })
}

function downloadSimulation(file) {
  const url = URL.createObjectURL(file)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = file.name
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000)
}

async function generateSimulation(action = 'download') {
  if (isGenerating.value) return
  isGenerating.value = true
  try {
    await new Promise((resolve) => window.setTimeout(resolve, 80))
    const result = buildSimulationCsv(props.project, simulation.value)
    const file = new File([result.csv], result.name, { type: 'text/csv;charset=utf-8' })
    const pending = createPendingFile(file, {
      source: '仿真生成器',
      rows: result.rowCount,
      variables: result.variableCount,
      period: result.period,
      status: action === 'run' ? '执行中' : '已生成',
    })
    files.value.unshift(pending)
    generatedDataset.value = { file, ...result }

    if (action === 'run') {
      await runPipelineFile(file, pending)
    } else {
      downloadSimulation(file)
      pending.status = '已下载'
      emit('notify', { tone: 'success', title: '仿真 CSV 已生成并下载', message: `${result.rowCount.toLocaleString('zh-CN')} 行数据·${result.summary}。` })
    }
  } catch (error) {
    emit('notify', { tone: 'warning', title: '仿真数据生成失败', message: error.message })
  } finally {
    isGenerating.value = false
  }
}

function handleGlobalCommand(event) {
  if (event.detail?.action === 'generate-simulation') generateSimulation('download')
}
onMounted(() => window.addEventListener('processpilot:command', handleGlobalCommand))
onBeforeUnmount(() => window.removeEventListener('processpilot:command', handleGlobalCommand))
</script>

<template>
  <div class="view-stack data-assets-view">
    <PageHeader
      eyebrow="Industrial Time-series Assets"
      title="数据资产与仿真测试集"
      description="统一管理多变量工业时序文件，完成字段识别、质量画像和跨系统时间轴对齐，并生成符合赛题要求的合成测试数据。"
    >
      <template #actions>
        <input ref="fileInput" class="visually-hidden" type="file" accept=".csv,text/csv" @change="handleFile" />
        <button class="btn btn-secondary" type="button" :disabled="uploading" @click="chooseFile"><AppIcon :name="uploading ? 'loop' : 'upload'" :class="{ spinning: uploading }" />{{ uploading ? '流水线运行中…' : '上传并运行 CSV' }}</button>
        <button class="btn btn-primary" type="button" :disabled="isGenerating || uploading" @click="generateSimulation('download')">
          <AppIcon :name="isGenerating ? 'loop' : 'download'" :class="{ spinning: isGenerating }" />{{ isGenerating ? '生成中…' : '生成并下载 CSV' }}
        </button>
      </template>
    </PageHeader>

      <IntegratedEvidencePanel module="standardization" />

      <section v-if="mismatchText" class="panel scene-mismatch-panel">
        <AppIcon name="alert" :size="15" />
        <p>{{ mismatchText }}</p>
      </section>

    <section v-if="latestRun" class="panel pipeline-run-panel">
      <div class="section-heading compact"><div><span class="section-kicker">真实执行任务</span><h2>{{ latestRun.original_name }}</h2></div><StatusPill :tone="latestRun.status === 'completed' ? 'success' : 'warning'" dot>{{ latestRun.status === 'completed' ? '全部完成' : '运行异常' }}</StatusPill></div>
      <div class="pipeline-stage-grid">
        <article v-for="stage in latestRun.stages" :key="stage.key" :class="`is-${stage.status}`"><span>{{ stage.label }}</span><strong>{{ stage.status === 'completed' ? '完成' : stage.status === 'failed' ? '失败' : stage.status === 'running' ? '执行中' : '未执行' }}</strong><small>{{ stage.message }}</small></article>
      </div>
      <div v-if="latestRun.status === 'completed'" class="pipeline-artifacts">
        <a :href="artifactUrl(latestRun.run_id, 'standardized_csv')">下载标准化数据</a>
        <a :href="artifactUrl(latestRun.run_id, 'mapping_csv')">下载字段映射</a>
        <a :href="artifactUrl(latestRun.run_id, 'cleaned_csv')">下载清洗数据</a>
        <a :href="artifactUrl(latestRun.run_id, 'segments_csv')">下载动态段</a>
        <a :href="artifactUrl(latestRun.run_id, 'metrics_json')">下载模型指标</a>
      </div>
    </section>

    <section v-if="latestRun?.status === 'needs_review' && liveStandard" class="panel mapping-review-panel">
      <div class="section-heading compact"><div><span class="section-kicker">Human mapping review</span><h2>人工字段映射</h2></div><StatusPill tone="warning">{{ reviewMappings.length }} 项待处理</StatusPill></div>
      <p class="panel-description">系统不会猜测不透明工厂位号。请选择已确认的场景和字段含义；选择“忽略该字段”会把它保留在审计记录中但不送入建模。</p>
      <label class="mapping-review-scenario"><span>确认场景</span><select v-model="reviewScenario"><option v-for="candidate in scenarioCandidates" :key="candidate.scenario_id" :value="candidate.scenario_id">{{ candidate.scenario_name }} · {{ (candidate.confidence * 100).toFixed(1) }}%</option></select></label>
      <div class="mapping-review-grid">
        <label v-for="item in reviewMappings" :key="item.raw"><span>{{ item.raw }}</span><small>{{ item.method }} · {{ (item.confidence * 100).toFixed(1) }}%</small><select v-model="mappingDraft[item.raw]"><option value="__ignore__">忽略该字段</option><option v-for="field in dictionary" :key="field.standard_name" :value="field.standard_name">{{ field.display_name }}（{{ field.standard_name }}）</option></select></label>
      </div>
      <button class="btn btn-primary" type="button" :disabled="uploading || !reviewScenario" @click="applyMappingReview"><AppIcon :name="uploading ? 'loop' : 'check'" :class="{ spinning: uploading }" />保存映射并重新运行</button>
    </section>

    <section class="metric-grid four-col">
      <article class="metric-card"><span class="metric-label">当前数据文件</span><div class="metric-value">{{ latestRun ? 1 : files.length }} <small>个</small></div><p>{{ latestRun?.original_name ?? '演示数据资产' }}</p><span class="metric-trend positive">{{ latestRun?.run_id ?? '等待真实任务' }}</span></article>
      <article class="metric-card"><span class="metric-label">规整数据量</span><div class="metric-value">{{ formatNumber(liveCleaning?.cleaned_row_count ?? totalRows) }}</div><p>{{ liveFieldCount }} 个识别字段</p><span class="metric-trend positive">当前数据场景：{{ dataSceneInfo.display_name }}</span></article>
      <article class="metric-card"><span class="metric-label">综合数据质量</span><div class="metric-value">{{ liveCleaning?.overall_score ?? '—' }}<small> / 100</small></div><p>必需字段覆盖 {{ ((liveStandard?.mapping?.required_coverage ?? 0) * 100).toFixed(0) }}%</p><span class="metric-trend" :class="liveStandard?.data_decision?.status === 'ready' ? 'positive' : 'warning'">{{ liveStandard?.data_decision?.status ?? '等待判断' }}</span></article>
      <article class="metric-card"><span class="metric-label">字段统一结果</span><div class="metric-value metric-value-text">{{ liveStandard?.mapping?.review_count ?? 0 }} 待确认</div><p>{{ liveStandard?.mapping?.unmapped_count ?? 0 }} 未映射 · {{ liveStandard?.mapping?.unit_risk_count ?? 0 }} 单位风险</p><span class="metric-trend positive">数据字典已生成</span></article>
    </section>

    <div class="content-grid content-grid-8-4">
      <section class="panel files-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">数据文件管理</span><h2>项目数据资产</h2></div>
          <div class="table-tools"><button type="button" :class="{ 'is-active': fileFilter === 'all' }" @click="setFileFilter('all')">全部来源</button><button type="button" :class="{ 'is-active': fileFilter === 'recent' }" @click="setFileFilter('recent')">最近更新</button><button class="icon-button" type="button" :class="{ 'is-active': fileFilter === 'quality' }" aria-label="只看高质量数据" title="只看质量分不低于95的数据" @click="setFileFilter('quality')"><AppIcon name="more" /></button></div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <caption class="visually-hidden">项目数据文件列表</caption>
            <thead><tr><th>文件与来源</th><th>规模</th><th>数据时间窗</th><th>质量</th><th>状态</th><th><span class="visually-hidden">操作</span></th></tr></thead>
            <tbody>
              <tr v-for="file in visibleFiles" :key="file.id">
                <td><div class="file-cell"><span class="file-type"><AppIcon name="file" /></span><div><strong>{{ file.name }}</strong><small>{{ file.source }} · {{ file.size }}</small></div></div></td>
                <td><strong>{{ file.rows ? formatNumber(file.rows) : '—' }}</strong><small>{{ file.variables ? `${file.variables} 变量` : '待识别' }}</small></td>
                <td class="period-cell">{{ file.period }}</td>
                <td><span v-if="file.quality" class="quality-score"><i :style="{ '--score': `${file.quality}%` }"></i>{{ file.quality }}</span><span v-else>—</span></td>
                <td><StatusPill :tone="file.status === '待解析' ? 'warning' : 'success'" dot>{{ file.status }}</StatusPill></td>
                <td><button class="icon-button danger-on-hover" type="button" :aria-label="`删除 ${file.name}`" @click="removeFile(file)"><AppIcon name="trash" /></button></td>
              </tr>
            </tbody>
          </table>
          <p v-if="!visibleFiles.length" class="empty-state">当前筛选条件下没有数据资产。</p>
        </div>
        <button class="drop-zone" :class="{ 'is-dragging': dragActive }" type="button" @click="chooseFile" @dragenter.prevent="dragActive = true" @dragover.prevent="dragActive = true" @dragleave.prevent="dragActive = false" @drop.prevent="handleDrop">
          <span><AppIcon name="upload" :size="22" /></span>
          <strong>拖拽 CSV 到这里，或点击选择文件</strong>
          <small>单文件不超过 200 MB · 源文件只读保存 · 自动识别时间戳、变量与质量码</small>
        </button>
      </section>

      <section class="panel simulation-panel">
        <div class="section-heading compact"><div><span class="section-kicker">赛题演示工具</span><h2>仿真测试集生成器</h2></div><StatusPill tone="brand">内置</StatusPill></div>
        <p class="panel-description">生成包含长周期稳态、明确阶跃响应和异常干扰的合成工业数据。</p>
        <div class="control-stack">
          <label><span>稳态占比 <strong>{{ simulation.steady }}%</strong></span><input v-model="simulation.steady" type="range" min="20" max="75" /></label>
          <label><span>阶跃幅度 <strong>{{ simulation.step }}%</strong></span><input v-model="simulation.step" type="range" min="5" max="35" /></label>
          <label><span>噪声强度 <strong>{{ simulation.noise }}σ</strong></span><input v-model="simulation.noise" type="range" min="1" max="6" /></label>
          <label><span>异常干扰 <strong>{{ simulation.anomalies }} 点</strong></span><input v-model="simulation.anomalies" type="range" min="0" max="30" /></label>
        </div>
        <div class="simulation-preview" aria-label="仿真数据构成预览">
          <span class="sim-steady" :style="{ width: `${simulation.steady}%` }">稳态</span>
          <span class="sim-step">阶跃</span><span class="sim-noise">噪声 / 异常</span>
        </div>
        <div class="simulation-actions">
          <button class="btn btn-secondary" type="button" :disabled="isGenerating || uploading" @click="generateSimulation('download')"><AppIcon name="download" />生成并下载 CSV</button>
          <button class="btn btn-primary" type="button" :disabled="isGenerating || uploading" @click="generateSimulation('run')"><AppIcon :name="isGenerating || uploading ? 'loop' : 'play'" :class="{ spinning: isGenerating || uploading }" />{{ uploading ? '流水线运行中…' : '生成并运行流水线' }}</button>
        </div>
        <div v-if="generatedDataset" class="simulation-result">
          <span><AppIcon name="check" /></span>
          <div><strong>{{ generatedDataset.name }}</strong><small>{{ generatedDataset.rowCount.toLocaleString('zh-CN') }} 行 · {{ generatedDataset.variableCount }} 变量 · {{ generatedDataset.summary }}</small></div>
          <button type="button" @click="downloadSimulation(generatedDataset.file)">再次下载</button>
        </div>
      </section>
    </div>

    <div class="content-grid content-grid-7-5">
      <section class="panel timeseries-panel">
        <div class="section-heading compact"><div><span class="section-kicker">多变量时序预览</span><h2>{{ project.target }}与主要输入变量 · {{ chartRange === '6h' ? '6 h' : chartRange === '24h' ? '24 h' : '全量' }}</h2></div><div class="chart-actions"><button :class="{ 'is-active': chartRange === '6h' }" type="button" @click="setChartRange('6h')">6 h</button><button :class="{ 'is-active': chartRange === '24h' }" type="button" @click="setChartRange('24h')">24 h</button><button :class="{ 'is-active': chartRange === 'all' }" type="button" @click="setChartRange('all')">全量</button></div></div>
        <div class="chart-legend"><span><i class="legend-dot target"></i>{{ project.target }}</span><span><i class="legend-dot mv"></i>{{ project.mv }}</span><span><i class="legend-dot dv"></i>{{ project.disturbance }}</span></div>
        <svg class="line-chart" viewBox="0 0 760 250" role="img" :aria-label="`${project.target}、${project.mv}和${project.disturbance}的时序趋势`">
          <defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3b82f6" stop-opacity=".24" /><stop offset="100%" stop-color="#3b82f6" stop-opacity="0" /></linearGradient></defs>
          <g class="chart-grid"><path d="M50 30H740M50 75H740M50 120H740M50 165H740M50 210H740" /><path d="M50 30V210M188 30V210M326 30V210M464 30V210M602 30V210M740 30V210" /></g>
          <path class="chart-area" d="M50 168 C90 166,112 150,145 155 S205 174,240 144 S290 88,326 100 S380 125,416 92 S480 48,520 70 S585 138,625 118 S690 72,740 88 L740 210 L50 210Z" />
          <path class="chart-line target-line" d="M50 168 C90 166,112 150,145 155 S205 174,240 144 S290 88,326 100 S380 125,416 92 S480 48,520 70 S585 138,625 118 S690 72,740 88" />
          <path class="chart-line mv-line" d="M50 188 L145 188 L150 150 L240 150 L246 106 L360 106 L366 72 L520 72 L526 130 L650 130 L656 96 L740 96" />
          <path class="chart-line dv-line" d="M50 138 C120 132 155 142 220 135 S330 128 400 138 S520 145 590 126 S675 134 740 122" />
          <g class="chart-labels"><text x="50" y="234">07-01 00:00</text><text x="188" y="234">01:12</text><text x="326" y="234">02:24</text><text x="464" y="234">03:36</text><text x="602" y="234">04:48</text><text x="700" y="234">06:00</text></g>
        </svg>
      </section>

      <section class="panel schema-panel">
        <div class="section-heading compact"><div><span class="section-kicker">自动字段识别</span><h2>变量角色与数据质量</h2></div><button class="text-button" type="button" @click="emit('navigate', '/standard-check/')">进入规整 <AppIcon name="arrow" :size="15" /></button></div>
        <div class="role-summary"><div><span class="role-dot cv"></span><strong>CV</strong><small>2 被控变量</small></div><div><span class="role-dot mv"></span><strong>MV</strong><small>7 操纵变量</small></div><div><span class="role-dot dv"></span><strong>DV</strong><small>9 扰动变量</small></div><div><span class="role-dot ff"></span><strong>FF</strong><small>18 特征变量</small></div></div>
        <div class="quality-list">
          <div><span>时间戳完整性</span><strong>100%</strong><i><b style="width:100%"></b></i></div>
          <div><span>字段映射覆盖率</span><strong>97.2%</strong><i><b style="width:97.2%"></b></i></div>
          <div><span>跨源时间对齐率</span><strong>98.6%</strong><i><b style="width:98.6%"></b></i></div>
          <div class="is-warning"><span>异常规则命中</span><strong>{{ project.abnormal }}%</strong><i><b :style="{ width: `${project.abnormal * 12}%` }"></b></i></div>
        </div>
        <div class="agent-tip"><span><AppIcon name="spark" /></span><p><strong>Agent 建议</strong>先隔离 2 个压力尖峰，再按 {{ project.sample }} 重采样进入动态优选，可避免异常点抬高斜率能量。</p></div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.pipeline-stage-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.pipeline-stage-grid article { min-height: 92px; padding: 13px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; }
.pipeline-stage-grid span, .pipeline-stage-grid small { display: block; }
.pipeline-stage-grid strong { display: block; margin: 5px 0; color: #475569; }
.pipeline-stage-grid small { color: #64748b; line-height: 1.35; }
.pipeline-stage-grid .is-completed { border-color: #a7f3d0; background: #f0fdf4; }
.pipeline-stage-grid .is-completed strong { color: #047857; }
.pipeline-stage-grid .is-failed { border-color: #fecaca; background: #fff7f7; }
.pipeline-stage-grid .is-failed strong { color: #b91c1c; }
.pipeline-artifacts { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 15px; }
.pipeline-artifacts a { padding: 7px 10px; border: 1px solid #bfdbfe; border-radius: 6px; color: #1d4ed8; text-decoration: none; background: #eff6ff; font-size: 13px; }
.drop-zone.is-dragging { border-color: #2563eb; background: #eff6ff; box-shadow: inset 0 0 0 1px #60a5fa; }
.simulation-actions { display: grid; grid-template-columns: 1fr; gap: 9px; margin-top: 16px; }
.simulation-actions .btn { width: 100%; }
.simulation-result { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 9px; margin-top: 12px; padding: 10px; border: 1px solid #a7f3d0; border-radius: 8px; background: #f0fdf4; }
.simulation-result > span { display: grid; place-items: center; width: 28px; height: 28px; color: #047857; border-radius: 7px; background: #d1fae5; }
.simulation-result strong, .simulation-result small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.simulation-result strong { color: #14532d; font-size: 11px; }
.simulation-result small { margin-top: 3px; color: #64748b; font-size: 8px; }
.simulation-result button { color: #047857; font-size: 9px; white-space: nowrap; }
@media (max-width: 900px) { .pipeline-stage-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .pipeline-stage-grid { grid-template-columns: 1fr; } }
.scene-mismatch-panel { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; padding: 9px 12px; color: #854d0e; border: 1px solid #fcd34d; border-radius: 10px; background: #fffbeb; font-size: 13px; }
</style>
