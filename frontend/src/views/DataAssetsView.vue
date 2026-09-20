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
import { apiRequest, parseApiResponse, secureFetch } from '../api/client'
import { buildPresetDataset, DEMO_DEFAULTS, DEMO_VERSION, DEMO_VERIFIED, LEGACY_DEFAULTS, CHALLENGES, isVerifiedConfiguration } from '../utils/simulationPresets'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate', 'scene-detected'])

const fileInput = ref(null)
const isGenerating = ref(false)
const uploading = ref(false)
const dragActive = ref(false)
const generatedDataset = ref(null)
const { latestRun } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(props.project, latestRun.value))
const simulationMode = ref('custom')
const challenge = ref('high_noise')
const simulation = ref({ ...DEMO_DEFAULTS })
const supportsDemo = computed(() => props.project.scenarioId === 'blast_furnace')
const legacyMode = ref(false)
const verifiedDefault = computed(() => isVerifiedConfiguration(props.project.scenarioId, simulationMode.value, simulation.value))
const modeDescription = computed(() => simulationMode.value === 'full_demo'
  ? (verifiedDefault.value ? '适合首次体验，在所示版本和默认配置下已验证完整流程。' : '本版流程已跑通，但固定 seed 验收未全部达到预测覆盖率和基线要求，暂不作为已验证推荐。')
  : simulationMode.value === 'challenge' ? '用于观察算法边界，可能出现质量警告或无可用模型。' : '修改生成参数后，结果需要重新评估。')
function setSimulationMode(mode) {
  simulationMode.value = mode
  legacyMode.value = !supportsDemo.value || mode === 'challenge' && challenge.value === 'legacy_pressure_v1'
  simulation.value = { ...(legacyMode.value ? LEGACY_DEFAULTS : mode === 'challenge' ? CHALLENGES[challenge.value] : DEMO_DEFAULTS) }
  generatedDataset.value = null
}
function customize() { simulationMode.value = 'custom'; generatedDataset.value = null }
watch(() => props.project.scenarioId, () => {
  challenge.value = supportsDemo.value ? 'high_noise' : 'legacy_pressure_v1'
  setSimulationMode(supportsDemo.value && DEMO_VERIFIED ? 'full_demo' : supportsDemo.value ? 'custom' : 'challenge')
}, { immediate: true })
function downloadGeneratedJson(key) {
  const value = generatedDataset.value?.[key]
  if (value) downloadSimulation(new File([JSON.stringify(value, null, 2)], `SYNTHETIC_${key === 'manifest' ? 'generation_manifest' : 'evaluation_reference'}.json`, { type: 'application/json' }))
}
const fileFilter = ref('all')
const chartRange = ref('6h')
const mappingDraft = ref({})
const reviewScenario = ref('')

