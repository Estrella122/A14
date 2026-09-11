<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { getAgentTrace } from '../api/agent'
import { mockAgentTraceByScenario } from '../data/mockData'

const props = defineProps({ runId: { type: String, default: '' }, running: { type: Boolean, default: false }, scenarioId: { type: String, default: 'blast_furnace' } })
const trace = ref(null)
const loading = ref(false)
const error = ref('')
const expanded = ref([])
const activeStep = ref(0)
let controller
let stepTimer

const nodes = computed(() => trace.value?.nodes ?? [])
const activeIndex = computed(() => props.running ? Math.min(nodes.value.length - 1, activeStep.value) : -1)
const traceSource = computed(() => trace.value?.source === 'mock' ? '演示轨迹' : '后端真实轨迹')

function toggle(id) {
  expanded.value = expanded.value.includes(id) ? expanded.value.filter((item) => item !== id) : [...expanded.value, id]
}

async function loadTrace() {
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''
  try {
    trace.value = await getAgentTrace(props.runId, { signal: controller.signal })
  } catch (requestError) {
    if (requestError.name === 'AbortError') return
    // TODO(mock): trace API 请求失败或无运行记录时使用一次完整执行链，保证离线演示可用。
    const fallback = mockAgentTraceByScenario[props.scenarioId] ?? mockAgentTraceByScenario.blast_furnace
    trace.value = { ...fallback, nodes: fallback.nodes.map((node) => ({ ...node })) }
    error.value = '推理轨迹接口待接入，当前展示同结构演示数据'
  } finally {
    loading.value = false
  }
}

function stateOf(node, index) {
  if (props.running && index === activeIndex.value) return 'running'
  if (props.running && index > activeIndex.value) return 'skipped'
  return node.status
}

watch(() => props.runId, loadTrace, { immediate: true })
watch(() => props.scenarioId, loadTrace)
watch(() => props.running, (value) => {
  window.clearInterval(stepTimer)
  if (value) {
    activeStep.value = 0
    stepTimer = window.setInterval(() => { activeStep.value = Math.min(activeStep.value + 1, Math.max(nodes.value.length - 1, 0)) }, 620)
  } else if (props.runId) loadTrace()
}, { immediate: true })
onBeforeUnmount(() => { controller?.abort(); window.clearInterval(stepTimer) })
</script>

<template>
  <section class="panel agent-trace-panel" :aria-busy="loading">
    <div class="section-heading compact">
      <div><span class="section-kicker">Reasoning & Tool Trace</span><h2>Agent 推理链路</h2></div>
      <div class="trace-heading-actions">
        <StatusPill v-if="error" tone="warning">{{ traceSource }}</StatusPill>
        <StatusPill v-else :tone="loading ? 'neutral' : 'success'" dot>{{ loading ? '读取中' : traceSource }}</StatusPill>
        <span>{{ trace?.total_duration_ms ? `${(trace.total_duration_ms / 1000).toFixed(2)} s` : '—' }}</span>
      </div>
    </div>
    <p v-if="error" class="trace-fallback"><AppIcon name="alert" :size="14" />{{ error }}</p>

    <div v-if="nodes.length" class="trace-timeline">
      <article v-for="(node, index) in nodes" :key="node.id" class="trace-node" :class="`is-${stateOf(node, index)}`">
        <span class="trace-index">
          <AppIcon :name="stateOf(node, index) === 'failed' ? 'alert' : stateOf(node, index) === 'running' ? 'loop' : stateOf(node, index) === 'success' ? 'check' : 'clock'" :class="{ spinning: stateOf(node, index) === 'running' }" :size="15" />
        </span>
        <button type="button" :aria-expanded="expanded.includes(node.id)" @click="toggle(node.id)">
          <span><small>0{{ index + 1 }} · {{ node.kind }}</small><strong>{{ node.name }}</strong></span>
          <span class="trace-summary"><small>输入</small>{{ Object.entries(node.input ?? {}).slice(0, 2).map(([key, value]) => `${key}=${Array.isArray(value) ? value.length : value}`).join(' · ') }}</span>
          <span class="trace-summary"><small>输出</small>{{ Object.entries(node.output ?? {}).slice(0, 2).map(([key, value]) => `${key}=${Array.isArray(value) ? value.length : value}`).join(' · ') }}</span>
          <span class="trace-duration">{{ node.duration_ms }} ms</span>
          <AppIcon name="chevron" :class="{ rotated: expanded.includes(node.id) }" :size="15" />
        </button>
        <div v-if="expanded.includes(node.id)" class="trace-json">
          <div><span>INPUT</span><pre>{{ JSON.stringify(node.input, null, 2) }}</pre></div>
          <div><span>OUTPUT</span><pre>{{ JSON.stringify(node.output, null, 2) }}</pre></div>
        </div>
      </article>
    </div>
    <div v-else class="empty-state">{{ loading ? '正在读取 Agent 推理轨迹…' : '当前任务暂无推理节点。' }}</div>

    <div class="trace-toolchain">
      <div><span class="section-kicker">Tool Call Chain</span><strong>底层工具调用链</strong></div>
      <template v-for="(tool, index) in trace?.toolchain ?? []" :key="tool">
        <span class="toolchain-node"><AppIcon :name="['clean', 'segments', 'network', 'model', 'check'][index] ?? 'loop'" :size="16" />{{ tool }}</span>
        <AppIcon v-if="index < (trace?.toolchain?.length ?? 0) - 1" name="arrow" class="toolchain-arrow" :size="16" />
      </template>
    </div>
  </section>
