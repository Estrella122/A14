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
import ChatOptimizationSummary from '../components/ChatOptimizationSummary.vue'
import { getAgentLLMProviders, getAgentSkillRun, getAgentSkillEvents, getAgentSkills, startAgentLiveRun, streamAgentSkillEvents } from '../api/agent'
import { announcePipelineUpdate, artifactUrl, getPipelineRun, listPipelineRuns, uploadPipelineFile } from '../api/pipeline'
import { buildSceneState } from '../composables/useSceneBinding'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildRuntimeObservability } from '../utils/runtimeObservability'
import { applyRuntimeEvents, mergeRuntimeEvents } from '../utils/runtimeEvents'

const props = defineProps({
  project: { type: Object, required: true },
  userBoard: { type: Boolean, default: false },
})
const emit = defineEmits(['notify', 'navigate', 'scene-detected'])

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
const historyKey = `${chatStorageKey}-threads`
function readThreads() {
  try { return JSON.parse(window.localStorage.getItem(historyKey) || '[]') } catch { return [] }
}
const conversations = ref(readThreads())
const conversationId = ref(savedChat?.conversationId || crypto.randomUUID())
const historyOpen = ref(false)
const detailsOpen = ref(false)
const preferredSkill = ref('')
const noDataContext = ref(savedChat?.noDataContext ?? false)
const conversationBusy = computed(() => isRunning.value || uploading.value || activeRun.value?.status === 'running')
function conversationSnapshot() {
  return {
    id: conversationId.value, title: messages.value.find((item) => item.role === 'user')?.text.slice(0, 48) || '新对话',
    messages: messages.value, responseState: responseState.value, runtimeHistory: runtimeHistory.value,
    liveLogs: liveLogs.value, selectedRun: activeRun.value, noDataContext: noDataContext.value,
    updatedAt: new Date().toISOString(),
  }
}
function saveConversation() {
  if (uploading.value || !messages.value.some((item) => item.role === 'user')) return
  const entry = JSON.parse(JSON.stringify(conversationSnapshot()))
  conversations.value = [entry, ...conversations.value.filter((item) => item.id !== entry.id)].slice(0, 30)
  try { window.localStorage.setItem(historyKey, JSON.stringify(conversations.value)) } catch { /* Storage may be full. */ }
}
function newConversation() {
  if (conversationBusy.value) return
  saveConversation()
  conversationId.value = crypto.randomUUID()
  messages.value = [{ ...welcomeMessage, text: activeRun.value ? `新对话已开始，当前关联 ${activeRun.value.original_name || '当前数据'}。可以继续提问，或上传另一份 CSV。` : '你好，可以上传 CSV 开始分析。上传后直接提问，就能查看答案、技能和执行过程。' }]
  prompt.value = ''
  responseState.value = null
  runtimeHistory.value = {}
  liveLogs.value = []
  selectedRun.value = activeRun.value
  noDataContext.value = !selectedRun.value
  activeLiveRun.value = null
  preferredSkill.value = ''
  historyOpen.value = false
}
function openConversation(entry) {
  if (conversationBusy.value) return
  saveConversation()
  const stored = JSON.parse(JSON.stringify(entry))
  conversationId.value = stored.id
  messages.value = stored.messages
  responseState.value = stored.responseState
  runtimeHistory.value = stored.runtimeHistory || {}
  liveLogs.value = stored.liveLogs || []
  selectedRun.value = stored.selectedRun
  noDataContext.value = stored.noDataContext || !stored.selectedRun
  prompt.value = ''
  preferredSkill.value = ''
  historyOpen.value = false
  void scrollToLatest()
}
const artifactNames = { standardized_csv: '标准化数据 CSV', cleaned_csv: '清洗后数据 CSV', segments_csv: '动态数据段 CSV', modeling_csv: '建模数据 CSV', metrics_json: '模型指标', optimization_json: '寻优记录', analysis_report_md: '分析报告', quality_report_json: '数据质量报告' }
function openDataView(path) {
  if (activeRun.value) announcePipelineUpdate(activeRun.value)
  emit('navigate', path)
}
function composerKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void runWorkflow()
  }
}

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
const llmCatalog = ref(null)
const llmProvider = ref('evidence')
const llmModel = ref('')
const localLLMBaseUrl = ref('http://127.0.0.1:11434/v1')
const messages = ref(savedChat?.messages?.length ? savedChat.messages : [welcomeMessage])
const liveLogs = ref(savedChat?.liveLogs ?? [])
const logsNewestFirst = ref(true)
const displayedLogs = computed(() => logsNewestFirst.value ? liveLogs.value : [...liveLogs.value].reverse())
const rightModuleOptions = [
  { id: 'pipeline', label: '算法流水线' },
  { id: 'console', label: '工作日志' },
]
const selectedRightModules = ref(rightModuleOptions.map((item) => item.id))
const selectedRightModuleSet = computed(() => new Set(selectedRightModules.value))

function toggleRightModule(id) {
  const idx = selectedRightModules.value.indexOf(id)
  if (idx >= 0) {
    selectedRightModules.value.splice(idx, 1)
  } else {
    selectedRightModules.value.push(id)
  }
}
const { latestRun } = useLatestPipelineRun()
let pollController
let scrollFrame
let disposed = false
const activeRun = computed(() => noDataContext.value ? null : selectedRun.value ?? latestRun.value)
const sceneState = computed(() => buildSceneState(props.project, activeRun.value))
const runtimeObservation = computed(() => buildRuntimeObservability(responseState.value ?? {}))
const hasRuntimeObservation = computed(() => Boolean(
  runtimeObservation.value?.capabilities?.length ||
  runtimeObservation.value?.execution_dag?.steps?.length
))
const activeRunStatusText = computed(() => {
  if (uploading.value) return '上传数据后正在生成基础分析'
  if (isRunning.value) return liveProgress.value == null ? 'Agent 正在同步运行事件' : `Agent 正在运行 · ${liveProgress.value}%`
  if (activeRun.value?.status === 'completed') return '当前任务已完成'
  if (activeRun.value?.status === 'running') return '深度分析进行中'
  return '等待上传或提问'
})

const promptTemplates = computed(() => ({
  blast_furnace: ['提取高炉高信噪比动态数据并评估铁水硅模型', '判断矿焦比和鼓风流量是否存在共线性', '以稳健性优先重新执行闭环寻优'],
  debutanizer_column: ['提取脱丁烷塔高信噪比动态数据', '评估回流量到塔底 C4 浓度的时滞是否可信', '比较精馏塔候选模型的残差白噪声检验'],
  industrial_dryer: ['提取干燥器热风阶跃动态数据', '分析热风温度与产品含水率的动态响应', '检查多变量干燥模型的可辨识性与共线性'],
}[sceneState.value.data_scene.id || props.project.scenarioId] ?? ['提取当前场景高信噪比动态数据', '分析当前模型的 R²、RMSE 和残差是否可靠', '以稳健性优先重新执行闭环寻优']))

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
      activityStatus: executionMap[step.skill_id]?.execution_state ?? (executionMap[step.skill_id]?.activity === 'read' ? 'evidence_only' : null),
      icon: skillCategoryIcon[step.category] ?? 'loop',
    }))
  }
  return (responseState.value?.plan ?? activeRun.value?.stages?.map((stage) => ({ key: stage.key, name: stage.label, tool: stage.key, output: stage.message, status: stage.status })) ?? []).map((node) => ({ ...node, icon: iconMap[node.key] ?? 'loop' }))
})
const intent = computed(() => responseState.value?.intent ?? { key: 'overview', confidence: 0, keywords: [] })
const contextRunId = computed(() => responseState.value?.run_id ?? activeRun.value?.run_id ?? '尚无任务')
const reportUrl = computed(() => activeRun.value?.artifacts?.analysis_report_md ? artifactUrl(activeRun.value.run_id, 'analysis_report_md') : '')
const activeLLMProvider = computed(() => llmCatalog.value?.providers?.find((item) => item.id === llmProvider.value))

function readLLMPreference() {
  try { return JSON.parse(window.localStorage.getItem('processpilot-llm-preference') || 'null') } catch { return null }
}

function llmRequestConfig() {
  return {
    provider: llmProvider.value,
    model: llmModel.value || activeLLMProvider.value?.model,
    ...(llmProvider.value === 'local' ? { base_url: localLLMBaseUrl.value } : {}),
  }
}

watch([llmProvider, llmModel, localLLMBaseUrl], () => {
  try { window.localStorage.setItem('processpilot-llm-preference', JSON.stringify(llmRequestConfig())) } catch { /* preference persistence is optional */ }
})

function handleLLMProviderChange() {
  llmModel.value = activeLLMProvider.value?.model || ''
}

