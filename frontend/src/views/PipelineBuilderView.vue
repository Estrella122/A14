<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import { defaultPipelineGraph, pipelineNodeTypes } from '../data/mockData'

const emit = defineEmits(['notify', 'navigate'])
const canvas = ref(null)
const nodes = ref(defaultPipelineGraph.nodes.map((node) => ({ ...node, config: { ...node.config }, status: 'idle' })))
const edges = ref(defaultPipelineGraph.edges.map((edge) => ({ ...edge })))
const selectedId = ref(nodes.value[0]?.id ?? '')
const connectingFrom = ref('')
const templates = ref([])
const activeTemplate = ref('')
const loading = ref(true)
const running = ref(false)
const error = ref('')
const progress = ref(0)
let movingId = ''
let runTimer

const typeMap = Object.fromEntries(pipelineNodeTypes.map((item) => [item.type, item]))
const selectedNode = computed(() => nodes.value.find((node) => node.id === selectedId.value) ?? null)
const selectedDefinition = computed(() => selectedNode.value ? typeMap[selectedNode.value.type] : null)

function readTemplates() {
  try { templates.value = JSON.parse(window.localStorage.getItem('processpilot-pipeline-templates') || '[]') } catch { templates.value = [] }
  loading.value = false
}

function dragPalette(event, type) {
  movingId = ''
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/processpilot-node', type)
}

function addNode(type) {
  const definition = typeMap[type]
  if (!definition) return
  const index = nodes.value.length
  const node = { id: `node-${Date.now()}`, type, x: 35 + (index % 3) * 220, y: 35 + Math.floor(index / 3) * 135, config: { ...definition.defaults }, status: 'idle' }
  nodes.value.push(node)
  selectedId.value = node.id
}

function dragNode(event, id) {
  movingId = id
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/processpilot-node-id', id)
}

function dropOnCanvas(event) {
  const bounds = canvas.value.getBoundingClientRect()
  const x = Math.max(16, Math.min(bounds.width - 210, event.clientX - bounds.left - 90))
  const y = Math.max(16, Math.min(bounds.height - 100, event.clientY - bounds.top - 35))
  const type = event.dataTransfer.getData('application/processpilot-node')
  const id = event.dataTransfer.getData('application/processpilot-node-id') || movingId
  if (id) {
    const node = nodes.value.find((item) => item.id === id)
    if (node) { node.x = x; node.y = y; selectedId.value = id }
    return
  }
  const definition = typeMap[type]
  if (!definition) return
  const newNode = { id: `node-${Date.now()}`, type, x, y, config: { ...definition.defaults }, status: 'idle' }
  nodes.value.push(newNode)
  selectedId.value = newNode.id
}

function portClick(id, direction) {
  if (direction === 'output') {
    connectingFrom.value = connectingFrom.value === id ? '' : id
    return
  }
  if (!connectingFrom.value || connectingFrom.value === id) return
  const duplicate = edges.value.some((edge) => edge.from === connectingFrom.value && edge.to === id)
  if (!duplicate) edges.value.push({ id: `edge-${Date.now()}`, from: connectingFrom.value, to: id })
  connectingFrom.value = ''
}

function edgePath(edge) {
  const from = nodes.value.find((node) => node.id === edge.from)
  const to = nodes.value.find((node) => node.id === edge.to)
  if (!from || !to) return ''
  const x1 = from.x + 190
  const y1 = from.y + 41
  const x2 = to.x
  const y2 = to.y + 41
  const bend = Math.max(55, Math.abs(x2 - x1) * .48)
  return `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`
}

function removeEdge(id) { edges.value = edges.value.filter((edge) => edge.id !== id) }
function deleteSelected() {
  if (!selectedNode.value) return
  const id = selectedNode.value.id
  nodes.value = nodes.value.filter((node) => node.id !== id)
  edges.value = edges.value.filter((edge) => edge.from !== id && edge.to !== id)
  selectedId.value = nodes.value[0]?.id ?? ''
}

function clearCanvas() {
  nodes.value = []
  edges.value = []
  selectedId.value = ''
  error.value = ''
}