</template>

<style scoped>
.trace-heading-actions { display: flex; align-items: center; gap: 10px; color: var(--muted); font-family: monospace; font-size: 11px; }
.trace-fallback { display: flex; align-items: center; gap: 7px; margin: -4px 0 14px; color: #9a6700; font-size: 12px; }
.trace-timeline { display: grid; }
.trace-node { position: relative; display: grid; grid-template-columns: 34px minmax(0, 1fr); }
.trace-node:not(:last-child)::before { content: ''; position: absolute; top: 30px; bottom: -5px; left: 16px; width: 2px; background: #dbe5f1; }
.trace-index { z-index: 1; display: grid; place-items: center; width: 33px; height: 33px; color: #fff; border: 4px solid #fff; border-radius: 50%; background: #10b981; box-shadow: 0 0 0 1px #b7e4d2; }
.trace-node.is-failed .trace-index { background: #dc2626; box-shadow: 0 0 0 1px #fecaca; }
.trace-node.is-skipped .trace-index { color: #64748b; background: #e2e8f0; box-shadow: 0 0 0 1px #cbd5e1; }
.trace-node.is-running .trace-index { background: #2563eb; animation: trace-pulse 1.4s ease-in-out infinite; }
.trace-node > button { display: grid; grid-template-columns: 140px minmax(170px, 1fr) minmax(170px, 1fr) 70px 20px; gap: 12px; align-items: center; width: 100%; min-height: 58px; margin: 0 0 8px 8px; padding: 9px 12px; color: var(--ink-2); text-align: left; border: 1px solid var(--line); border-radius: 9px; background: #fbfdff; transition: 160ms ease; }
.trace-node > button:hover { border-color: #a8c6f3; background: #f5f9ff; }
.trace-node > button > span:first-child small, .trace-node > button > span:first-child strong { display: block; }
.trace-node > button > span:first-child small { color: #7c91aa; font-family: monospace; font-size: 9px; text-transform: uppercase; }
.trace-node > button > span:first-child strong { margin-top: 3px; font-size: 13px; }
.trace-summary { overflow: hidden; color: #52647a; font-family: monospace; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.trace-summary small { display: block; margin-bottom: 3px; color: #94a3b8; font-family: inherit; font-size: 8px; }
.trace-duration { color: #1e5fae; font-family: monospace; font-size: 10px; text-align: right; }
.rotated { transform: rotate(90deg); }
.trace-json { grid-column: 2; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: -3px 0 12px 8px; padding: 9px; border: 1px solid #dbe6f2; border-radius: 8px; background: #0b1728; }
.trace-json span { color: #60a5fa; font: 700 9px monospace; }
.trace-json pre { max-height: 180px; margin: 6px 0 0; padding: 9px; overflow: auto; color: #d9e6f5; font: 10px/1.55 monospace; background: #07111f; border-radius: 5px; }
.trace-toolchain { display: flex; align-items: center; gap: 9px; margin-top: 15px; padding: 15px; overflow-x: auto; border: 1px solid #d9e6f4; border-radius: 10px; background: linear-gradient(90deg, #f8fbff, #f3f7fd); }
.trace-toolchain > div { min-width: 130px; margin-right: 5px; }
.trace-toolchain > div strong { display: block; margin-top: 3px; font-size: 12px; }
.toolchain-node { display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto; padding: 9px 11px; color: #1e4f89; font-size: 11px; font-weight: 650; border: 1px solid #c9dff8; border-radius: 8px; background: #fff; }
.toolchain-arrow { flex: 0 0 auto; color: #8aa5c3; }
@keyframes trace-pulse { 50% { box-shadow: 0 0 0 8px rgba(37, 99, 235, .12), 0 0 0 1px #93c5fd; } }
@media (max-width: 900px) { .trace-node > button { grid-template-columns: 120px 1fr 70px 18px; } .trace-node > button .trace-summary:nth-of-type(3) { display: none; } }
@media (max-width: 620px) { .trace-node > button { grid-template-columns: 1fr auto 18px; } .trace-summary { display: none; } .trace-json { grid-template-columns: 1fr; } }
</style>