watch([messages, responseState, runtimeHistory, liveLogs, prompt, conversationId, noDataContext], () => {
  try {
    const persistedResponse = responseState.value ? { ...responseState.value, snapshot: null } : null
    window.localStorage.setItem(chatStorageKey, JSON.stringify({
      conversationId: conversationId.value, noDataContext: noDataContext.value,
      prompt: prompt.value,
      messages: messages.value.slice(-60),
      responseState: persistedResponse,
      runtimeHistory: runtimeHistory.value,
      selectedRunId: selectedRun.value?.run_id ?? activeRun.value?.run_id ?? null,
      liveLogs: liveLogs.value.slice(0, 20),
      activeLiveRun: activeLiveRun.value,
    }))
    saveConversation()
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

function scheduleScrollToLatest() {
  if (scrollFrame) return
  scrollFrame = window.requestAnimationFrame(() => {
    scrollFrame = null
    void scrollToLatest()
  })
}

function applyLivePayload(live, timelineMessage, draftMessage, payload) {
  const events = payload.events ?? []
  timelineMessage.events = mergeRuntimeEvents(timelineMessage.events, events)
  pushRuntimeLogs(events)
  const after = Number(payload.next_sequence ?? events.at(-1)?.sequence ?? activeLiveRun.value?.after ?? 0)
  timelineMessage.status = payload.status ?? timelineMessage.status
  timelineMessage.metrics = payload.metrics ?? timelineMessage.metrics
  const answerDelta = events.filter((event) => event.event_type === 'llm_response_delta').map((event) => event.metadata?.delta || '').join('')
  if (answerDelta && draftMessage) draftMessage.text += answerDelta
  const latestStage = [...events].reverse().find((event) => event.event_type !== 'llm_response_delta' && event.message)
  if (latestStage && draftMessage) draftMessage.phase = latestStage.message
  activeLiveRun.value = { ...live, after, status: payload.status ?? 'running' }
  liveProgress.value = [...timelineMessage.events].reverse().find((event) => Number.isFinite(event.progress))?.progress ?? null
  responseState.value = {
    ...(responseState.value ?? { run_id: live.run_id }),
    skill_run_id: live.skill_run_id,
    runtime_observability: applyRuntimeEvents(responseState.value?.runtime_observability, events),
  }
  scheduleScrollToLatest()
  return after
}

function runtimeLogLevel(event) {
  if (['failed', 'blocked'].includes(event.status) || event.event_type === 'run_failed') return 'WARN'
  if (event.event_type?.startsWith('executor_') || event.event_type === 'artifact_produced') return 'TOOL'
  if (event.status === 'completed' || event.status === 'success') return 'BEST'
  return 'INFO'
}

function pushRuntimeLogs(events = []) {
  const visible = events
    .filter((event) => event.event_type !== 'llm_response_delta' && event.message)
    .map((event) => ({
      sequence: event.sequence,
      time: event.timestamp || new Date().toISOString(),
      level: runtimeLogLevel(event),
      text: `${event.executor || event.capability_id || event.skill_id || event.stage || event.event_type}：${event.message}`,
    }))
  if (!visible.length) return
  const existing = new Set(liveLogs.value.map((log) => log.sequence == null ? `${log.time}-${log.text}` : `seq-${log.sequence}`))
  liveLogs.value = [
    ...visible.filter((log) => !existing.has(log.sequence == null ? `${log.time}-${log.text}` : `seq-${log.sequence}`)).reverse(),
    ...liveLogs.value,
  ].slice(0, 40)
}

async function pollLiveRun(live, timelineMessage, draftMessage, initialAfter = null) {
  isRunning.value = true
  activeLiveRun.value = live
  let after = Number(initialAfter ?? live.after ?? 0)
  let delay = 350
  while (true) {
    const payload = await getAgentSkillEvents(live.skill_run_id, after, { signal: pollController.signal })
    after = applyLivePayload(live, timelineMessage, draftMessage, payload)
    if (payload.status === 'completed') return payload.result
    if (payload.status === 'failed') throw new Error(payload.error || 'Agent 执行失败')
    delay = (payload.events?.length ?? 0) > 0 ? 350 : Math.min(2_500, Math.round(delay * 1.6))
    await new Promise((resolve) => window.setTimeout(resolve, document.hidden ? Math.max(delay, 5_000) : delay))
  }
}

async function streamLiveRun(live, timelineMessage, draftMessage) {
  isRunning.value = true
  activeLiveRun.value = live
  pollController?.abort()
  pollController = new AbortController()
  let after = Number(live.after ?? 0)
  try {
    const terminal = await streamAgentSkillEvents(live.skill_run_id, after, {
      signal: pollController.signal,
      onRuntime(event) {
        after = applyLivePayload(live, timelineMessage, draftMessage, {
          status: 'running', events: [event], next_sequence: event.sequence,
        })
      },
    })
    timelineMessage.status = terminal.status
    timelineMessage.metrics = terminal.metrics ?? timelineMessage.metrics
    activeLiveRun.value = { ...live, after: terminal.next_sequence ?? after, status: terminal.status }
    return terminal.result
  } catch (error) {
    if (error.name === 'AbortError') throw error
    if (draftMessage) draftMessage.phase = '实时连接已恢复，正在同步遗漏事件…'
    return pollLiveRun({ ...live, after }, timelineMessage, draftMessage, after)
  }
}

function appendAgentResult(result, prefix = '', draftMessage = null) {
  responseState.value = result
  rememberRuntime(result)
  liveLogs.value = [...(result.logs ?? []), ...liveLogs.value].slice(0, 18)
  const completedMessage = {
    id: Date.now() + 2, role: 'agent', text: prefix + result.answer, cards: result.cards,
    skills: result.skill_executions?.map((item) => ({ id: item.skill_id, name: item.name, status: item.status, activity: item.activity, execution_state: item.execution_state, executor_selection_kind: item.executor_selection_kind })) ?? [],
    skillRunId: result.skill_run_id, skillSummary: result.skill_summary, deliverables: result.deliverables ?? [],
    runId: result.run_id, llm: result.llm, streaming: false, phase: '', time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  }
  if (draftMessage) Object.assign(draftMessage, completedMessage, { id: draftMessage.id })
  else messages.value.push(completedMessage)
  if (result.snapshot) {
    noDataContext.value = false
    latestRun.value = result.snapshot
    selectedRun.value = result.snapshot
    announcePipelineUpdate(result.snapshot)
  }
}

async function executeLiveMessage(userText, runId, prefix = '') {
  const started = await startAgentLiveRun(userText, runId, responseState.value?.intent?.key, responseState.value?.intent?.matched ?? [], llmRequestConfig())
  const timelineMessage = { id: Date.now() + 1, role: 'runtime', events: [], status: 'running', metrics: {}, skillRunId: started.skill_run_id, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  const draftMessage = { id: Date.now() + 2, role: 'agent', text: '', streaming: true, phase: '正在连接 Agent 实时事件流…', skillRunId: started.skill_run_id, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  messages.value.push(timelineMessage, draftMessage)
  try {
    const result = await streamLiveRun(started, timelineMessage, draftMessage)
    appendAgentResult(result, prefix, draftMessage)
    activeLiveRun.value = null
    liveProgress.value = null
    return result
  } catch (error) {
    Object.assign(draftMessage, { text: `本次请求失败：${error.message}`, phase: '', streaming: false, error: true })
    error.renderedInConversation = true
    throw error
  }
}

async function waitForPipeline(runId, predicate, timeoutMs = 60000) {
  const started = Date.now()
  let delay = 500
  while (Date.now() - started < timeoutMs) {
    const snapshot = await getPipelineRun(runId)
    latestRun.value = snapshot
    selectedRun.value = snapshot
    announcePipelineUpdate(snapshot)
    if (predicate(snapshot)) return snapshot
    await new Promise((resolve) => window.setTimeout(resolve, document.hidden ? 5_000 : delay))
    delay = Math.min(3_000, Math.round(delay * 1.45))
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
  if (!activeRun.value?.run_id) {
    emit('notify', { tone: 'warning', title: '请先关联数据', message: '当前聊天服务需要数据上下文。请上传 CSV 后提问，以免引用其他任务的数据。' })
    return
  }
  const userText = prompt.value.trim()
  messages.value.push({ id: Date.now(), role: 'user', text: userText, skillPreference: skillCatalog.value?.skills?.find((item) => item.id === preferredSkill.value)?.name, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
  prompt.value = ''
  isRunning.value = true
  await scrollToLatest()
  emit('notify', { tone: 'info', title: 'Agent 正在执行', message: '实时状态将直接来自后端 Runtime。' })
  try {
    const chosen = skillCatalog.value?.skills?.find((item) => item.id === preferredSkill.value)
    const requestText = chosen ? `技能偏好：${chosen.name}（${chosen.id}）\n用户问题：${userText}` : userText
    const result = await executeLiveMessage(requestText, activeRun.value?.run_id)
    emit('notify', { tone: result.blocked ? 'warning' : 'success', title: result.blocked ? 'Agent 已阻断不匹配任务' : 'Agent 执行完成', message: `意图：${intentLabels[result.intent.key] ?? result.intent.key}` })
  } catch (error) {
    activeLiveRun.value = null
    if (!error.renderedInConversation) messages.value.push({ id: Date.now() + 2, role: 'agent', text: `本次请求失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
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
  if (!file || uploading.value || isRunning.value) return
  saveConversation()
  uploading.value = true
  basicAnalysisReady.value = false
  isRunning.value = true
  liveProgress.value = null
  const uploadMessage = { id: Date.now(), role: 'user', text: `上传并分析CSV：${file.name}`, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  messages.value.push(uploadMessage)
  liveLogs.value = [{ time: new Date().toISOString(), level: 'INFO', text: `已接收 ${file.name}，准备上传并启动 Agent 总控流水线。` }, ...liveLogs.value].slice(0, 40)
  await scrollToLatest()
  try {
    const created = await uploadPipelineFile(file, { scenarioId: 'auto', projectSceneId: props.project.scenarioId, instruction: '请根据上传数据识别工业场景，由Agent总控从头执行并生成分析报告', resampleRule: props.project.resampleRule, maxLag: props.project.maxLag, asyncAnalysis: true })
    // A successfully created CSV run starts a fresh evidence conversation.
    // Failed uploads keep the previous conversation so troubleshooting context is not lost.
    conversationId.value = crypto.randomUUID()
    prompt.value = ''
    messages.value = [uploadMessage]
    responseState.value = null
    liveLogs.value = [{ time: created.created_at ?? new Date().toISOString(), level: 'TOOL', text: `任务 ${created.run_id} 已创建，正在等待基础分析结果。` }]
    noDataContext.value = false
    latestRun.value = created
    selectedRun.value = created
    announcePipelineUpdate(created)
    const snapshot = await waitForPipeline(created.run_id, (item) => Boolean(item.results?.cleaning) || ['failed', 'needs_review'].includes(item.status))
    if (snapshot.status === 'failed') throw new Error(snapshot.error?.message ?? '流水线基础分析失败')
    basicAnalysisReady.value = true
    liveLogs.value = [
      { time: snapshot.updated_at ?? new Date().toISOString(), level: 'BEST', text: `基础分析完成，已进入 Agent 决策摘要与工具轨迹同步阶段。` },
      ...snapshot.stages.map((stage) => ({ time: stage.finished_at ?? snapshot.updated_at ?? new Date().toISOString(), level: stage.status === 'completed' ? 'TOOL' : 'WARN', text: `${stage.label}：${stage.message}` })),
      ...liveLogs.value,
    ].slice(0, 40)
    const result = await executeLiveMessage('快速分析当前上传数据的数据概况、数据质量、能源表现和变化趋势', snapshot.run_id, `已接收 ${file.name}。基础分析已完成；深度建模与寻优正在后台继续。`)
    liveLogs.value = [
      ...(result.logs ?? []),
      ...snapshot.stages.map((stage) => ({ time: stage.finished_at ?? snapshot.updated_at, level: stage.status === 'completed' ? 'TOOL' : 'WARN', text: `${stage.label}：${stage.message}` })),
    ].slice(0, 18)
    emit('notify', { tone: 'success', title: 'CSV基础分析已完成', message: `任务 ${snapshot.run_id} 已返回首版结果，深度分析在后台继续。` })
    void monitorExtendedAnalysis(snapshot.run_id)
    const detectedScenario = snapshot.results?.standardization?.scenario?.scenario_id
    if (detectedScenario) emit('scene-detected', { scenarioId: detectedScenario, runId: snapshot.run_id, path: '/digital-twin/' })
  } catch (error) {
    if (!error.renderedInConversation) messages.value.push({ id: Date.now() + 1, role: 'agent', text: `CSV执行失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    emit('notify', { tone: 'warning', title: 'CSV分析失败', message: error.message })
  } finally {
    uploading.value = false
    isRunning.value = false
    saveConversation()
    await scrollToLatest()
  }
}

onMounted(async () => {
  const savedLLM = readLLMPreference()
  await Promise.allSettled([
    getAgentSkills().then((result) => { skillCatalog.value = result }).catch((error) => { skillCatalogError.value = error.message }).finally(() => { skillCatalogLoading.value = false }),
    listPipelineRuns({ limit: 20 }).then(async (payload) => {
      recentRuns.value = (Array.isArray(payload) ? payload : payload?.results ?? payload?.runs ?? []).slice(0, 20)
      if (savedChat?.selectedRunId && !noDataContext.value) {
        try { selectedRun.value = await getPipelineRun(savedChat.selectedRunId) }
        catch { noDataContext.value = true; selectedRun.value = null }
      }
    }),
    getAgentLLMProviders().then((result) => {
      llmCatalog.value = result
      const candidate = result.providers?.find((item) => item.id === savedLLM?.provider && item.configured)
        ?? result.providers?.find((item) => item.id === result.default_provider && item.configured)
        ?? result.providers?.[0]
      llmProvider.value = candidate?.id || 'evidence'
      llmModel.value = savedLLM?.model || candidate?.model || ''
      localLLMBaseUrl.value = savedLLM?.base_url || result.providers?.find((item) => item.id === 'local')?.base_url || localLLMBaseUrl.value
    }).catch(() => { llmProvider.value = 'evidence' }),
  ])
  if (activeLiveRun.value?.skill_run_id && activeLiveRun.value.status === 'running') {
    isRunning.value = true
    const timelineMessage = messages.value.find((message) => message.role === 'runtime' && message.skillRunId === activeLiveRun.value.skill_run_id) ?? { id: Date.now(), role: 'runtime', events: [], status: 'running', metrics: {}, skillRunId: activeLiveRun.value.skill_run_id }
    const draftMessage = messages.value.find((message) => message.role === 'agent' && message.streaming && message.skillRunId === activeLiveRun.value.skill_run_id) ?? { id: Date.now() + 1, role: 'agent', text: '', streaming: true, phase: '正在恢复 Agent 实时事件流…', skillRunId: activeLiveRun.value.skill_run_id }
    if (!messages.value.includes(timelineMessage)) messages.value.push(timelineMessage)
    if (!messages.value.includes(draftMessage)) messages.value.push(draftMessage)
    try {
      const result = await streamLiveRun(activeLiveRun.value, timelineMessage, draftMessage)
      appendAgentResult(result, '', draftMessage)
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
onBeforeUnmount(() => { disposed = true; pollController?.abort(); if (scrollFrame) window.cancelAnimationFrame(scrollFrame) })

async function switchRun(event) {
  const run = recentRuns.value.find((item) => item.run_id === event.target.value)
  if (!run || isRunning.value) return
  try {
    const snapshot = await getPipelineRun(run.run_id)
    if (props.userBoard) newConversation()
    noDataContext.value = false
    selectedRun.value = snapshot
    if (props.userBoard) messages.value = [{ ...welcomeMessage, text: `已关联 ${snapshot.original_name || '所选数据'}。本次对话将使用这份数据的分析证据。` }]
  } catch (error) { emit('notify', { tone: 'warning', title: '数据关联失败', message: error.message }) }
}
</script>

<template>
  <div class="view-stack agent-view" :class="{ 'is-user-board': userBoard }" @keydown.esc="detailsOpen = false; historyOpen = false">
    <aside v-if="userBoard" class="conversation-sidebar" :class="{ 'is-open': historyOpen }">
      <strong class="sidebar-brand">ProcessPilot <span>工业数据助手</span></strong>
      <button class="new-conversation" type="button" :disabled="conversationBusy" @click="newConversation">＋ 新建对话</button>
      <span class="history-label">历史对话 · 保存在此浏览器</span>
      <nav aria-label="历史对话">
        <button v-for="entry in conversations" :key="entry.id" type="button" :disabled="conversationBusy" :class="{ active: entry.id === conversationId }" @click="openConversation(entry)">{{ entry.title }}</button>
        <p v-if="!conversations.length">你的对话会显示在这里。</p>
      </nav>
      <button type="button" class="staff-link" @click="emit('navigate', '/agent-review/')">打开工作人员模式 ↗</button>
    </aside>
    <div v-if="userBoard" class="user-mode-bar">
      <button type="button" class="history-toggle" aria-label="展开或收起历史对话" :aria-expanded="historyOpen" @click="historyOpen = !historyOpen">☰</button>
      <div class="user-mode-brand">
        <span class="brand-symbol small"><i></i><b></b><em></em></span>
        <strong>ProcessPilot</strong>
      </div>
      <div class="user-mode-bar-spacer"></div>
      <button class="user-mode-staff-btn" type="button" :aria-expanded="detailsOpen" @click="detailsOpen = !detailsOpen"><AppIcon name="network" :size="15" />过程与结果</button>
    </div>

    <PageHeader
      v-if="!userBoard"
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

    <div class="agent-layout">
      <section class="panel chat-panel">
        <div class="chat-header" v-if="!userBoard">
          <div class="agent-avatar"><AppIcon name="spark" /></div>
          <div><strong>ProcessPilot Agent</strong><span><i></i> 工业建模智能中枢</span></div>
          <div class="chat-header-actions">
            <input v-if="userBoard" ref="fileInput" class="visually-hidden" type="file" accept=".csv,text/csv" @change="handleCsv" />
            <button v-if="userBoard" class="icon-button" type="button" :disabled="uploading" aria-label="上传 CSV 并分析" title="上传 CSV 并分析" @click="chooseCsv"><AppIcon :name="uploading ? 'loop' : 'upload'" :class="{ spinning: uploading }" /></button>
            <button class="icon-button" type="button" aria-label="导出当前对话" title="导出当前对话" @click="exportConversation"><AppIcon name="download" /></button>
          </div>
        </div>

        <input v-if="userBoard" ref="fileInput" class="visually-hidden" type="file" accept=".csv,text/csv" @change="handleCsv" />
        <div v-if="userBoard" class="conversation-context"><span>{{ activeRun?.original_name || '未关联数据 · 上传 CSV 开始分析' }}</span><span v-if="activeRun">{{ sceneState.data_scene.display_name }} · {{ activeRunStatusText }}</span></div>
        <div ref="chatThread" class="chat-thread">
          <div v-for="message in messages" :key="message.id" class="message" :class="message.role === 'agent' ? 'message-agent' : message.role === 'runtime' ? 'message-runtime' : 'message-user'">
            <AgentExecutionTimeline v-if="message.role === 'runtime'" :events="message.events" :status="message.status" :metrics="message.metrics" :compact="userBoard" />
            <div v-if="message.role === 'agent'" class="message-avatar"><AppIcon name="spark" :size="17" /></div>
            <div v-if="message.role !== 'runtime'" class="message-bubble" :class="{ 'rich-message': message.cards?.length, 'message-error': message.error }">
              <span v-if="message.streaming" class="streaming-phase"><AppIcon name="loop" class="spinning" :size="11" />{{ message.phase }}</span>
              <p>{{ message.text || (message.streaming ? '正在读取数据证据与 Skill 执行结果…' : '') }}<i v-if="message.streaming" class="streaming-cursor"></i></p>
              <span v-if="message.llm" class="message-model"><AppIcon name="spark" :size="11" />{{ message.llm.used ? `${message.llm.provider} · ${message.llm.model}` : message.llm.fallback ? '大模型不可用 · Evidence 回退' : 'Evidence Agent' }}</span>
              <div v-if="message.cards?.length" class="intent-chips"><span v-for="card in message.cards" :key="card.label">{{ card.label }}：{{ card.value ?? '—' }}</span></div>
              <div v-if="message.skills?.length" class="message-skill-chain">
                <div><AppIcon name="network" :size="13" /><strong v-if="message.skillSummary?.read != null">Skill 证据核验 · 取证 {{ message.skillSummary?.read ?? 0 }} · 规划 {{ message.skillSummary?.planned ?? 0 }} · 缺证据 {{ message.skillSummary?.unavailable ?? 0 }} · 阻断 {{ message.skillSummary?.blocked ?? 0 }}</strong><strong v-else>历史 Skill 记录（未经新版证据核验）</strong><code>{{ message.skillRunId }}</code></div>
                <span v-for="skill in message.skills" :key="skill.id" :title="skill.id" :class="`status-${executionStatus(skill.status).tone}`"><AppIcon :name="executionStatus(skill.status).icon" :size="11" />{{ skillActivityText(skill) }} · {{ skill.name }}</span>
              </div>
              <div v-if="message.deliverables?.length" class="message-deliverables">
                <strong><AppIcon name="download" :size="12" />结果产物</strong>
                <a v-for="item in message.deliverables" :key="item.key" :href="artifactUrl(message.runId, item.key)">{{ item.label }}</a>
              </div>
              <small v-if="message.skillPreference" class="skill-preference-note">技能偏好：{{ message.skillPreference }}</small>
              <span>{{ message.time }}<template v-if="userBoard && message.runId"> · 数据运行 {{ message.runId.slice(-8) }}</template></span>
            </div>
          </div>

        </div>

        <div class="prompt-templates" v-if="!userBoard || messages.length < 3">
          <button v-for="item in (responseState?.suggestions ?? promptTemplates)" :key="item" type="button" @click="setTemplate(item)">{{ item }}</button>
        </div>
        <div v-if="!userBoard && activeRun?.status === 'completed'" class="agent-delivery-bar">
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
          <textarea v-model="prompt" rows="2" @keydown="composerKeydown" aria-label="输入问题或工业建模指令" placeholder="例如：这批数据最大的问题是什么？为什么第3轮最好？"></textarea>
          <div class="composer-footer">
            <div v-if="!userBoard"><span class="composer-tag">当前任务</span><span>{{ contextRunId }}</span></div>
            <button v-if="userBoard" class="upload-chat-button" type="button" :disabled="isRunning || uploading" @click="chooseCsv" aria-label="上传 CSV 并分析"><AppIcon name="upload" :size="18" /> CSV</button>
            <label v-if="userBoard" class="skill-picker"><select v-model="preferredSkill" :disabled="isRunning || skillCatalogLoading" aria-label="技能偏好"><option value="">技能：自动选择</option><option v-for="skill in skillCatalog?.skills ?? []" :key="skill.id" :value="skill.id">优先：{{ skill.name }}</option></select></label>
            <div class="composer-model-controls" aria-label="回答模型设置">
              <label class="composer-model-pill">
                <select v-model="llmProvider" aria-label="回答模型" @change="handleLLMProviderChange">
                  <option v-for="provider in llmCatalog?.providers ?? []" :key="provider.id" :value="provider.id" :disabled="!provider.configured">{{ provider.label }}{{ provider.configured ? '' : '（未配置）' }}</option>
                </select>
              </label>
              <input v-if="llmProvider !== 'evidence'" v-model.trim="llmModel" class="composer-model-input" maxlength="120" aria-label="模型名称" autocomplete="off" :placeholder="activeLLMProvider?.model || '模型名称'" />
              <input v-if="llmProvider === 'local'" v-model.trim="localLLMBaseUrl" class="composer-model-input endpoint" inputmode="url" aria-label="本地模型接口" autocomplete="off" placeholder="http://127.0.0.1:11434/v1" />
            </div>
            <button class="send-button" type="button" :disabled="isRunning || !prompt.trim()" @click="runWorkflow">
              <AppIcon :name="isRunning ? 'loop' : 'arrow'" :class="{ spinning: isRunning }" />
              {{ isRunning ? (liveProgress == null ? '处理中' : `处理中 ${liveProgress}%`) : '发送' }}
            </button>
          </div>
          <small v-if="userBoard" class="composer-hint">{{ preferredSkill ? '技能偏好随问题发送，Agent 仍会检查任务目标与数据条件。' : 'Enter 发送 · Shift + Enter 换行 · 上传会启动数据分析' }}</small>
          <div v-if="isRunning && liveProgress != null" class="composer-progress"><span :style="{ width: `${liveProgress}%` }"></span></div>
        </div>
      </section>

      <aside v-if="!userBoard" class="agent-side-stack agent-live-stack">
        <section class="panel current-run-panel">
          <div class="section-heading compact">
            <div><span class="section-kicker">Current Run</span><h2>当前运行</h2></div>
            <StatusPill :tone="isRunning ? 'brand' : activeRun?.status === 'completed' ? 'success' : 'neutral'" dot>{{ activeRunStatusText }}</StatusPill>
          </div>
          <div class="current-run-id"><span>任务编号</span><code>{{ contextRunId }}</code></div>
          <div v-if="isRunning && liveProgress != null" class="current-run-progress"><span :style="{ width: `${liveProgress}%` }"></span></div>
          <div class="module-switches" aria-label="右侧模块显示选项">
            <span class="module-switches-label">模块</span>
            <div class="module-switch-group">
              <button
                v-for="item in rightModuleOptions"
                :key="item.id"
                type="button"
                :class="['module-switch-btn', { 'is-active': selectedRightModuleSet.has(item.id) }]"
                @click="toggleRightModule(item.id)"
              >{{ item.label }}</button>
            </div>
          </div>
        </section>

        <div class="agent-live-modules">
          <section v-if="selectedRightModuleSet.has('pipeline')" class="panel plan-panel">
            <div class="section-heading compact">
              <div><span class="section-kicker">动态编排计划</span><h2>Agent 算法流水线</h2></div>
              <div class="plan-summary"><span>{{ planNodes.length }} 阶段</span><span>{{ responseState?.blocked ? '门禁阻断' : responseState?.executed ? '真实执行' : '证据分析' }}</span></div>
            </div>
            <div class="plan-flow">
              <div v-if="!planNodes.length" class="plan-empty-state">
                <span><AppIcon name="network" /></span>
                <div><strong>暂无编排阶段</strong><small>上传 CSV 或发送分析指令后，这里会显示 Agent 规划出的算法步骤。</small></div>
              </div>
              <article
                v-for="(node, index) in planNodes"
                :key="node.name"
                class="plan-node"
                :class="{ 'is-complete': ['completed', 'success'].includes(node.status), 'is-partial': node.status === 'partial', 'is-blocked': node.status === 'blocked', 'is-failed': node.status === 'failed', 'is-current': node.status === 'executing', 'is-waiting': ['pending', 'skipped', 'queued', 'waiting', 'deferred'].includes(node.status) }"
              >
                <span class="plan-node-icon"><AppIcon :name="node.icon" :size="14" /></span>
                <span class="plan-node-num">{{ stepNumber(index) }}</span>
                <span class="plan-node-name" :title="node.name">{{ node.name }}</span>
                <span class="plan-node-state" :title="executionStatus(node.status).label"><AppIcon :name="node.status === 'executing' ? 'loop' : executionStatus(node.status).icon" :size="9" :class="{ spinning: node.status === 'executing' }" /></span>
              </article>
            </div>
          </section>

          <section v-if="selectedRightModuleSet.has('console')" class="panel console-panel">
            <div class="console-header"><div><i class="console-dot red"></i><i class="console-dot amber"></i><i class="console-dot green"></i></div><strong>AGENT TRACE · {{ contextRunId }}</strong><button type="button" @click="logsNewestFirst = !logsNewestFirst">{{ logsNewestFirst ? '最新优先' : '时间顺序' }}</button></div>
            <div class="console-body" role="log" aria-label="Agent 执行日志">
              <p v-if="!liveLogs.length"><time>--:--:--</time><span class="level-info">INFO</span><code>发送指令或上传 CSV 后显示真实意图解析与工具访问日志</code></p>
              <p v-for="(log, index) in displayedLogs" :key="`${log.time}-${index}`"><time>{{ log.time.slice(11, 19) }}</time><span :class="`level-${log.level.toLowerCase()}`">{{ log.level }}</span><code>{{ log.text }}</code></p>
            </div>
          </section>
        </div>

      </aside>
    </div>

    <aside v-if="userBoard && detailsOpen" class="conversation-details" aria-label="过程与结果">
      <header><h2>过程与结果</h2><button type="button" @click="detailsOpen = false" aria-label="关闭过程与结果">✕</button></header>
      <label class="detail-run-picker">关联数据<select :value="activeRun?.run_id || ''" :disabled="conversationBusy" aria-label="选择对话数据" @change="switchRun"><option value="" disabled>选择已有数据，或上传 CSV</option><option v-for="run in recentRuns" :key="run.run_id" :value="run.run_id">{{ run.original_name }} · {{ run.run_id.slice(-8) }}</option></select></label>
      <p>{{ activeRun?.original_name || '尚未关联数据' }}</p>
      <p v-if="activeRun">{{ sceneState.data_scene.display_name }} · {{ activeRunStatusText }}</p>
      <section><h3>执行步骤</h3><p v-if="!planNodes.length">发送问题后，这里显示实际计划和执行状态。</p><ol><li v-for="node in planNodes" :key="node.key"><strong>{{ node.name }} · {{ executionStatus(node.activityStatus ?? node.status).label }}</strong><p>{{ node.output }}</p></li></ol></section>
      <ChatOptimizationSummary v-if="activeRun?.results?.optimization?.iterations?.length" :report="activeRun.results.optimization" />
      <RuntimeObservabilityPanel v-if="hasRuntimeObservation" :runtime="runtimeObservation" />
      <details><summary>查看技能说明与本轮调用</summary><AgentSkillCenter :catalog="skillCatalog" :executions="responseState?.skill_executions ?? []" :loading="skillCatalogLoading" :error="skillCatalogError" /></details>
      <section><h3>结果文件</h3><p v-if="!Object.keys(activeRun?.artifacts || {}).length">生成的图表、数据和报告会出现在这里。</p><a v-for="(value, key) in activeRun?.artifacts ?? {}" :key="key" :href="artifactUrl(activeRun.run_id, key)">{{ artifactNames[key] || key }}</a></section>
      <button type="button" @click="exportConversation">导出当前对话</button>
      <button v-if="activeRun" type="button" @click="openDataView('/closed-loop-optimization/')">打开完整寻优记录 ↗</button>
      <button v-if="activeRun" type="button" @click="openDataView('/digital-twin/')">打开三维场景 ↗</button>
    </aside>
    <section v-if="!userBoard" class="agent-evidence-stack">
      <AgentTracePanel
        :run-id="contextRunId === '尚无任务' ? '' : contextRunId"
        :running="isRunning"
        :scenario-id="project.scenarioId"
        :fallback-scenario-id="sceneState.data_scene.id || props.project.scenarioId"
      />

      <AgentSkillCenter
        :catalog="skillCatalog"
        :executions="responseState?.skill_executions ?? []"
        :loading="skillCatalogLoading"
        :error="skillCatalogError"
      />
      <div class="agent-support-grid" :class="{ 'no-observability': !hasRuntimeObservation }">
        <RuntimeObservabilityPanel v-if="hasRuntimeObservation" :runtime="runtimeObservation" />
        <aside class="agent-verification-rail">
          <IntegratedEvidencePanel module="agent" />
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
    </section>
  </div>
</template>

<style scoped>
/* ── 用户模式顶部切换栏 ── */
.user-mode-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 30;
  /* break out of parent max-width to span full viewport */
  width: 100vw;
  margin-left: calc(-50vw + 50%);
  padding: 10px clamp(18px, 3vw, 32px);
  border-bottom: 1px solid rgba(207, 218, 232, 0.86);
  background: rgba(248, 250, 253, 0.92);
  -webkit-backdrop-filter: blur(16px);
  backdrop-filter: blur(16px);
}
.user-mode-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.user-mode-brand .brand-symbol.small { width: 22px; height: 22px; }
.user-mode-brand .brand-symbol.small i,
.user-mode-brand .brand-symbol.small b,
.user-mode-brand .brand-symbol.small em { border-radius: 3px; }
.user-mode-brand strong { color: #10233e; font-size: 13px; letter-spacing: -.02em; }

.user-mode-bar-spacer { flex: 1; }

.user-mode-staff-btn {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: 1px solid #c7d6ed;
  border-radius: 999px;
  color: #1e3a5f;
  background: linear-gradient(135deg, #f0f6ff, #e6eeff);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  transition: all 180ms ease;
  box-shadow: 0 1px 4px rgba(37, 99, 235, 0.10);
}
.user-mode-staff-btn:hover {
  color: #1a3578;
  border-color: #93b4e0;
  background: linear-gradient(135deg, #e6eeff, #d6e4ff);
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.18);
}

.chat-header-actions { display: flex; align-items: center; gap: 6px; }
.agent-view .agent-layout { grid-template-columns: minmax(660px, 1.45fr) minmax(360px, .55fr); align-items: start; }
.agent-view .chat-panel { grid-template-rows: auto minmax(0, 1fr) auto auto auto; height: clamp(560px, calc(100vh - 280px), 700px); min-height: 0; }
.agent-view.is-user-board { max-width: 980px; min-height: calc(100vh - 56px); margin: 0 auto; align-content: start; }
.agent-view.is-user-board .agent-layout { grid-template-columns: minmax(0, 1fr); }
.agent-view.is-user-board .chat-panel { height: calc(100vh - 148px); min-height: 520px; }
.agent-view .chat-thread { min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.agent-view .message { min-width: 0; max-width: min(92%, 760px); }
.agent-view .message-runtime { max-width: min(96%, 760px); }
.agent-view .message-bubble { min-width: 0; max-width: 100%; }
.agent-view .message-bubble p,
.agent-view .message-bubble strong,
.agent-view .message-bubble code,
.agent-view .message-bubble span { overflow-wrap: anywhere; }
.agent-live-stack { display: grid; grid-template-rows: auto minmax(0, 1fr); height: calc(100vh - 150px); min-height: 0; overflow: hidden; padding-right: 2px; }
.agent-live-modules { --live-module-height: 255px; display: grid; grid-auto-rows: var(--live-module-height); align-content: start; gap: 14px; min-height: 0; overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain; padding-right: 2px; scrollbar-width: thin; }
.current-run-panel { display: grid; gap: 8px; }
.current-run-id { display: grid; gap: 5px; min-width: 0; padding: 9px 10px; border: 1px solid #dce6f3; border-radius: 9px; background: #f8fbff; }
.current-run-id span { color: #64748b; font-size: 8px; }
.current-run-id code { overflow: hidden; color: #2454b8; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.current-run-progress { height: 4px; overflow: hidden; border-radius: 999px; background: #e7edf5; }
.current-run-progress span { display: block; height: 100%; background: linear-gradient(90deg, #2563eb, #22c4f0); transition: width 240ms ease; }
.module-switches { display: flex; align-items: center; gap: 5px; min-width: 0; padding-top: 2px; overflow-x: auto; scrollbar-width: none; flex-wrap: nowrap; }
.module-switches::-webkit-scrollbar { display: none; }
.module-switches-label { flex: 0 0 auto; color: #7a8797; font-size: 7px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.module-switch-group { display: flex; gap: 4px; flex-wrap: nowrap; }
.module-switch-btn {
  flex: 0 0 auto;
  padding: 3px 8px;
  border: 1px solid #dbe3ef;
  border-radius: 999px;
  color: #64748b;
  background: #fff;
  font-size: 7px;
  font-weight: 720;
  cursor: pointer;
  transition: all 150ms ease;
  white-space: nowrap;
  min-height: 21px;
  align-items: center;
  display: inline-flex;
  gap: 3px;
}
.module-switch-btn:hover { border-color: #a8bfdb; background: #f8fbff; }
.module-switch-btn.is-active {
  color: #2454b8;
  border-color: #c8d8fb;
  background: #f0f5ff;
}
.agent-live-stack .plan-panel { height: var(--live-module-height); min-height: 0; display: flex; flex-direction: column; padding: 14px; overflow: hidden; }
.agent-live-stack .plan-flow { display: flex !important; flex-direction: column; flex: 1; gap: 2px; min-height: 0; padding-right: 2px; overflow-y: auto; overflow-x: hidden; scrollbar-width: thin; }
.agent-live-stack .plan-node {
  display: flex !important;
  align-items: center;
  gap: 8px;
  min-height: 0 !important;
  min-width: 0;
  padding: 7px 10px 7px 6px;
  border-radius: 8px;
  transition: background 120ms ease;
}
.agent-live-stack .plan-node:hover { background: #f1f5f9; }
.agent-live-stack .plan-node::after { display: none !important; }
.agent-live-stack .plan-node-icon {
  flex: 0 0 16px;
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  color: #64748b;
  overflow: hidden;
}
.agent-live-stack .plan-node-num {
  flex: 0 0 auto;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  font-family: "SFMono-Regular", Consolas, monospace;
}
.agent-live-stack .plan-node-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-live-stack .plan-node-state {
  position: static !important;
  flex: 0 0 14px;
  display: grid;
  place-items: center;
  width: 14px;
  height: 14px;
  color: #fff;
  border-radius: 50%;
  background: #10b981;
}
.agent-live-stack .plan-node.is-current .plan-node-state { background: #3b82f6; }
.agent-live-stack .plan-node.is-waiting { opacity: .45; }
.agent-live-stack .plan-node.is-waiting .plan-node-state { background: #cbd5e1; }
.agent-live-stack .plan-node.is-failed .plan-node-state { background: #ef4444; }
.agent-live-stack .plan-node code,
.agent-live-stack .plan-node small { white-space: normal; }
.agent-live-stack .console-panel { height: var(--live-module-height); min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.agent-live-stack .console-body { flex: 1; min-height: 0; max-height: none; overflow: auto; }
.agent-live-stack .console-body p { grid-template-columns: 56px 38px minmax(260px, 1fr); }
.agent-evidence-stack { display: grid; gap: 18px; }
.agent-evidence-stack :deep(.agent-trace-panel) { padding: 20px; }
.agent-evidence-stack :deep(.trace-timeline) { max-height: 320px; overflow-y: auto; scrollbar-width: thin; }
.agent-evidence-stack :deep(.trace-node > button) { grid-template-columns: 34px minmax(200px, 1fr) minmax(170px, 1fr) 70px 20px; gap: 12px; min-height: 52px; }
.agent-evidence-stack :deep(.trace-toolchain) { flex-wrap: wrap; overflow-x: auto; }
.agent-evidence-stack :deep(.trace-toolchain > div) { min-width: 0; flex: 0 0 auto; }
.agent-evidence-stack :deep(.trace-toolchain > div strong) { white-space: nowrap; }
.agent-evidence-stack :deep(.toolchain-node) { white-space: nowrap; }
.agent-support-grid { display: grid; grid-template-columns: 1fr; gap: 14px; align-items: start; }
.agent-support-grid > * { min-width: 0; }
.agent-verification-rail { display: grid; grid-template-columns: 1fr; gap: 14px; align-content: start; min-width: 0; }
.agent-verification-rail :deep(.integrated-evidence-panel) { padding: 16px; }
.agent-verification-rail :deep(.integrated-evidence-panel .section-heading) { gap: 10px; }
.agent-verification-rail :deep(.evidence-source) { align-items: flex-start; margin: -2px 0 12px; font-size: 9px; line-height: 1.5; }
.agent-verification-rail :deep(.evidence-kpis) { grid-template-columns: minmax(0, 1fr); gap: 7px; margin-bottom: 10px; }
.agent-verification-rail :deep(.evidence-kpis > div) { padding: 9px 10px; }
.agent-verification-rail :deep(.evidence-kpis span) { margin-bottom: 2px; font-size: 8px; }
.agent-verification-rail :deep(.evidence-kpis strong) { font-size: 14px; }
.agent-verification-rail :deep(.evidence-table-wrap) { max-height: 150px; }
.agent-verification-rail .intent-list { gap: 0; }
.agent-verification-rail .intent-list > div { padding: 8px 0; }
.agent-verification-rail .runtime-grid { grid-template-columns: minmax(0, 1fr); gap: 8px; }
.run-switcher { display:flex;align-items:center;gap:6px;padding:5px 7px;border:1px solid #dbe3ef;border-radius:8px;background:#fff }.run-switcher span { color:#64748b;font-size:8px }.run-switcher select { max-width:185px;border:0;outline:0;color:#334155;background:transparent;font-size:8px }
.agent-delivery-bar { display: flex; align-items: center; flex-wrap: wrap; gap: 7px; padding: 9px 17px; border-top: 1px solid #e2e8f0; background: #f8fafc; }
.agent-delivery-bar span { display: inline-flex; align-items: center; gap: 5px; margin-right: auto; color: #166534; font-size: 9px; }
.agent-delivery-bar a { padding: 5px 8px; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; background: #fff; text-decoration: none; font-size: 8px; }
.agent-delivery-bar .report-link { display: inline-flex; align-items: center; gap: 4px; border-color: #93c5fd; color: #1d4ed8; background: #eff6ff; }
.message-error { border-color: #fecaca; background: #fff7f7; }
.message-model { display: inline-flex!important; align-items: center; gap: 3px; margin-top: 7px!important; padding: 3px 6px; border: 1px solid #dbeafe; border-radius: 999px; color: #1d4ed8!important; background: #eff6ff; font-size: 7px!important; }
.streaming-phase { display:inline-flex!important;align-items:center;gap:4px;margin-bottom:7px!important;color:#2563eb!important;font-size:8px!important;font-weight:650 }.streaming-cursor{display:inline-block;width:5px;height:12px;margin-left:3px;vertical-align:-1px;background:#2563eb;animation:stream-blink .8s steps(1) infinite}@keyframes stream-blink{50%{opacity:0}}
.composer-model-controls { display: inline-flex; gap: 7px; align-items: center; margin-left: auto; min-width: 0; }
.composer-model-pill { position: relative; display: inline-flex; align-items: center; min-width: 122px; max-width: 190px; height: 34px; border: 1px solid #c8d8fb; border-radius: 999px; background: #f0f5ff; }
.composer-model-pill::after { content: ""; position: absolute; right: 13px; top: 50%; width: 8px; height: 8px; border-right: 2px solid #5f78a8; border-bottom: 2px solid #5f78a8; pointer-events: none; transform: translateY(-65%) rotate(45deg); }
.composer-model-pill select { width: 100%; height: 100%; min-width: 0; padding: 0 30px 0 14px; overflow: hidden; color: #2454b8; font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; border: 0; outline: 0; border-radius: inherit; background: transparent; appearance: none; }
.composer-model-pill select:focus-visible { box-shadow: 0 0 0 3px rgba(37, 99, 235, .14); }
.composer-model-input { width: min(170px, 20vw); height: 32px; min-width: 0; padding: 0 10px; color: #243b5a; font-size: 9px; border: 1px solid #cbd8e8; border-radius: 999px; outline: 0; background: #fff; }
.composer-model-input.endpoint { width: min(230px, 24vw); }
.composer-model-input:focus { border-color: #6e9ff0; box-shadow: 0 0 0 2px rgba(37, 99, 235, .08); }
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
@media (max-width: 1280px) { .agent-view .agent-layout { grid-template-columns: minmax(0, 1fr); } .agent-live-stack { max-height: none; overflow: visible; padding-right: 0; } .agent-live-modules { overflow: visible; padding-right: 0; } .agent-view .chat-panel { height: 620px; } }
@media (max-width: 1100px) { .agent-support-grid { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .agent-verification-rail { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .agent-delivery-bar span { width: 100%; margin-right: 0; } .agent-view .composer-footer { flex-wrap: wrap; } .composer-model-controls { order: 2; width: calc(100% - 52px); margin-left: 0; overflow-x: auto; } .composer-model-pill { min-width: 140px; } .composer-model-input { width: 150px; flex: 0 0 150px; } .composer-model-input.endpoint { width: 210px; flex-basis: 210px; } .agent-view .send-button { order: 3; width: 42px; min-width: 42px; padding: 0; } .agent-view .send-button svg + text { display: none; } }

/* ══════════════════════════════════════════════════════
   用户板块视觉美化 — 纯视觉，不改布局与交互
   ══════════════════════════════════════════════════════ */

/* ── 聊天面板容器 ── */
.is-user-board .chat-panel {
  border: 1px solid #dce6f3;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(15, 23, 42, .05), 0 1px 3px rgba(15, 23, 42, .03);
}

/* ── 聊天头部 ── */
.is-user-board .chat-header {
  padding: 16px 20px;
  background: linear-gradient(180deg, #f8faff, #ffffff);
  border-bottom: 1px solid #e8eef6;
}

.is-user-board .agent-avatar {
  box-shadow: 0 3px 10px rgba(37, 99, 235, .18);
}

.is-user-board .chat-header strong {
  font-size: 12px;
  letter-spacing: -.01em;
  color: #1e293b;
}

.is-user-board .chat-header span {
  color: #64748b;
  font-size: 9px;
  margin-top: 2px;
}

/* ── 聊天线程背景 ── */
.is-user-board .chat-thread {
  background: linear-gradient(180deg, #f6f8fc 0%, #ffffff 40%);
}

/* ── 消息卡片 ── */
.is-user-board .message-agent .message-bubble {
  border: 1px solid #e2e9f4;
  border-radius: 4px 16px 16px 16px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, .04), 0 1px 2px rgba(15, 23, 42, .02);
  padding: 14px 16px;
  transition: box-shadow 180ms ease;
}

.is-user-board .message-agent .message-bubble:hover {
  box-shadow: 0 4px 14px rgba(15, 23, 42, .07), 0 1px 3px rgba(15, 23, 42, .03);
}

.is-user-board .message-user .message-bubble {
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 3px 12px rgba(37, 99, 235, .18);
}

.is-user-board .message-bubble p {
  font-size: 11px;
  line-height: 1.72;
  color: #334155;
}

.is-user-board .message-user .message-bubble p {
  color: #ffffff;
}

/* ── 时间戳 ── */
.is-user-board .message-bubble > span:not(.streaming-phase):not(.message-model) {
  color: #94a3b8;
  font-size: 8px;
  margin-top: 8px;
}

/* ── 流式状态 ── */
.is-user-board .streaming-phase {
  margin-bottom: 6px !important;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb !important;
  font-size: 9px !important;
  width: fit-content;
}

/* ── 模型标签 ── */
.is-user-board .message-model {
  margin-top: 8px !important;
  padding: 3px 8px;
  font-size: 8px !important;
  border-color: #dbeafe;
  background: #f0f7ff;
  box-shadow: 0 1px 3px rgba(37, 99, 235, .06);
}

/* ── 实时执行时间线 ── */
.is-user-board :deep(.execution-timeline) {
  width: 100%;
  max-width: 100%;
  padding: 12px 16px;
  border: 1px solid #dce6f3;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fbff, #f0f6ff);
  box-shadow: 0 1px 4px rgba(15, 23, 42, .03);
}

.is-user-board :deep(.execution-timeline header) {
  color: #1e40af;
  font-size: 10px;
  font-weight: 650;
}

.is-user-board :deep(.execution-timeline header button) {
  padding: 4px 10px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #ffffff;
  color: #2563eb;
  font-size: 8px;
  font-weight: 600;
  transition: all 150ms ease;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}

.is-user-board :deep(.execution-timeline header button:hover) {
  border-color: #93c5fd;
  background: #eff6ff;
  box-shadow: 0 2px 6px rgba(37, 99, 235, .10);
}

.is-user-board :deep(.execution-timeline li) {
  padding: 5px 6px;
  border-radius: 6px;
  transition: background 120ms ease;
}

.is-user-board :deep(.execution-timeline li:hover) {
  background: rgba(219, 234, 254, .35);
}

.is-user-board :deep(.execution-timeline li strong) {
  color: #1e293b;
  font-size: 9px;
}

.is-user-board :deep(.execution-timeline li p) {
  color: #475569;
  font-size: 9px;
  line-height: 1.5;
}

/* ── 提示词建议条 ── */
.is-user-board .prompt-templates {
  padding: 4px 18px 10px;
  gap: 7px;
}

.is-user-board .prompt-templates button {
  padding: 6px 12px;
  border: 1px solid #d4e2f7;
  border-radius: 999px;
  background: #ffffff;
  color: #475569;
  font-size: 9px;
  font-weight: 500;
  transition: all 180ms ease;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
}

.is-user-board .prompt-templates button:hover {
  color: #2563eb;
  border-color: #93c5fd;
  background: #f0f7ff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, .10);
  transform: translateY(-1px);
}

/* ── 任务完成交付栏 ── */
.is-user-board .agent-delivery-bar {
  padding: 10px 18px;
  border-top: 1px solid #e8eef6;
  background: linear-gradient(180deg, #f8fbff, #ffffff);
  border-radius: 0 0 16px 16px;
  margin: 0;
}

.is-user-board .agent-delivery-bar span {
  font-size: 10px;
  font-weight: 600;
  color: #15803d;
}

.is-user-board .agent-delivery-bar a {
  padding: 5px 10px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  color: #1e40af;
  background: #ffffff;
  font-size: 9px;
  font-weight: 500;
  transition: all 150ms ease;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
  text-decoration: none;
}

.is-user-board .agent-delivery-bar a:hover {
  border-color: #60a5fa;
  background: #eff6ff;
  box-shadow: 0 2px 6px rgba(37, 99, 235, .10);
  transform: translateY(-1px);
}

.is-user-board .agent-delivery-bar .report-link {
  border-color: #93c5fd;
  color: #1d4ed8;
  background: #f0f7ff;
  box-shadow: 0 1px 3px rgba(37, 99, 235, .06);
}

.is-user-board .agent-delivery-bar .report-link:hover {
  background: #dbeafe;
  box-shadow: 0 3px 10px rgba(37, 99, 235, .14);
}

/* ── 输入区域 ── */
.is-user-board .prompt-composer {
  margin: 0 16px 16px;
  border: 1.5px solid #d4dff0;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 2px 12px rgba(15, 23, 42, .04);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.is-user-board .prompt-composer:focus-within {
  border-color: #60a5fa;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .10), 0 2px 12px rgba(15, 23, 42, .04);
}

.is-user-board .prompt-composer textarea {
  padding: 14px 16px 6px;
  font-size: 12px;
  line-height: 1.65;
  color: #334155;
}

.is-user-board .prompt-composer textarea::placeholder {
  color: #94a3b8;
  font-size: 12px;
}

.is-user-board .composer-footer {
  padding: 10px 12px 11px 16px;
  border-top: 1px solid #f0f3f8;
}

.is-user-board .composer-tag {
  padding: 3px 7px;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 8px;
  font-weight: 600;
}

/* ── 模型选择器 ── */
.is-user-board .composer-model-pill {
  border: 1.5px solid #d4dff0;
  background: #f8fbff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.is-user-board .composer-model-pill:hover {
  border-color: #93c5fd;
  box-shadow: 0 2px 6px rgba(37, 99, 235, .08);
}

.is-user-board .composer-model-pill select:focus-visible {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .12);
}

/* ── 发送按钮 ── */
.is-user-board .send-button {
  border-radius: 10px;
  padding: 0 16px;
  min-height: 36px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .01em;
  background: linear-gradient(145deg, #2563eb, #1d4ed8);
  box-shadow: 0 2px 8px rgba(37, 99, 235, .22);
  transition: all 180ms ease;
}

.is-user-board .send-button:hover:not(:disabled) {
  background: linear-gradient(145deg, #1d4ed8, #1e40af);
  box-shadow: 0 4px 14px rgba(37, 99, 235, .30);
  transform: translateY(-1px);
}

.is-user-board .send-button:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(37, 99, 235, .18);
}

.is-user-board .send-button:disabled {
  opacity: .5;
  box-shadow: none;
  transform: none;
}

/* ── 用户模式顶部栏 ── */
.is-user-board .user-mode-bar {
  background: rgba(255, 255, 255, .88);
  border-bottom-color: rgba(212, 223, 240, .8);
  box-shadow: 0 1px 6px rgba(15, 23, 42, .03);
}

.is-user-board .user-mode-staff-btn {
  border: 1.5px solid #bfdbfe;
  background: linear-gradient(135deg, #f0f7ff, #e0ecff);
  box-shadow: 0 1px 4px rgba(37, 99, 235, .08);
}

.is-user-board .user-mode-staff-btn:hover {
  border-color: #60a5fa;
  background: linear-gradient(135deg, #e0ecff, #d0e0ff);
  box-shadow: 0 3px 10px rgba(37, 99, 235, .16);
  transform: translateY(-1px);
}

/* ── 快捷操作栏中的按钮（用户上传、导出） ── */
.is-user-board .chat-header-actions .icon-button {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid #d4e2f7;
  border-radius: 9px;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  transition: all 150ms ease;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
}

.is-user-board .chat-header-actions .icon-button:hover {
  border-color: #93c5fd;
  color: #2563eb;
  background: #f0f7ff;
  box-shadow: 0 2px 6px rgba(37, 99, 235, .10);
}

.is-user-board .chat-header-actions .icon-button:disabled {
  opacity: .45;
  cursor: not-allowed;
  box-shadow: none;
}

/* Chat-first user workspace; staff layout remains independent. */
.agent-view.is-user-board { --chat-ink:#202123; --chat-muted:#66706b; position:fixed; inset:0; z-index:25; margin:0; max-width:none; min-height:0; display:grid; grid-template-columns:248px minmax(0,1fr); grid-template-rows:60px minmax(0,1fr); gap:0; background:#fff; color:var(--chat-ink); }
.is-user-board button,.is-user-board select,.is-user-board textarea { font:inherit; }
.conversation-sidebar { grid-row:1 / -1; display:flex; flex-direction:column; gap:20px; padding:24px 16px; background:#f5f6f5; border-right:1px solid #e7e9e7; min-height:0; }
.sidebar-brand { font-size:19px; letter-spacing:-.5px; }.sidebar-brand span { display:block; margin-top:6px; font-size:12px; font-weight:400; color:#68716d; letter-spacing:0; }
.conversation-sidebar button { text-align:left; padding:12px; border:0; border-radius:8px; background:transparent; cursor:pointer; color:#303733; font-size:14px; }.conversation-sidebar .new-conversation { border:1px solid #d8ded9; background:white; }.conversation-sidebar nav { flex:1; overflow:auto; }.conversation-sidebar nav button { width:100%; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; margin-bottom:4px; }.conversation-sidebar nav button:hover,.conversation-sidebar nav button.active { background:#e5eae6; }.history-label,.conversation-sidebar nav p { font-size:12px; color:#68716d; }.conversation-sidebar .staff-link { border-top:1px solid #dde2de; border-radius:0; }.is-user-board button:disabled { opacity:.5; cursor:not-allowed; }
.is-user-board .user-mode-bar { position:static; width:auto; margin:0; padding:12px 28px; background:white; border-bottom:0; backdrop-filter:none; }.is-user-board .user-mode-brand strong { font-size:18px; }.is-user-board .user-mode-staff-btn { background:white; box-shadow:none; color:#33433a; border:1px solid #dce2dd; font-size:13px; }.history-toggle { display:none; }
.agent-view.is-user-board .agent-layout { min-height:0; display:block; padding:0 24px; }.agent-view.is-user-board .chat-panel { display:flex; flex-direction:column; width:100%; max-width:880px; height:100%; min-height:0; margin:auto; border:0; box-shadow:none; border-radius:0; background:white; padding:0; }
.conversation-context { display:flex; flex-wrap:wrap; justify-content:space-between; gap:6px; font-size:12px; color:#68716d; padding:12px 8px; border-bottom:1px solid #edf0ed; }
.agent-view.is-user-board .chat-thread { flex:1; padding:28px 12px; display:flex; flex-direction:column; gap:28px; }.agent-view.is-user-board .message { width:100%; max-width:100%; }.is-user-board .message-avatar { background:#edf3ef; color:#35634d; box-shadow:none; flex-shrink:0; }.is-user-board .message-agent .message-bubble { border:0; box-shadow:none; background:white; padding:0 12px; }.is-user-board .message-user { align-self:flex-end; width:auto; max-width:85%; }.is-user-board .message-user .message-bubble { color:#202123; background:#f0f2f0; border:0; box-shadow:none; border-radius:20px; padding:14px 20px; }.is-user-board .message-bubble p { font-size:16px; line-height:1.85; white-space:pre-wrap; }.is-user-board .message-bubble>span { font-size:12px; color:#6a746e; }.is-user-board .message-skill-chain>div strong,.is-user-board .message-skill-chain>span,.is-user-board .intent-chips span { font-size:12px; }.is-user-board .message-skill-chain code { display:none; }.skill-preference-note { display:block; font-size:12px; color:#607565; margin-top:8px; }
.is-user-board .prompt-composer { margin:12px 0 18px; padding:14px 18px; border:1px solid #dce3dd; border-radius:24px; background:#f8faf8; box-shadow:0 5px 22px #243b2910; }.is-user-board .prompt-composer textarea { font-size:16px; line-height:1.6; min-height:55px; background:transparent; }.is-user-board .composer-footer { display:flex; flex-wrap:wrap; gap:8px; }.skill-picker { min-width:0; max-width:220px; }.skill-picker select { width:100%; border:0; background:transparent; padding:8px 4px; color:#415a4a; font-size:13px; }.upload-chat-button { display:flex; align-items:center; gap:4px; background:transparent; border:0; padding:8px 4px; font-size:13px!important; cursor:pointer; }.is-user-board .composer-model-controls { flex:1; }.is-user-board .composer-model-pill select { font-size:12px; }.is-user-board .send-button { background:#244c38; border-radius:14px; font-size:13px; padding:10px 14px; }.composer-hint { display:block; color:#6f7972; font-size:11px; margin-top:9px; }.is-user-board .prompt-templates { padding:12px 8px 0; flex-wrap:wrap; }.is-user-board .prompt-templates button { font-size:12px; background:white; }.is-user-board :deep(.execution-timeline) { width:100%; background:#f8faf8; border-color:#e0e7e1; padding:14px; }.is-user-board :deep(.execution-timeline header),.is-user-board :deep(.execution-timeline li div strong),.is-user-board :deep(.execution-timeline li p),.is-user-board :deep(.execution-timeline header button) { font-size:12px; }.is-user-board :deep(.execution-timeline time),.is-user-board :deep(.execution-timeline footer) { font-size:11px; }
.conversation-details { position:absolute; right:0; top:60px; bottom:0; width:min(560px, calc(100vw - 24px)); overflow:auto; z-index:40; background:white; border-left:1px solid #dde4de; box-shadow:-16px 0 40px #1d342512; padding:24px; font-size:14px; }.conversation-details header { display:flex; justify-content:space-between; align-items:center; }.conversation-details h2 { font-size:20px; }.conversation-details h3 { font-size:15px; }.conversation-details section,.conversation-details details { margin:24px 0; }.conversation-details p { color:#637067; line-height:1.7; overflow-wrap:anywhere; }.conversation-details li { margin:14px 0; }.conversation-details a { display:block; padding:8px 0; overflow-wrap:anywhere; }.conversation-details button { background:#f1f5f2; border:1px solid #dde5de; border-radius:8px; padding:10px; cursor:pointer; margin:4px; }.conversation-details :deep(.skill-grid) { grid-template-columns:1fr; }.conversation-details :deep(.skill-heading) { flex-wrap:wrap; }.is-user-board :focus-visible { outline:2px solid #468663; outline-offset:3px; }
@media(max-width:760px) { .agent-view.is-user-board { grid-template-columns:minmax(0,1fr); grid-template-rows:56px minmax(0,1fr); }.conversation-sidebar { display:none; }.conversation-sidebar.is-open { display:flex; position:absolute; inset:56px auto 0 0; width:min(290px,85vw); z-index:45; box-shadow:12px 0 25px #1733211a; }.history-toggle { display:block; border:0; background:none; padding:8px; cursor:pointer; }.is-user-board .user-mode-bar { padding:8px 12px; gap:8px; }.agent-view.is-user-board .agent-layout { padding:0 12px; }.is-user-board .message-avatar { display:none; }.is-user-board .message-agent .message-bubble { padding:0; }.agent-view.is-user-board .chat-thread { padding:22px 4px; }.is-user-board .prompt-composer { padding:12px; margin-bottom:10px; }.is-user-board .composer-model-input { max-width:120px; }.skill-picker { max-width:180px; }.conversation-context { font-size:11px; }.is-user-board .user-mode-staff-btn { padding:8px; }.conversation-details { top:56px; }.is-user-board .message-bubble p { font-size:15px; } }

.is-user-board .send-button { flex-shrink:0; width:auto; min-width:76px; white-space:nowrap; }
.is-user-board .composer-model-controls { flex-wrap:wrap; width:auto; overflow:visible; }
.is-user-board .composer-model-input { flex:1 1 100px; max-width:160px; }
.is-user-board .composer-model-pill { min-width:135px; background:#f3f6f3; border-color:#d9e2da; }
.is-user-board .composer-model-pill select { color:#3c5545; }
@media(max-width:760px) { .is-user-board .composer-model-controls { flex-basis:calc(100% - 90px); }.is-user-board .send-button { padding:10px; } }

.is-user-board .chat-thread { background:#fff; }
.is-user-board .message-user .message-bubble p { color:#202123; }
.is-user-board .message-bubble > span:not(.message-model) { font-size:12px; }
.is-user-board .message-model { font-size:11px; }
.detail-run-picker { display:grid; gap:8px; margin-top:20px; }.detail-run-picker select { width:100%; padding:10px; border:1px solid #dce4dd; border-radius:8px; background:#fff; font-size:13px; }
.agent-view.is-user-board .message-user { width:auto; max-width:85%; margin-left:auto; }
</style>
