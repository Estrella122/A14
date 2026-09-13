<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import { executionStatus } from '../utils/executionStatus'
import IntegratedEvidencePanel from '../components/IntegratedEvidencePanel.vue'
import AgentTracePanel from '../components/AgentTracePanel.vue'
import AgentSkillCenter from '../components/AgentSkillCenter.vue'
import RuntimeObservabilityPanel from '../components/RuntimeObservabilityPanel.vue'
import AgentExecutionTimeline from '../components/AgentExecutionTimeline.vue'
import { getAgentSkillRun, getAgentSkillEvents, getAgentSkills, startAgentLiveRun } from '../api/agent'
import { announcePipelineUpdate, artifactUrl, getPipelineRun, listPipelineRuns, uploadPipelineFile } from '../api/pipeline'
import { buildSceneState } from '../composables/useSceneBinding'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildRuntimeObservability } from '../utils/runtimeObservability'
import { applyRuntimeEvents, mergeRuntimeEvents } from '../utils/runtimeEvents'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate'])

const chatStorageKey = `processpilot-chat-${props.project.id}`
function readSavedChat() {
  try {
    const persisted = window.localStorage.getItem(chatStorageKey)
    const legacy = window.sessionStorage.getItem(chatStorageKey)
    if (!persisted && legacy) window.localStorage.setItem(chatStorageKey, legacy)
    return JSON.parse(persisted || legacy || 'null')
  } catch { return null }
}
const savedChat = readSavedChat()
const welcomeMessage = { id: 1, role: 'agent', text: `你好，我已进入 ${props.project.name}。你可以像和工程师交流一样直接提问；当前场景存在真实运行时我会引用任务证据，只有你明确要求重跑时才会执行算法。`, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }

const prompt = ref(savedChat?.prompt ?? '')
const isRunning = ref(false)
const liveProgress = ref(null)
const activeLiveRun = ref(savedChat?.activeLiveRun ?? null)
const chatThread = ref(null)
const fileInput = ref(null)
const uploading = ref(false)
const basicAnalysisReady = ref(false)
const responseState = ref(savedChat?.responseState ?? null)
const runtimeHistory = ref(savedChat?.runtimeHistory ?? {})
const recentRuns = ref([])
const selectedRun = ref(null)
const skillCatalog = ref(null)
const skillCatalogLoading = ref(true)
const skillCatalogError = ref('')
const messages = ref(savedChat?.messages?.length ? savedChat.messages : [welcomeMessage])
const liveLogs = ref(savedChat?.liveLogs ?? [])
const logsNewestFirst = ref(true)
const displayedLogs = computed(() => logsNewestFirst.value ? liveLogs.value : [...liveLogs.value].reverse())
const { latestRun } = useLatestPipelineRun()
let pollController
let disposed = false
const activeRun = computed(() => selectedRun.value ?? latestRun.value)
const sceneState = computed(() => buildSceneState(props.project, activeRun.value))
const runtimeObservation = computed(() => buildRuntimeObservability(responseState.value ?? {}))

const promptTemplates = computed(() => ({
  blast_furnace: ['提取高炉高信噪比动态数据并评估铁水硅模型', '判断矿焦比和鼓风流量是否存在共线性', '以稳健性优先重新执行闭环寻优'],
  debutanizer_column: ['提取脱丁烷塔高信噪比动态数据', '评估回流量到塔底 C4 浓度的时滞是否可信', '比较精馏塔候选模型的残差白噪声检验'],
  industrial_dryer: ['提取干燥器热风阶跃动态数据', '分析热风温度与产品含水率的动态响应', '检查多变量干燥模型的可辨识性与共线性'],
}[props.project.scenarioId] ?? ['提取当前场景高信噪比动态数据', '分析当前模型的 R²、RMSE 和残差是否可靠', '以稳健性优先重新执行闭环寻优']))