function saveTemplate() {
  if (!nodes.value.length) {
    error.value = '空画布无法保存，请先添加节点。'
    return
  }
  const name = `流水线模板 ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  const snapshot = { id: `template-${Date.now()}`, name, nodes: nodes.value.map(({ status, ...node }) => ({ ...node, config: { ...node.config } })), edges: edges.value.map((edge) => ({ ...edge })) }
  templates.value = [snapshot, ...templates.value].slice(0, 12)
  window.localStorage.setItem('processpilot-pipeline-templates', JSON.stringify(templates.value))
  activeTemplate.value = snapshot.id
  emit('notify', { tone: 'success', title: '流水线模板已保存', message: `${name} 已保存到本机。` })
}

function loadTemplate() {
  const template = templates.value.find((item) => item.id === activeTemplate.value)
  if (!template) return
  nodes.value = template.nodes.map((node) => ({ ...node, config: { ...node.config }, status: 'idle' }))
  edges.value = template.edges.map((edge) => ({ ...edge }))
  selectedId.value = nodes.value[0]?.id ?? ''
  error.value = ''
}

function restoreDefault() {
  nodes.value = defaultPipelineGraph.nodes.map((node) => ({ ...node, config: { ...node.config }, status: 'idle' }))
  edges.value = defaultPipelineGraph.edges.map((edge) => ({ ...edge }))
  selectedId.value = nodes.value[0]?.id ?? ''
  error.value = ''
}

function topologicalOrder() {
  const indegree = Object.fromEntries(nodes.value.map((node) => [node.id, 0]))
  const outgoing = Object.fromEntries(nodes.value.map((node) => [node.id, []]))
  edges.value.forEach((edge) => {
    if (indegree[edge.to] === undefined || !outgoing[edge.from]) return
    indegree[edge.to] += 1
    outgoing[edge.from].push(edge.to)
  })
  const queue = nodes.value.filter((node) => indegree[node.id] === 0).map((node) => node.id)
  const order = []
  while (queue.length) {
    const id = queue.shift()
    order.push(id)
    outgoing[id].forEach((next) => { indegree[next] -= 1; if (!indegree[next]) queue.push(next) })
  }
  if (order.length !== nodes.value.length) throw new Error('流水线存在循环连线，请删除环路后重试。')
  return order
}

async function runPipeline() {
  if (running.value) return
  error.value = ''
  if (!nodes.value.length) { error.value = '画布为空，请添加至少一个节点。'; return }
  let order
  try { order = topologicalOrder() } catch (runError) { error.value = runError.message; return }
  running.value = true
  progress.value = 0
  nodes.value.forEach((node) => { node.status = 'idle' })
  // TODO(mock): 后端提供 POST /api/pipeline/workflows/execute 后，用 SSE/WebSocket 节点事件替换此演示执行器。
  for (let index = 0; index < order.length; index += 1) {
    const node = nodes.value.find((item) => item.id === order[index])
    node.status = 'running'
    selectedId.value = node.id
    await new Promise((resolve) => { runTimer = window.setTimeout(resolve, 420 + index * 25) })
    node.status = 'success'
    progress.value = Math.round((index + 1) / order.length * 100)
  }
  running.value = false
  emit('notify', { tone: 'success', title: '流水线运行完成', message: `${order.length} 个节点已按拓扑顺序执行。` })
  window.setTimeout(() => emit('navigate', nodes.value.some((node) => node.type === 'report') ? '/report-export/' : '/identification-modeling/'), 550)
}

function handleGlobalSave() { saveTemplate() }
onMounted(() => { readTemplates(); window.addEventListener('processpilot:save-pipeline', handleGlobalSave) })
onBeforeUnmount(() => { window.clearTimeout(runTimer); window.removeEventListener('processpilot:save-pipeline', handleGlobalSave) })
</script>

<template>
  <div class="view-stack pipeline-builder-view">
    <PageHeader eyebrow="Visual Agent Orchestration" title="可视化数据流水线编排器" description="以工业算法节点组装可执行工作流，连线定义数据依赖，Agent 按拓扑顺序调度并将辨识指标反馈到前置参数。">
      <template #actions>
        <select v-model="activeTemplate" aria-label="选择流水线模板"><option value="">选择已保存模板</option><option v-for="item in templates" :key="item.id" :value="item.id">{{ item.name }}</option></select>
        <button class="btn btn-secondary" type="button" :disabled="!activeTemplate" @click="loadTemplate">加载</button>
        <button class="btn btn-secondary" type="button" @click="saveTemplate"><AppIcon name="download" />保存模板</button>
        <button class="btn btn-primary" type="button" :disabled="running" @click="runPipeline"><AppIcon :name="running ? 'loop' : 'play'" :class="{ spinning: running }" />{{ running ? `执行中 ${progress}%` : '运行流水线' }}</button>
      </template>
    </PageHeader>

    <div v-if="error" class="builder-error"><AppIcon name="alert" /><span>{{ error }}</span><button type="button" @click="error = ''">关闭</button></div>
    <div v-if="loading" class="builder-loading"><AppIcon name="loop" class="spinning" />正在加载本地流水线模板…</div>

    <div v-else class="builder-shell">
      <aside class="node-library panel">
        <div class="section-heading compact"><div><span class="section-kicker">Node Library</span><h2>算法节点</h2></div><StatusPill tone="brand">9 类</StatusPill></div>
        <p>拖动节点到画布；先点输出端口，再点目标输入端口即可连线。</p>
        <button v-for="item in pipelineNodeTypes" :key="item.type" type="button" draggable="true" @dragstart="dragPalette($event, item.type)" @click="addNode(item.type)">
          <span :style="{ '--node-color': item.color }"><AppIcon :name="item.icon" :size="17" /></span><div><strong>{{ item.label }}</strong><small>{{ item.description }}</small></div><AppIcon name="more" :size="14" />
        </button>
      </aside>

      <section class="pipeline-canvas-panel panel">
        <div class="canvas-toolbar"><span><i></i>Agent Flow Canvas</span><div><button type="button" @click="restoreDefault">恢复标准闭环</button><button type="button" @click="clearCanvas">清空画布</button></div></div>
        <div ref="canvas" class="pipeline-canvas" @dragover.prevent @drop.prevent="dropOnCanvas">
          <svg class="edge-layer" width="100%" height="100%">
            <g v-for="edge in edges" :key="edge.id" class="pipeline-edge" @dblclick="removeEdge(edge.id)"><path :d="edgePath(edge)" /><circle :cx="nodes.find((node) => node.id === edge.to)?.x" :cy="(nodes.find((node) => node.id === edge.to)?.y ?? 0) + 41" r="3" /></g>
          </svg>
          <article v-for="node in nodes" :key="node.id" class="canvas-node" :class="[`is-${node.status}`, { 'is-selected': selectedId === node.id }]" :style="{ left: `${node.x}px`, top: `${node.y}px`, '--node-color': typeMap[node.type]?.color }" draggable="true" @dragstart="dragNode($event, node.id)" @click="selectedId = node.id">
            <button class="node-port input-port" type="button" title="输入端口" @click.stop="portClick(node.id, 'input')"></button>
            <span class="node-icon"><AppIcon :name="typeMap[node.type]?.icon ?? 'loop'" :class="{ spinning: node.status === 'running' }" :size="17" /></span>
            <div><small>{{ node.type }}</small><strong>{{ typeMap[node.type]?.label }}</strong><p>{{ Object.values(node.config).slice(0, 2).join(' · ') }}</p></div>
            <span class="node-state"><AppIcon :name="node.status === 'success' ? 'check' : node.status === 'running' ? 'loop' : 'more'" :size="13" /></span>
            <button class="node-port output-port" :class="{ 'is-connecting': connectingFrom === node.id }" type="button" title="输出端口" @click.stop="portClick(node.id, 'output')"></button>
          </article>
          <div v-if="!nodes.length" class="canvas-empty"><span><AppIcon name="network" :size="32" /></span><strong>把左侧算法节点拖到这里</strong><p>也可以恢复标准闭环模板快速开始。</p><button class="btn btn-primary" type="button" @click="restoreDefault">恢复标准闭环</button></div>
        </div>
        <div class="canvas-status"><span>{{ nodes.length }} 节点 · {{ edges.length }} 连线</span><span v-if="connectingFrom">正在选择目标输入端口…</span><strong v-if="running">当前执行：{{ typeMap[selectedNode?.type]?.label }} · {{ progress }}%</strong><span v-else>双击连线可删除</span></div>
      </section>

      <aside class="property-panel panel">
        <div class="section-heading compact"><div><span class="section-kicker">Properties</span><h2>节点属性</h2></div><StatusPill :tone="selectedNode ? 'success' : 'neutral'">{{ selectedNode ? '已选择' : '空' }}</StatusPill></div>
        <template v-if="selectedNode">
          <div class="property-node-head"><span :style="{ background: selectedDefinition?.color }"><AppIcon :name="selectedDefinition?.icon" /></span><div><strong>{{ selectedDefinition?.label }}</strong><small>{{ selectedNode.id }}</small></div></div>
          <div class="property-fields">
            <label v-for="(value, key) in selectedNode.config" :key="key"><span>{{ key }}</span>
              <input v-if="typeof value === 'number'" v-model.number="selectedNode.config[key]" type="number" />
              <select v-else-if="typeof value === 'boolean'" v-model="selectedNode.config[key]"><option :value="true">启用</option><option :value="false">关闭</option></select>
              <input v-else v-model="selectedNode.config[key]" type="text" />
            </label>
          </div>
          <div class="property-meta"><span>输入连接<strong>{{ edges.filter((edge) => edge.to === selectedNode.id).length }}</strong></span><span>输出连接<strong>{{ edges.filter((edge) => edge.from === selectedNode.id).length }}</strong></span></div>
          <button class="btn btn-secondary btn-block danger-button" type="button" @click="deleteSelected"><AppIcon name="trash" />删除节点</button>
        </template>
        <div v-else class="property-empty"><AppIcon name="more" :size="28" /><p>选择画布中的节点以配置算法参数。</p></div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.pipeline-builder-view { min-width: 0; }
.page-heading select { min-height: 38px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }
.builder-error, .builder-loading { display: flex; align-items: center; gap: 9px; padding: 12px 15px; border: 1px solid #fecaca; border-radius: 9px; color: #a61b1b; background: #fff7f7; }
.builder-error button { margin-left: auto; border: 0; color: inherit; background: transparent; }
.builder-loading { border-color: #bfdbfe; color: #1d4ed8; background: #eff6ff; }
.builder-shell { display: grid; grid-template-columns: 210px minmax(620px, 1fr) 240px; gap: 12px; min-height: 690px; }
.node-library, .property-panel { padding: 14px; }
.node-library > p { margin: -4px 0 12px; color: var(--muted); font-size: 10px; line-height: 1.5; }
.node-library > button { display: grid; grid-template-columns: 34px minmax(0, 1fr) 14px; gap: 8px; align-items: center; width: 100%; min-height: 54px; margin-top: 7px; padding: 7px; color: var(--ink-2); text-align: left; border: 1px solid var(--line-soft); border-radius: 8px; background: #fbfdff; }
.node-library > button:hover { border-color: #b9cff0; transform: translateY(-1px); }
.node-library > button > span { display: grid; place-items: center; width: 34px; height: 34px; color: var(--node-color); border-radius: 8px; background: color-mix(in srgb, var(--node-color) 10%, white); }
.node-library strong, .node-library small { display: block; }.node-library strong { font-size: 11px; }.node-library small { margin-top: 3px; color: var(--muted); font-size: 8px; }
.pipeline-canvas-panel { display: grid; grid-template-rows: 42px minmax(0, 1fr) 31px; padding: 0; overflow: hidden; }
.canvas-toolbar, .canvas-status { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 13px; border-bottom: 1px solid var(--line-soft); background: #fbfdff; }
.canvas-toolbar > span { display: flex; align-items: center; gap: 7px; color: #46617e; font: 700 10px monospace; letter-spacing: .05em; text-transform: uppercase; }
.canvas-toolbar > span i { width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 0 4px #dff8ed; }
.canvas-toolbar button { padding: 5px 8px; color: #52647a; font-size: 9px; border: 0; background: transparent; }
.pipeline-canvas { position: relative; min-height: 615px; overflow: auto; background-color: #f8fbff; background-image: radial-gradient(#cbd8e8 1px, transparent 1px); background-size: 19px 19px; }
.edge-layer { position: absolute; inset: 0; min-width: 850px; min-height: 615px; overflow: visible; pointer-events: none; }
.pipeline-edge { pointer-events: stroke; cursor: pointer; }.pipeline-edge path { fill: none; stroke: #87a7c9; stroke-width: 2; }.pipeline-edge:hover path { stroke: #dc2626; stroke-width: 3; }.pipeline-edge circle { fill: #3b82f6; }
.canvas-node { position: absolute; display: grid; grid-template-columns: 34px minmax(0, 1fr) 18px; gap: 8px; align-items: center; width: 190px; min-height: 82px; padding: 11px; border: 1px solid #cedbea; border-left: 4px solid var(--node-color); border-radius: 9px; background: rgba(255,255,255,.96); box-shadow: 0 5px 15px rgba(32, 61, 92, .08); cursor: grab; user-select: none; }
.canvas-node:active { cursor: grabbing; }.canvas-node.is-selected { border-color: #60a5fa; border-left-color: var(--node-color); box-shadow: 0 0 0 3px rgba(37,99,235,.12), 0 8px 18px rgba(32,61,92,.12); }.canvas-node.is-running { animation: running-node 1.3s ease-in-out infinite; }.canvas-node.is-success { background: #f6fffb; }
.node-icon { display: grid; place-items: center; width: 34px; height: 34px; color: var(--node-color); border-radius: 8px; background: color-mix(in srgb, var(--node-color) 10%, white); }
.canvas-node small, .canvas-node strong, .canvas-node p { display: block; }.canvas-node small { color: #8799ad; font: 8px monospace; text-transform: uppercase; }.canvas-node strong { margin-top: 2px; font-size: 11px; }.canvas-node p { margin-top: 4px; overflow: hidden; color: var(--muted); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.node-state { color: #10b981; }
.node-port { position: absolute; z-index: 2; top: 34px; width: 14px; height: 14px; padding: 0; border: 3px solid #fff; border-radius: 50%; background: #7f9dbd; box-shadow: 0 0 0 1px #7694b5; }.input-port { left: -9px; }.output-port { right: -9px; }.node-port:hover, .node-port.is-connecting { background: #2563eb; box-shadow: 0 0 0 5px rgba(37,99,235,.16); }
.canvas-empty { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 8px; color: #7890a9; text-align: center; }.canvas-empty > span { display: grid; place-items: center; width: 64px; height: 64px; border: 1px dashed #a9bdd3; border-radius: 17px; background: rgba(255,255,255,.7); }.canvas-empty strong { color: #405975; }.canvas-empty p { font-size: 11px; }.canvas-empty .btn { margin-top: 6px; }
.canvas-status { border-top: 1px solid var(--line-soft); border-bottom: 0; color: var(--muted); font-size: 9px; }.canvas-status strong { color: #1d4ed8; }
.property-node-head { display: grid; grid-template-columns: 42px minmax(0, 1fr); gap: 10px; align-items: center; margin-bottom: 15px; padding: 12px; border-radius: 9px; background: #f7faff; }.property-node-head > span { display: grid; place-items: center; width: 42px; height: 42px; color: #fff; border-radius: 10px; }.property-node-head strong, .property-node-head small { display: block; }.property-node-head small { margin-top: 3px; color: var(--muted); font: 8px monospace; }
.property-fields { display: grid; gap: 11px; }.property-fields label > span { display: block; margin-bottom: 5px; color: #66778a; font: 9px monospace; }.property-fields input, .property-fields select { width: 100%; min-height: 36px; padding: 0 9px; color: var(--ink-2); border: 1px solid var(--line); border-radius: 7px; background: #fff; }
.property-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin: 14px 0; }.property-meta span { padding: 9px; color: var(--muted); font-size: 9px; border: 1px solid var(--line-soft); border-radius: 7px; }.property-meta strong { display: block; margin-top: 4px; color: var(--ink); font-size: 15px; }.danger-button { color: #b42318; border-color: #fecaca; }.property-empty { display: grid; place-items: center; gap: 8px; min-height: 270px; color: var(--muted-2); text-align: center; }.property-empty p { max-width: 150px; font-size: 11px; line-height: 1.5; }
@keyframes running-node { 50% { box-shadow: 0 0 0 5px rgba(37,99,235,.12), 0 10px 22px rgba(37,99,235,.18); } }
@media (max-width: 1180px) { .builder-shell { grid-template-columns: 185px minmax(580px, 1fr); overflow-x: auto; }.property-panel { grid-column: 1 / -1; }.property-panel .property-fields { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 760px) { .builder-shell { display: block; }.node-library { margin-bottom: 12px; }.node-library > button { display: inline-grid; width: calc(50% - 5px); margin-right: 5px; }.pipeline-canvas-panel { min-height: 620px; }.property-panel { margin-top: 12px; }.property-panel .property-fields { grid-template-columns: 1fr; } }
</style>
