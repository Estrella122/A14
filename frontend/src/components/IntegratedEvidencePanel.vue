<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { sceneFromRun } from '../composables/useSceneBinding'

const props = defineProps({
  module: { type: String, required: true },
})

const data = ref(null)
const loading = ref(false)
const error = ref('')
const runId = ref('')

const label = computed(() => data.value?.module ?? '交付物集成')
const detailRows = computed(() => {
  if (!data.value) return []
  if (props.module === 'standardization') return data.value.mapping_preview ?? []
  if (props.module === 'cleaning') return data.value.segments ?? []
  if (props.module === 'modeling') return data.value.lags ?? []
  return Object.entries(data.value.candidate ?? {}).slice(0, 8).map(([key, value]) => ({ key, value: typeof value === 'object' ? JSON.stringify(value) : value }))
})

function formatValue(value) {
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3)
  if (typeof value === 'object' && value !== null) {
    const serialized = JSON.stringify(value)
    return serialized.length > 96 ? `${serialized.slice(0, 93)}…` : serialized
  }
  return String(value ?? '—')
}

async function loadEvidence() {
  loading.value = true
  error.value = ''
  try {
    const latestResponse = await fetch('/api/pipeline/runs/latest/')
    const latestPayload = await latestResponse.json()
    const run = latestPayload?.data
    const resultKey = props.module === 'agent' ? 'review' : props.module
    if (latestResponse.ok && run?.results?.[resultKey]) {
      runId.value = run.run_id
      data.value = liveEvidence(run, props.module)
      return
    }
    const response = await fetch(`/api/integration/${props.module}/`)
    const payload = await response.json()
    if (!response.ok || !payload.ok) throw new Error(payload.message ?? '原始交付物读取失败')
    data.value = payload.data
  } catch (requestError) {
    error.value = requestError.message || '无法连接统一后端服务'
  } finally {
    loading.value = false
  }
}

function liveEvidence(run, module) {
  const result = run.results[module === 'agent' ? 'review' : module]
  const common = { module: '', source: `实时流水线 · ${run.run_id}`, available: true, live: true }
  if (module === 'standardization') return {
    ...common,
    module: '统一标准与多场景模板（2号）',
    passed: result.data_decision?.status === 'ready',
    passed_items: result.mapping?.mappings?.filter((item) => item.status === 'matched').length ?? 0,
    total_items: result.mapping?.mappings?.length ?? 0,
    mapping_preview: result.mapping?.mappings ?? [],
    data_scene: sceneFromRun(run),
  }
  if (module === 'cleaning') return {
    ...common,
    module: '数据清洗与优质数据筛选（3号）',
    overall_score: result.overall_score,
    selected_segment_count: result.selected_segment_count,
    logs: result.logs,
    segments: result.segments_preview,
  }
  if (module === 'modeling') return {
    ...common,
    module: '时滞分析与系统辨识（4号）',
    metrics: result.metrics,
    selected_inputs: result.selected_inputs,
    lags: result.lags,
  }
  return {
    ...common,
    module: 'Agent 总控编排（1号）',
    candidate: {
      test_r2: result.evidence?.test_r2,
      dynamic_ratio: Number(run.results?.cleaning?.modeling_row_count ?? 0) / Math.max(Number(run.results?.cleaning?.cleaned_row_count ?? 0), 1),
      conclusion: result.conclusion,
    },
    stages: run.stages?.map((stage) => stage.label) ?? [],
  }
}

function handlePipelineUpdate() { loadEvidence() }
onMounted(() => {
  loadEvidence()
  window.addEventListener('processpilot:pipeline-updated', handlePipelineUpdate)
})
onBeforeUnmount(() => window.removeEventListener('processpilot:pipeline-updated', handlePipelineUpdate))
</script>