const iconMap = { intent: 'spark', standardization: 'network', cleaning: 'clean', selection: 'segments', modeling: 'model', optimization: 'loop', review: 'shield', report: 'report' }
const skillCategoryIcon = { orchestration: 'spark', data: 'database', selection: 'segments', modeling: 'model', delivery: 'report' }
const intentLabels = { conversation: '自然对话', capability: '能力说明', clarification: '需要确认', diagnosis: '问题诊断', overview: '任务总览', standardization: '字段标准化', cleaning: '数据清洗', selection: '动态优选', lag: '时滞分析', collinearity: '共线性处理', modeling: '系统辨识', optimization: '闭环寻优', review: 'Agent评审' }
const planNodes = computed(() => {
  if (responseState.value?.skill_plan?.steps?.length) {
    const executionMap = Object.fromEntries((responseState.value.skill_executions ?? []).map((item) => [item.skill_id, item]))
    return responseState.value.skill_plan.steps.map((step) => ({
      key: step.skill_id,
      name: step.name,
      tool: step.skill_id,
      output: `${step.reason} · 匹配 ${(Number(step.relevance_score ?? 0) * 100).toFixed(0)}%`,
      status: executionMap[step.skill_id]?.status ?? step.status,
      icon: skillCategoryIcon[step.category] ?? 'loop',
    }))
  }
  return (responseState.value?.plan ?? activeRun.value?.stages?.map((stage) => ({ key: stage.key, name: stage.label, tool: stage.key, output: stage.message, status: stage.status })) ?? []).map((node) => ({ ...node, icon: iconMap[node.key] ?? 'loop' }))
})
const intent = computed(() => responseState.value?.intent ?? { key: 'overview', confidence: 0, keywords: [] })
const contextRunId = computed(() => responseState.value?.run_id ?? activeRun.value?.run_id ?? '尚无任务')
const reportUrl = computed(() => activeRun.value?.artifacts?.analysis_report_md ? artifactUrl(activeRun.value.run_id, 'analysis_report_md') : '')

watch([messages, responseState, runtimeHistory, liveLogs, prompt], () => {
  try {
    const persistedResponse = responseState.value ? { ...responseState.value, snapshot: null } : null
    window.localStorage.setItem(chatStorageKey, JSON.stringify({
      prompt: prompt.value,
      messages: messages.value.slice(-60),
      responseState: persistedResponse,
      runtimeHistory: runtimeHistory.value,
      selectedRunId: selectedRun.value?.run_id ?? activeRun.value?.run_id ?? null,
      liveLogs: liveLogs.value.slice(0, 20),
      activeLiveRun: activeLiveRun.value,
    }))
  } catch { /* Conversation persistence is best effort. */ }
}, { deep: true })

watch(() => activeRun.value?.run_id, (runId) => {
  if (runId && responseState.value?.run_id !== runId && runtimeHistory.value[runId]) responseState.value = runtimeHistory.value[runId]
  else if (runId && responseState.value?.run_id !== runId) responseState.value = null
})

function rememberRuntime(result) {
  if (!result?.run_id) return
  runtimeHistory.value = {
    ...runtimeHistory.value,
    [result.run_id]: {
      run_id: result.run_id,
      skill_run_id: result.skill_run_id,
      runtime_observability: buildRuntimeObservability(result),
    },
  }
}

function setTemplate(text) {
  prompt.value = text
}

function stepNumber(index) {
  return String(index + 1).padStart(2, '0')
}

function skillActivityText(skill) {
  if (skill.execution_state) {
    const suffix = skill.executor_selection_kind === 'stage_support' ? '（阶段共用）' : skill.executor_selection_kind === 'direct' ? '（直接命中）' : ''
    return `${executionStatus(skill.execution_state).label}${suffix}`
  }
  if (['success', 'partial', 'blocked', 'failed', 'skipped', 'unavailable'].includes(skill.status)) return executionStatus(skill.status).label
  return skill.activity === 'executed' ? '旧版执行记录，未核验' : skill.activity === 'read' ? '取证' : skill.activity === 'planned' ? '规划' : '调用'
}