const assetPreview = ref(null)
const files = ref([])
async function refreshAssets() {
  try {
    const payload = await apiRequest('/assets/')
    files.value = payload.data.map(asset => ({ ...asset, id: asset.asset_id, name: asset.display_name,
      source: ['SYNTHETIC', 'simulation'].includes(asset.source_type) ? 'SYNTHETIC 合成数据' : '本地上传', variables: asset.columns, period: asset.created_at,
      size: `${(asset.size / 1024).toFixed(1)} KB`, quality: null }))
  } catch (error) { emit('notify', { tone: 'warning', title: '资产读取失败', message: error.message }) }
}
async function persistAsset(file, sourceType = 'upload', generated = null) {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  if (generated) {
    form.append('generation_manifest', JSON.stringify(generated.manifest))
    form.append('evaluation_reference', JSON.stringify(generated.reference))
  }
  const payload = await parseApiResponse(await secureFetch('/assets/', { method: 'POST', body: form }))
  await refreshAssets()
  return files.value.find(item => item.id === payload.data.asset_id)
}
onMounted(refreshAssets)

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
  uploading.value = true
  try {
    if (!pending.asset_id) pending = await persistAsset(file)
    latestRun.value = await uploadPipelineFile(file, { assetId: pending.asset_id, scenarioId: 'auto', projectSceneId: props.project.scenarioId, instruction: '请根据上传数据识别工业场景并执行APC建模', resampleRule: props.project.resampleRule, maxLag: props.project.maxLag })
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

async function previewAsset(file) {
  try { assetPreview.value = (await apiRequest(`/assets/${file.id}/?preview=1`)).data }
  catch (error) { emit('notify', { tone: 'warning', title: '预览失败', message: error.message }) }
}
async function runStoredAsset(file) {
  try {
    const response = await secureFetch(`/assets/${file.id}/?download=1`)
    if (!response.ok) throw new Error('资产不可读取')
    await runPipelineFile(new File([await response.blob()], file.name, { type: 'text/csv' }), file)
  } catch (error) { emit('notify', { tone: 'warning', title: '运行失败', message: error.message }) }
}
async function removeFile(file) {
  try {
    await apiRequest(`/assets/${encodeURIComponent(file.id)}/`, { method: 'DELETE' })
    const confirmed = await apiRequest(`/assets/${encodeURIComponent(file.id)}/`)
    if (confirmed.data.status !== 'archived') throw new Error('后端未确认归档状态')
    await refreshAssets()
    emit('notify', { tone: 'neutral', title: '资产已归档', message: `${file.name} 已归档；已有运行证据保留。` })
  } catch (error) { emit('notify', { tone: 'warning', title: '归档失败', message: error.message }) }
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
    const result = await buildPresetDataset(props.project, simulationMode.value, simulation.value, legacyMode.value ? 'legacy_pressure_v1' : challenge.value)
    const file = new File([result.csv], result.name, { type: 'text/csv;charset=utf-8' })
    const pending = await persistAsset(file, 'SYNTHETIC', result)
    generatedDataset.value = { file, asset: pending, ...result }

    if (action === 'run') {
      await runPipelineFile(file, pending)
    } else {
      if (action === 'download') downloadSimulation(file)
      pending.status = '已生成'
      emit('notify', { tone: 'success', title: '合成数据已生成并保存', message: `${result.rowCount.toLocaleString('zh-CN')} 行数据·${result.summary}。` })
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

    <section v-if="assetPreview" class="panel"><button type="button" @click="assetPreview = null">关闭预览</button><pre>{{ assetPreview }}</pre></section>
    <div class="content-grid content-grid-8-4">
      <section class="panel files-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">数据文件管理</span><h2>项目数据资产</h2></div>
          <div class="table-tools"><button type="button" :class="{ 'is-active': fileFilter === 'all' }" @click="setFileFilter('all')">全部来源</button><button type="button" :class="{ 'is-active': fileFilter === 'recent' }" @click="setFileFilter('recent')">最近更新</button><button class="icon-button" type="button" :class="{ 'is-active': fileFilter === 'quality' }" aria-label="只看高质量数据" title="只看质量分不低于95的数据" @click="setFileFilter('quality')"><AppIcon name="more" /></button></div>
        </div>
        <button class="drop-zone" :class="{ 'is-dragging': dragActive }" type="button" @click="chooseFile" @dragenter.prevent="dragActive = true" @dragover.prevent="dragActive = true" @dragleave.prevent="dragActive = false" @drop.prevent="handleDrop">
          <span><AppIcon name="upload" :size="22" /></span>
          <strong>拖拽 CSV 到这里，或点击选择文件</strong>
          <small>单文件不超过 200 MB · 源文件只读保存 · 自动识别时间戳、变量与质量码</small>
        </button>
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
                <td><button class="btn btn-secondary" type="button" @click="previewAsset(file)">查看</button><button class="btn btn-secondary" type="button" :disabled="uploading" @click="runStoredAsset(file)">运行</button><button class="icon-button danger-on-hover" type="button" :aria-label="`删除 ${file.name}`" @click="removeFile(file)"><AppIcon name="trash" /></button></td>
              </tr>
            </tbody>
          </table>
          <p v-if="!visibleFiles.length" class="empty-state">当前筛选条件下没有数据资产。</p>
        </div>
      </section>

      <section class="panel simulation-panel">
        <div class="section-heading compact"><div><span class="section-kicker">SYNTHETIC 合成数据</span><h2>仿真测试集生成器</h2></div><StatusPill :tone="verifiedDefault ? 'success' : 'neutral'">{{ verifiedDefault ? '已验证默认配置' : '未认证配置' }}</StatusPill></div>
        <label class="preset-select">生成模式<select :value="simulationMode" :disabled="isGenerating || uploading" @change="setSimulationMode($event.target.value)"><option value="full_demo" :disabled="!supportsDemo">完整流程演示{{ DEMO_VERIFIED && supportsDemo ? '〔推荐〕' : supportsDemo ? '〔质量未通过〕' : '〔未验证〕' }}</option><option value="challenge">挑战测试</option><option value="custom">自定义</option></select></label>
        <p class="panel-description">{{ modeDescription }}</p>
        <label v-if="simulationMode === 'challenge'" class="preset-select">挑战类型<select v-model="challenge" @change="setSimulationMode('challenge')"><template v-if="supportsDemo"><option value="high_noise">高噪声与目标测量尖峰</option><option value="sparse_target">稀疏目标观测（每 48 点）</option><option value="low_excitation">动态不足</option><option value="process_shock">过程冲击</option></template><option value="legacy_pressure_v1">旧版压力测试 legacy_pressure_v1</option></select></label>
        <p class="panel-description">{{ project.name }} · {{ legacyMode ? 'legacy_pressure_v1 · 原版采样和行数' : `${DEMO_VERSION} · 1 h 采样 · ${simulation.rows} 行` }}</p>
        <p v-if="!legacyMode" class="panel-description">独立输入激励；测量噪声 {{ simulation.noise }}，过程扰动 {{ simulation.processNoise }}；输入尖峰 {{ simulation.anomalies }} 点，目标尖峰 {{ simulation.targetSpikes }} 点。目标误差单位：Si 质量百分数的百分点。仅验证已知合成机制。</p>
        <div class="control-stack" @input="customize">
          <template v-if="!legacyMode">
            <label><span>固定 seed</span><input v-model.number="simulation.seed" aria-label="生成 seed" type="number" min="0" max="4294967295" /></label>
            <label><span>行数</span><input v-model.number="simulation.rows" aria-label="生成行数" type="number" min="150" max="10000" /></label>
            <label><span>测量噪声尺度</span><input v-model.number="simulation.noise" aria-label="测量噪声" type="number" min="0" max="0.2" step="0.0005" /></label>
            <label><span>过程扰动尺度</span><input v-model.number="simulation.processNoise" aria-label="过程扰动" type="number" min="0" max="0.1" step="0.0001" /></label>
            <label><span>目标测量尖峰（不改变状态）</span><input v-model.number="simulation.targetSpikes" type="number" min="0" max="30" /></label>
            <label><span>过程冲击（改变状态）</span><input v-model.number="simulation.processShocks" type="number" min="0" max="30" /></label>
            <label><span>目标观测间隔（采样点）</span><input v-model.number="simulation.targetEvery" type="number" min="1" max="100" /></label>
          </template>
          <template v-else>
            <label><span>稳态占比 {{ simulation.steady }}%</span><input v-model="simulation.steady" type="range" min="20" max="75" /></label>
            <label><span>旧版噪声尺度 {{ simulation.noise }}</span><input v-model="simulation.noise" type="range" min="1" max="6" /></label>
          </template>
          <label><span>阶跃幅度 {{ simulation.step }}%</span><input v-model="simulation.step" type="range" :min="legacyMode ? 5 : 0" max="35" /></label>
          <label><span>{{ legacyMode ? '旧版混合异常' : '输入传感器尖峰' }} {{ simulation.anomalies }} 点</span><input v-model="simulation.anomalies" type="range" min="0" max="30" /></label>
        </div>
        <div class="simulation-actions">
          <button class="btn btn-secondary" type="button" :disabled="isGenerating || uploading" @click="generateSimulation('generate')">生成数据</button>
          <button class="btn btn-primary" type="button" :disabled="isGenerating || uploading || !generatedDataset" @click="runPipelineFile(generatedDataset.file, generatedDataset.asset)">{{ uploading ? '流水线运行中…' : '开始完整分析' }}</button>
          <small>开始分析将执行真实清洗、筛选、建模与多轮寻优。切换模式不会启动计算。</small>
        </div>
        <div v-if="generatedDataset" class="generated-details">
          <strong>{{ generatedDataset.name }}</strong>
          <small>资产 {{ generatedDataset.asset.asset_id }} · SYNTHETIC</small>
          <small>SHA-256 {{ generatedDataset.manifest.file_hash }}</small>
          <button class="btn btn-secondary" type="button" @click="downloadSimulation(generatedDataset.file)">下载原始 CSV</button>
          <button class="btn btn-secondary" type="button" @click="downloadGeneratedJson('manifest')">下载生成清单</button>
          <button class="btn btn-secondary" type="button" @click="downloadGeneratedJson('reference')">下载独立验收参考</button>
          <small>参考文件独立保存，仅供验收，不参与分析或模型上下文。</small>
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

    <IntegratedEvidencePanel module="standardization" />
  </div>
</template>

<style scoped>
.preset-select, .generated-details { display: grid; gap: 9px; margin: 14px 0; overflow-wrap: anywhere; }
.preset-select select, .control-stack input[type="number"] { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background: white; max-width: 100%; }
.generated-details small { color: #64748b; }
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