<template>
  <section class="panel integrated-evidence-panel" :aria-busy="loading">
    <div class="section-heading compact">
      <div>
        <span class="section-kicker">{{ data?.live ? '最近一次真实运行' : '已合并原始交付物' }}</span>
        <h2>{{ label }}</h2>
      </div>
      <div class="evidence-actions">
        <StatusPill :tone="error ? 'warning' : data?.available === false ? 'warning' : 'success'" dot>{{ error ? '连接异常' : data ? '已接入' : '读取中' }}</StatusPill>
        <button class="text-button" type="button" :disabled="loading" @click="loadEvidence"><AppIcon name="loop" :class="{ spinning: loading }" :size="14" />刷新</button>
      </div>
    </div>

    <p v-if="error" class="evidence-error">{{ error }}。请先运行主工程的 <code>npm run dev</code>。</p>
    <template v-else-if="data">
      <p class="evidence-source"><AppIcon name="shield" :size="14" /> {{ data.source }} · {{ data.live ? '由上传数据实时执行并生成，指标与产物一致。' : '通过主工程统一接口读取，未改写成员原始成果。' }}</p>

      <div v-if="module === 'standardization'" class="evidence-kpis">
        <div><span>验收结果</span><strong>{{ data.passed ? '通过' : '待复核' }}</strong></div>
        <div><span>验收条目</span><strong>{{ data.passed_items }} / {{ data.total_items }}</strong></div>
        <div><span>当前数据场景</span><strong class="scene-value">{{ data.data_scene?.display_name ?? '待识别' }}</strong></div>
      </div>
      <div v-else-if="module === 'cleaning'" class="evidence-kpis">
        <div><span>质量评分</span><strong>{{ data.overall_score }}<small> / 100</small></strong></div>
        <div><span>优选动态段</span><strong>{{ data.selected_segment_count }} 段</strong></div>
        <div><span>清洗日志</span><strong>{{ data.logs?.length ?? 0 }} 条</strong></div>
      </div>
      <div v-else-if="module === 'modeling'" class="evidence-kpis">
        <div><span>独立测试 R²</span><strong>{{ data.metrics?.test?.r2 == null ? '—' : Number(data.metrics.test.r2).toFixed(3) }}</strong></div>
        <div><span>独立测试 RMSE</span><strong>{{ data.metrics?.test?.rmse == null ? '—' : Number(data.metrics.test.rmse).toFixed(3) }}</strong></div>
        <div><span>保留输入</span><strong>{{ data.selected_inputs?.length ?? 0 }} 个</strong></div>
      </div>
      <div v-else class="evidence-kpis">
        <div v-if="data.live"><span>独立测试 R²</span><strong>{{ data.candidate?.test_r2 == null ? '—' : Number(data.candidate.test_r2).toFixed(3) }}</strong></div>
        <div v-else><span>验证 Fit</span><strong>{{ Number(data.candidate?.validation_fit_percent ?? 0).toFixed(1) }}<small>%</small></strong></div>
        <div><span>动态段占比</span><strong>{{ Number(data.candidate?.dynamic_ratio ?? 0).toFixed(3) }}</strong></div>
        <div><span>Agent 阶段</span><strong>{{ data.stages?.length ?? 0 }} 步</strong></div>
      </div>

      <div v-if="detailRows.length" class="table-wrap evidence-table-wrap">
        <table class="data-table evidence-table">
          <caption class="visually-hidden">成员原始交付物证据预览</caption>
          <thead><tr><th v-for="key in Object.keys(detailRows[0])" :key="key">{{ key }}</th></tr></thead>
          <tbody><tr v-for="(row, index) in detailRows.slice(0, 4)" :key="index"><td v-for="(value, key) in row" :key="key">{{ formatValue(value) }}</td></tr></tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.integrated-evidence-panel { border-color: rgba(37, 99, 235, .22); }
.evidence-actions { display: flex; align-items: center; gap: 10px; }
.evidence-source { display: flex; align-items: center; gap: 7px; margin: -4px 0 17px; color: #64748b; font-size: 13px; }
.evidence-error { color: #b45309; margin: 0; }
.evidence-kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.evidence-kpis > div { padding: 13px 14px; border-radius: 10px; background: #f8fbff; border: 1px solid #e1ecfb; }
.evidence-kpis span { display: block; color: #64748b; font-size: 12px; margin-bottom: 4px; }
.evidence-kpis strong { color: #173b74; font-size: 20px; }
.evidence-kpis .scene-value { font-size: 14px; line-height: 1.45; }
.evidence-kpis small { font-size: 12px; color: #64748b; }
.evidence-table-wrap { max-height: 205px; }
.evidence-table td, .evidence-table th { white-space: nowrap; }
@media (max-width: 640px) { .evidence-kpis { grid-template-columns: 1fr; } }
</style>