async function scrollToLatest() {
  await nextTick()
  if (chatThread.value) chatThread.value.scrollTop = chatThread.value.scrollHeight
}

async function pollLiveRun(live, timelineMessage) {
  isRunning.value = true
  activeLiveRun.value = live
  let after = Number(live.after ?? 0)
  pollController?.abort()
  pollController = new AbortController()
  while (true) {
    const payload = await getAgentSkillEvents(live.skill_run_id, after, { signal: pollController.signal })
    timelineMessage.events = mergeRuntimeEvents(timelineMessage.events, payload.events ?? [])
    after = Number(payload.next_sequence ?? after)
    timelineMessage.status = payload.status
    timelineMessage.metrics = payload.metrics ?? {}
    activeLiveRun.value = { ...live, after, status: payload.status }
    liveProgress.value = [...timelineMessage.events].reverse().find((event) => Number.isFinite(event.progress))?.progress ?? null
    responseState.value = {
      ...(responseState.value ?? { run_id: live.run_id }),
      skill_run_id: live.skill_run_id,
      runtime_observability: applyRuntimeEvents(responseState.value?.runtime_observability, payload.events ?? []),
    }
    await scrollToLatest()
    if (payload.status === 'completed') return payload.result
    if (payload.status === 'failed') throw new Error(payload.error || 'Agent 执行失败')
    await new Promise((resolve) => window.setTimeout(resolve, 450))
  }
}

function appendAgentResult(result, prefix = '') {
  responseState.value = result
  rememberRuntime(result)
  liveLogs.value = [...(result.logs ?? []), ...liveLogs.value].slice(0, 18)
  messages.value.push({
    id: Date.now() + 2, role: 'agent', text: prefix + result.answer, cards: result.cards,
    skills: result.skill_executions?.map((item) => ({ id: item.skill_id, name: item.name, status: item.status, activity: item.activity, execution_state: item.execution_state, executor_selection_kind: item.executor_selection_kind })) ?? [],
    skillRunId: result.skill_run_id, skillSummary: result.skill_summary, deliverables: result.deliverables ?? [],
    runId: result.run_id, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  })
  if (result.snapshot) {
    latestRun.value = result.snapshot
    selectedRun.value = result.snapshot
    announcePipelineUpdate(result.snapshot)
  }
}

async function executeLiveMessage(userText, runId, prefix = '') {
  const started = await startAgentLiveRun(userText, runId, responseState.value?.intent?.key, responseState.value?.intent?.matched ?? [])
  const timelineMessage = { id: Date.now() + 1, role: 'runtime', events: [], status: 'running', metrics: {}, skillRunId: started.skill_run_id, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  messages.value.push(timelineMessage)
  const result = await pollLiveRun(started, timelineMessage)
  appendAgentResult(result, prefix)
  activeLiveRun.value = null
  liveProgress.value = null
  return result
}

async function waitForPipeline(runId, predicate, timeoutMs = 60000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const snapshot = await getPipelineRun(runId)
    latestRun.value = snapshot
    selectedRun.value = snapshot
    announcePipelineUpdate(snapshot)
    if (predicate(snapshot)) return snapshot
    await new Promise((resolve) => window.setTimeout(resolve, 700))
  }
  throw new Error(`基础分析在 ${Math.round(timeoutMs / 1000)} 秒内未返回`)
}

async function monitorExtendedAnalysis(runId) {
  try {
    const snapshot = await waitForPipeline(runId, (item) => ['completed', 'failed', 'needs_review'].includes(item.status), 10 * 60 * 1000)
    if (disposed) return
    if (snapshot.status === 'completed') {
      messages.value.push({ id: Date.now(), role: 'agent', text: '深度分析已在后台完成：系统辨识、候选寻优、评审与报告产物现已可用。', runId, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    } else if (snapshot.status === 'failed') {
      messages.value.push({ id: Date.now(), role: 'agent', text: `基础分析已保留；后台深度分析失败：${snapshot.error?.message ?? '未知错误'}`, error: true, runId, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    }
  } catch (error) {
    if (!disposed) messages.value.push({ id: Date.now(), role: 'agent', text: `基础分析已保留；后台深度分析状态：${error.message}`, error: true, runId, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
  }
}

async function runWorkflow() {
  if (!prompt.value.trim() || isRunning.value) return
  const userText = prompt.value.trim()
  messages.value.push({ id: Date.now(), role: 'user', text: userText, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
  prompt.value = ''
  isRunning.value = true
  await scrollToLatest()
  emit('notify', { tone: 'info', title: 'Agent 正在执行', message: '实时状态将直接来自后端 Runtime。' })
  try {
    const result = await executeLiveMessage(userText, activeRun.value?.run_id)
    emit('notify', { tone: result.blocked ? 'warning' : 'success', title: result.blocked ? 'Agent 已阻断不匹配任务' : 'Agent 执行完成', message: `意图：${intentLabels[result.intent.key] ?? result.intent.key}` })
  } catch (error) {
    activeLiveRun.value = null
    messages.value.push({ id: Date.now() + 2, role: 'agent', text: `本次请求失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    emit('notify', { tone: 'warning', title: 'Agent 请求失败', message: error.message })
  } finally {
    isRunning.value = false
    await scrollToLatest()
  }
}

function chooseCsv() {
  fileInput.value?.click()
}

function exportConversation() {
  const body = messages.value.map((message) => `## ${message.role === 'agent' ? 'Agent' : '用户'} · ${message.time}\n\n${message.text}`).join('\n\n')
  const blob = new Blob([`# ProcessPilot Agent 对话记录\n\n任务：${contextRunId.value}\n\n${body}\n`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `agent-conversation-${contextRunId.value}.md`
  link.click()
  URL.revokeObjectURL(url)
  emit('notify', { tone: 'success', title: '对话记录已导出', message: '已生成 Markdown 对话记录。' })
}

async function handleCsv(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || uploading.value) return
  uploading.value = true
  basicAnalysisReady.value = false
  isRunning.value = true
  const uploadMessage = { id: Date.now(), role: 'user', text: `上传并分析CSV：${file.name}`, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  messages.value.push(uploadMessage)
  await scrollToLatest()
  try {
    const created = await uploadPipelineFile(file, { scenarioId: 'auto', projectSceneId: props.project.scenarioId, instruction: '请根据上传数据识别工业场景，由Agent总控从头执行并生成分析报告', resampleRule: props.project.resampleRule, maxLag: props.project.maxLag, asyncAnalysis: true })
    // A successfully created CSV run starts a fresh evidence conversation.
    // Failed uploads keep the previous conversation so troubleshooting context is not lost.
    prompt.value = ''
    messages.value = [uploadMessage]
    responseState.value = null
    liveLogs.value = []
    latestRun.value = created
    selectedRun.value = created
    announcePipelineUpdate(created)
    const snapshot = await waitForPipeline(created.run_id, (item) => Boolean(item.results?.cleaning) || ['failed', 'needs_review'].includes(item.status))
    if (snapshot.status === 'failed') throw new Error(snapshot.error?.message ?? '流水线基础分析失败')
    basicAnalysisReady.value = true
    const result = await executeLiveMessage('快速分析当前上传数据的数据概况、数据质量、能源表现和变化趋势', snapshot.run_id, `已接收 ${file.name}。基础分析已完成；深度建模与寻优正在后台继续。`)
    liveLogs.value = [
      ...(result.logs ?? []),
      ...snapshot.stages.map((stage) => ({ time: stage.finished_at ?? snapshot.updated_at, level: stage.status === 'completed' ? 'TOOL' : 'WARN', text: `${stage.label}：${stage.message}` })),
    ].slice(0, 18)
    emit('notify', { tone: 'success', title: 'CSV基础分析已完成', message: `任务 ${snapshot.run_id} 已返回首版结果，深度分析在后台继续。` })
    void monitorExtendedAnalysis(snapshot.run_id)
  } catch (error) {
    messages.value.push({ id: Date.now() + 1, role: 'agent', text: `CSV执行失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    emit('notify', { tone: 'warning', title: 'CSV分析失败', message: error.message })
  } finally {
    uploading.value = false
    isRunning.value = false
    await scrollToLatest()
  }
}

onMounted(async () => {
  await Promise.allSettled([
    getAgentSkills().then((result) => { skillCatalog.value = result }).catch((error) => { skillCatalogError.value = error.message }).finally(() => { skillCatalogLoading.value = false }),
    listPipelineRuns({ limit: 20 }).then((payload) => {
      recentRuns.value = (Array.isArray(payload) ? payload : payload?.results ?? payload?.runs ?? []).slice(0, 20)
      const restored = recentRuns.value.find((run) => run.run_id === savedChat?.selectedRunId)
      if (restored) selectedRun.value = restored
    }),
  ])
  if (activeLiveRun.value?.skill_run_id && activeLiveRun.value.status === 'running') {
    const timelineMessage = messages.value.find((message) => message.role === 'runtime' && message.skillRunId === activeLiveRun.value.skill_run_id) ?? { id: Date.now(), role: 'runtime', events: [], status: 'running', metrics: {}, skillRunId: activeLiveRun.value.skill_run_id }
    if (!messages.value.includes(timelineMessage)) messages.value.push(timelineMessage)
    try {
      const result = await pollLiveRun(activeLiveRun.value, timelineMessage)
      appendAgentResult(result)
      activeLiveRun.value = null
    } catch (error) {
      if (error.name !== 'AbortError') messages.value.push({ id: Date.now() + 1, role: 'agent', text: `恢复实时任务失败：${error.message}`, error: true })
      activeLiveRun.value = null
    } finally { isRunning.value = false }
  }
  if (responseState.value?.skill_run_id) {
    try {
      const skillRun = await getAgentSkillRun(responseState.value.skill_run_id)
      responseState.value = { ...responseState.value, runtime_observability: buildRuntimeObservability(skillRun) }
      rememberRuntime(responseState.value)
    } catch { /* Persisted observability remains usable if the runtime record expired. */ }
  }
  scrollToLatest()
})
onBeforeUnmount(() => { disposed = true; pollController?.abort() })

function switchRun(event) {
  const run = recentRuns.value.find((item) => item.run_id === event.target.value)
  if (run) selectedRun.value = run
}
</script>

<template>
  <div class="view-stack agent-view">
    <PageHeader
      eyebrow="Natural Language Orchestration"
      title="Agent 智能中枢"
      description="用工业自然语言描述目标，Agent 自动拆解意图、组装算法流水线，并以辨识指标驱动预处理策略持续自演进。"
    >
      <template #actions>
        <label class="run-switcher"><span>最近运行</span><select :value="activeRun?.run_id ?? ''" aria-label="切换最近运行" @change="switchRun"><option v-for="run in recentRuns" :key="run.run_id" :value="run.run_id">{{ run.original_name }} · {{ run.run_id.slice(-8) }}</option></select></label>
        <input ref="fileInput" class="visually-hidden" type="file" accept=".csv,text/csv" @change="handleCsv" />
        <button class="btn btn-primary" type="button" :disabled="uploading" @click="chooseCsv"><AppIcon :name="uploading ? 'loop' : 'upload'" :class="{ spinning: uploading }" />{{ uploading ? '正在生成基础分析' : '上传CSV并分析' }}</button>
        <StatusPill v-if="basicAnalysisReady && activeRun?.status === 'running'" tone="brand" dot>基础结果可用 · 深度分析进行中</StatusPill>
        <StatusPill tone="success" dot>证据 Agent 在线</StatusPill>
        <StatusPill tone="neutral"><AppIcon name="shield" :size="14" /> 本地安全执行</StatusPill>
      </template>
    </PageHeader>

    <IntegratedEvidencePanel module="agent" />

    <AgentSkillCenter
      :catalog="skillCatalog"
      :executions="responseState?.skill_executions ?? []"
      :loading="skillCatalogLoading"
      :error="skillCatalogError"
    />

    <RuntimeObservabilityPanel :runtime="runtimeObservation" />

    <div class="agent-layout">
      <section class="panel chat-panel">
        <div class="chat-header">
          <div class="agent-avatar"><AppIcon name="spark" /></div>
          <div><strong>ProcessPilot Agent</strong><span><i></i> 工业建模智能中枢</span></div>
          <button class="icon-button" type="button" aria-label="导出当前对话" title="导出当前对话" @click="exportConversation"><AppIcon name="download" /></button>
        </div>

        <div ref="chatThread" class="chat-thread">
          <div v-for="message in messages" :key="message.id" class="message" :class="message.role === 'agent' ? 'message-agent' : message.role === 'runtime' ? 'message-runtime' : 'message-user'">
            <AgentExecutionTimeline v-if="message.role === 'runtime'" :events="message.events" :status="message.status" :metrics="message.metrics" />
            <div v-if="message.role === 'agent'" class="message-avatar"><AppIcon name="spark" :size="17" /></div>
            <div v-if="message.role !== 'runtime'" class="message-bubble" :class="{ 'rich-message': message.cards?.length, 'message-error': message.error }">
              <p>{{ message.text }}</p>
              <div v-if="message.cards?.length" class="intent-chips"><span v-for="card in message.cards" :key="card.label">{{ card.label }}：{{ card.value ?? '—' }}</span></div>
              <div v-if="message.skills?.length" class="message-skill-chain">
                <div><AppIcon name="network" :size="13" /><strong v-if="message.skillSummary?.read != null">Skill 证据核验 · 取证 {{ message.skillSummary?.read ?? 0 }} · 规划 {{ message.skillSummary?.planned ?? 0 }} · 缺证据 {{ message.skillSummary?.unavailable ?? 0 }} · 阻断 {{ message.skillSummary?.blocked ?? 0 }}</strong><strong v-else>历史 Skill 记录（未经新版证据核验）</strong><code>{{ message.skillRunId }}</code></div>
                <span v-for="skill in message.skills" :key="skill.id" :title="skill.id" :class="`status-${executionStatus(skill.status).tone}`"><AppIcon :name="executionStatus(skill.status).icon" :size="11" />{{ skillActivityText(skill) }} · {{ skill.name }}</span>
              </div>
              <div v-if="message.deliverables?.length" class="message-deliverables">
                <strong><AppIcon name="download" :size="12" />结果产物</strong>
                <a v-for="item in message.deliverables" :key="item.key" :href="artifactUrl(message.runId, item.key)">{{ item.label }}</a>
              </div>
              <span>{{ message.time }}</span>
            </div>
          </div>

        </div>

        <div class="prompt-templates">
          <button v-for="item in (responseState?.suggestions ?? promptTemplates)" :key="item" type="button" @click="setTemplate(item)">{{ item }}</button>
        </div>
        <div v-if="activeRun?.status === 'completed'" class="agent-delivery-bar">
          <span><AppIcon name="check" :size="15" />任务 {{ activeRun.run_id }} 已完成</span>
          <a :href="artifactUrl(activeRun.run_id, 'standardized_csv')">标准化CSV</a>
          <a :href="artifactUrl(activeRun.run_id, 'cleaned_csv')">清洗CSV</a>
          <a v-if="activeRun.artifacts?.segments_csv" :href="artifactUrl(activeRun.run_id, 'segments_csv')">动态段CSV</a>
          <a v-if="activeRun.artifacts?.modeling_csv" :href="artifactUrl(activeRun.run_id, 'modeling_csv')">建模数据CSV</a>
          <a :href="artifactUrl(activeRun.run_id, 'metrics_json')">模型指标</a>
          <a :href="artifactUrl(activeRun.run_id, 'optimization_json')">寻优记录</a>
          <a v-if="reportUrl" class="report-link" :href="reportUrl"><AppIcon name="download" :size="14" />分析报告</a>
        </div>
        <div class="prompt-composer" :class="{ 'is-running': isRunning }">
          <textarea v-model="prompt" rows="3" aria-label="输入问题或工业建模指令" placeholder="例如：这批数据最大的问题是什么？为什么第3轮最好？"></textarea>
          <div class="composer-footer">
            <div><span class="composer-tag">当前任务</span><span>{{ contextRunId }}</span></div>
            <button class="send-button" type="button" :disabled="isRunning || !prompt.trim()" @click="runWorkflow">
              <AppIcon :name="isRunning ? 'loop' : 'arrow'" :class="{ spinning: isRunning }" />
              {{ isRunning ? (liveProgress == null ? '处理中' : `处理中 ${liveProgress}%`) : '发送' }}
            </button>
          </div>
          <div v-if="isRunning && liveProgress != null" class="composer-progress"><span :style="{ width: `${liveProgress}%` }"></span></div>
        </div>
      </section>

      <aside class="agent-side-stack">
        <section class="panel intent-panel">
          <div class="section-heading compact"><div><span class="section-kicker">结构化意图</span><h2>Agent 解析结果</h2></div><StatusPill :tone="responseState ? 'success' : 'neutral'">任务理解 {{ (intent.confidence * 100).toFixed(0) }}%</StatusPill></div>
          <dl class="intent-list">
            <div><dt>当前任务</dt><dd><code>{{ contextRunId }}</code></dd></div>
            <div><dt>识别意图</dt><dd>{{ intentLabels[intent.key] ?? intent.key }}</dd></div>
            <div><dt>候选召回线索</dt><dd>{{ intent.keywords?.join(' · ') || '语义与上下文' }}</dd></div>
            <div><dt>执行模式</dt><dd>{{ responseState?.blocked ? '设备门禁阻断' : responseState?.executed ? '真实重跑' : '只读证据分析' }}</dd></div>
            <div><dt>页面焦点</dt><dd>{{ intentLabels[intent.key] ?? '任务总览' }}</dd></div>
          </dl>
        </section>
        <section class="panel runtime-panel">
          <div class="section-heading compact"><div><span class="section-kicker">运行环境</span><h2>安全与资源</h2></div></div>
          <div class="runtime-grid">
            <div><span class="runtime-icon"><AppIcon name="shield" /></span><p><strong>本地任务目录</strong><small>独立产物 · 源数据留存</small></p><StatusPill tone="success" dot>在线</StatusPill></div>
            <div><span class="runtime-icon"><AppIcon name="spark" /></span><p><strong>Evidence Agent</strong><small>意图路由 · 证据回答</small></p><StatusPill tone="brand">可追溯</StatusPill></div>
            <div><span class="runtime-icon"><AppIcon name="model" /></span><p><strong>Python Pipeline</strong><small>pandas · ARX · 互相关</small></p><StatusPill tone="success" dot>就绪</StatusPill></div>
          </div>
        </section>
      </aside>
    </div>

    <section class="panel plan-panel">
      <div class="section-heading">
        <div><span class="section-kicker">动态编排计划</span><h2>Agent 自动组装的算法流水线</h2></div>
        <div class="plan-summary"><span>{{ planNodes.length }} 阶段</span><span>{{ responseState?.blocked ? '设备门禁阻断' : responseState?.executed ? '已真实执行' : '证据分析' }}</span><span>{{ contextRunId }}</span></div>
      </div>
      <div class="plan-flow">
        <article
          v-for="(node, index) in planNodes"
          :key="node.name"
          class="plan-node"
          :class="{ 'is-complete': ['completed', 'success'].includes(node.status), 'is-partial': node.status === 'partial', 'is-blocked': node.status === 'blocked', 'is-failed': node.status === 'failed', 'is-current': node.status === 'executing', 'is-waiting': ['pending', 'skipped', 'queued', 'waiting', 'deferred'].includes(node.status) }"
        >
          <span class="plan-node-icon"><AppIcon :name="node.icon" /></span>
          <div><span>{{ stepNumber(index) }}</span><strong>{{ node.name }}</strong><code>{{ node.tool }}</code><small>{{ node.output }}</small></div>
          <span class="plan-node-state" :title="executionStatus(node.status).label"><AppIcon :name="node.status === 'executing' ? 'loop' : executionStatus(node.status).icon" :class="{ spinning: node.status === 'executing' }" /></span>
        </article>
      </div>
    </section>

    <AgentTracePanel :run-id="contextRunId === '尚无任务' ? '' : contextRunId" :running="isRunning" :scenario-id="project.scenarioId" :fallback-scenario-id="sceneState.data_scene.id || props.project.scenarioId" />

    <section class="panel console-panel">
      <div class="console-header"><div><i class="console-dot red"></i><i class="console-dot amber"></i><i class="console-dot green"></i></div><strong>AGENT TRACE · {{ contextRunId }}</strong><button type="button" @click="logsNewestFirst = !logsNewestFirst">{{ logsNewestFirst ? '最新优先' : '时间顺序' }}</button></div>
      <div class="console-body" role="log" aria-label="Agent 执行日志">
        <p v-if="!liveLogs.length"><time>--:--:--</time><span class="level-info">INFO</span><code>发送指令后显示真实意图解析与工具访问日志</code></p>
        <p v-for="(log, index) in displayedLogs" :key="`${log.time}-${index}`"><time>{{ log.time.slice(11, 19) }}</time><span :class="`level-${log.level.toLowerCase()}`">{{ log.level }}</span><code>{{ log.text }}</code></p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.run-switcher { display:flex;align-items:center;gap:6px;padding:5px 7px;border:1px solid #dbe3ef;border-radius:8px;background:#fff }.run-switcher span { color:#64748b;font-size:8px }.run-switcher select { max-width:185px;border:0;outline:0;color:#334155;background:transparent;font-size:8px }
.agent-delivery-bar { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; padding: 9px 17px; border-top: 1px solid #e2e8f0; background: #f8fafc; }
.agent-delivery-bar span { display: inline-flex; align-items: center; gap: 5px; margin-right: auto; color: #166534; font-size: 9px; }
.agent-delivery-bar a { padding: 5px 8px; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; background: #fff; text-decoration: none; font-size: 8px; }
.agent-delivery-bar .report-link { display: inline-flex; align-items: center; gap: 4px; border-color: #93c5fd; color: #1d4ed8; background: #eff6ff; }
.message-error { border-color: #fecaca; background: #fff7f7; }
.message-skill-chain { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 9px; padding-top: 8px; border-top: 1px solid rgba(148, 163, 184, .22); }
.message-skill-chain > div { display: flex; align-items: center; gap: 5px; width: 100%; color: #334155; }
.message-skill-chain > div strong { font-size: 8px; }
.message-skill-chain > div code { margin-left: auto; color: #94a3b8; font-size: 7px; }
.message-skill-chain > span { display: inline-flex; align-items: center; gap: 2px; padding: 3px 6px; border: 1px solid #bfdbfe; border-radius: 999px; color: #1d4ed8; background: #eff6ff; font-size: 7px; }
.message-skill-chain > span.status-warning { border-color: #f5c26b; color: #b45309; background: #fffbeb; }
.message-skill-chain > span.status-danger { border-color: #fecaca; color: #b91c1c; background: #fff1f2; }
.message-skill-chain > span.status-neutral { border-color: #cbd5e1; color: #64748b; background: #f8fafc; }
.message-deliverables { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.message-deliverables strong, .message-deliverables a { display: inline-flex; align-items: center; gap: 3px; font-size: 7px; }
.message-deliverables strong { color: #475569; }
.message-deliverables a { padding: 3px 6px; border: 1px solid #a7f3d0; border-radius: 5px; color: #047857; background: #ecfdf5; text-decoration: none; }
@media (max-width: 680px) { .agent-delivery-bar span { width: 100%; margin-right: 0; } }
</style>
