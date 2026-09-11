<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import IntegratedEvidencePanel from '../components/IntegratedEvidencePanel.vue'
import AgentTracePanel from '../components/AgentTracePanel.vue'
import AgentSkillCenter from '../components/AgentSkillCenter.vue'
import { getAgentSkills, sendAgentMessage } from '../api/agent'
import { announcePipelineUpdate, artifactUrl, getLatestPipelineRun, uploadPipelineFile } from '../api/pipeline'
import { getRunScenarioId } from '../composables/useLatestPipelineRun'

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
const runProgress = ref(0)
const currentNode = ref(0)
const latestRun = ref(null)
const chatThread = ref(null)
const fileInput = ref(null)
const uploading = ref(false)
const responseState = ref(savedChat?.responseState ?? null)
const skillCatalog = ref(null)
const skillCatalogLoading = ref(true)
const skillCatalogError = ref('')
const messages = ref(savedChat?.messages?.length ? savedChat.messages : [welcomeMessage])
const liveLogs = ref(savedChat?.liveLogs ?? [])
const logsNewestFirst = ref(true)
const displayedLogs = computed(() => logsNewestFirst.value ? liveLogs.value : [...liveLogs.value].reverse())
let runTimer

const promptTemplates = [
  '提取 1 号塔高信噪比的动态数据',
  '分析当前模型的 R²、RMSE 和残差是否可靠',
  '以稳健性优先重新执行闭环寻优',
]

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
      status: executionMap[step.skill_id]?.status === 'success' ? 'completed' : step.status,
      icon: skillCategoryIcon[step.category] ?? 'loop',
    }))
  }
  return (responseState.value?.plan ?? latestRun.value?.stages?.map((stage) => ({ key: stage.key, name: stage.label, tool: stage.key, output: stage.message, status: stage.status })) ?? []).map((node) => ({ ...node, icon: iconMap[node.key] ?? 'loop' }))
})
const intent = computed(() => responseState.value?.intent ?? { key: 'overview', confidence: 0, keywords: [] })
const contextRunId = computed(() => responseState.value?.run_id ?? latestRun.value?.run_id ?? '尚无任务')
const reportUrl = computed(() => latestRun.value?.artifacts?.analysis_report_md ? artifactUrl(latestRun.value.run_id, 'analysis_report_md') : '')

watch([messages, responseState, liveLogs, prompt], () => {
  try {
    const persistedResponse = responseState.value ? { ...responseState.value, snapshot: null } : null
    window.localStorage.setItem(chatStorageKey, JSON.stringify({
      prompt: prompt.value,
      messages: messages.value.slice(-60),
      responseState: persistedResponse,
      liveLogs: liveLogs.value.slice(0, 20),
    }))
  } catch { /* Conversation persistence is best effort. */ }
}, { deep: true })

function setTemplate(text) {
  prompt.value = text
}

function stepNumber(index) {
  return String(index + 1).padStart(2, '0')
}

function skillActivityText(skill) {
  if (skill.status === 'unavailable') return '未执行/缺证据'
  if (skill.status === 'blocked') return '阻断'
  return skill.activity === 'executed' ? '旧版执行记录，未核验' : skill.activity === 'read' ? '取证' : skill.activity === 'planned' ? '规划' : '调用'
}

async function scrollToLatest() {
  await nextTick()
  if (chatThread.value) chatThread.value.scrollTop = chatThread.value.scrollHeight
}

async function runWorkflow() {
  if (!prompt.value.trim() || isRunning.value) return
  const userText = prompt.value.trim()
  messages.value.push({ id: Date.now(), role: 'user', text: userText, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
  prompt.value = ''
  isRunning.value = true
  runProgress.value = 8
  currentNode.value = 0
  await scrollToLatest()
  emit('notify', { tone: 'info', title: 'Agent 正在回答', message: '正在理解问题并读取相关任务证据。' })
  clearInterval(runTimer)
  runTimer = window.setInterval(() => {
    runProgress.value = Math.min(88, runProgress.value + 8)
    currentNode.value = Math.min(planNodes.value.length - 1, Math.floor((runProgress.value / 100) * planNodes.value.length))
  }, 240)
  try {
    const result = await sendAgentMessage(userText, latestRun.value?.run_id, responseState.value?.intent?.key, responseState.value?.intent?.matched ?? [])
    responseState.value = result
    liveLogs.value = [...result.logs, ...liveLogs.value].slice(0, 12)
    messages.value.push({
      id: Date.now() + 1,
      role: 'agent',
      text: result.answer,
      cards: result.cards,
      skills: result.skill_executions?.map((item) => ({ id: item.skill_id, name: item.name, status: item.status, activity: item.activity })) ?? [],
      skillRunId: result.skill_run_id,
      skillSummary: result.skill_summary,
      deliverables: result.deliverables ?? [],
      runId: result.run_id,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    })
    if (result.snapshot) {
      latestRun.value = result.snapshot
      announcePipelineUpdate(result.snapshot)
    }
    runProgress.value = 100
    currentNode.value = Math.max(planNodes.value.length - 1, 0)
    emit('notify', { tone: result.blocked ? 'warning' : 'success', title: result.blocked ? 'Agent 已阻断不匹配任务' : result.executed ? 'Agent 已执行并刷新任务' : 'Agent 分析完成', message: `意图：${intentLabels[result.intent.key] ?? result.intent.key} · 规则匹配分 ${(result.intent.confidence * 100).toFixed(0)}%` })
  } catch (error) {
    messages.value.push({ id: Date.now() + 1, role: 'agent', text: `本次请求失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    emit('notify', { tone: 'warning', title: 'Agent 请求失败', message: error.message })
  } finally {
    clearInterval(runTimer)
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
  isRunning.value = true
  runProgress.value = 5
  const uploadMessage = { id: Date.now(), role: 'user', text: `上传并分析CSV：${file.name}`, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  messages.value.push(uploadMessage)
  await scrollToLatest()
  clearInterval(runTimer)
  runTimer = window.setInterval(() => { runProgress.value = Math.min(90, runProgress.value + 5) }, 300)
  try {
    const snapshot = await uploadPipelineFile(file, { scenarioId: 'auto', instruction: '请根据上传数据识别工业场景，由Agent总控从头执行并生成分析报告', resampleRule: props.project.resampleRule, maxLag: props.project.maxLag })
    // A successfully created CSV run starts a fresh evidence conversation.
    // Failed uploads keep the previous conversation so troubleshooting context is not lost.
    prompt.value = ''
    messages.value = [uploadMessage]
    responseState.value = null
    liveLogs.value = []
    latestRun.value = snapshot
    announcePipelineUpdate(snapshot)
    const result = await sendAgentMessage('总结刚刚上传的CSV，说明数据质量、模型效果、评审结论和报告产物', snapshot.run_id)
    responseState.value = result
    liveLogs.value = [
      ...result.logs,
      ...snapshot.stages.map((stage) => ({ time: stage.finished_at ?? snapshot.updated_at, level: stage.status === 'completed' ? 'TOOL' : 'WARN', text: `${stage.label}：${stage.message}` })),
    ].slice(0, 18)
    messages.value.push({
      id: Date.now() + 1,
      role: 'agent',
      text: `已接收 ${file.name}，并完成全部子Agent调度。${result.answer} 分析报告已生成，可在对话框下方下载。`,
      cards: result.cards,
      skills: result.skill_executions?.map((item) => ({ id: item.skill_id, name: item.name, status: item.status, activity: item.activity })) ?? [],
      skillRunId: result.skill_run_id,
      skillSummary: result.skill_summary,
      deliverables: result.deliverables ?? [],
      runId: result.run_id,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    })
    runProgress.value = 100
    emit('notify', { tone: 'success', title: 'CSV全流程分析完成', message: `任务 ${snapshot.run_id} 已生成分析报告和全部中间产物。` })
  } catch (error) {
    messages.value.push({ id: Date.now() + 1, role: 'agent', text: `CSV执行失败：${error.message}`, error: true, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) })
    emit('notify', { tone: 'warning', title: 'CSV分析失败', message: error.message })
  } finally {
    clearInterval(runTimer)
    uploading.value = false
    isRunning.value = false
    await scrollToLatest()
  }
}

onMounted(async () => {
  await Promise.allSettled([
    getLatestPipelineRun().then((result) => { latestRun.value = getRunScenarioId(result) === props.project.scenarioId ? result : null }),
    getAgentSkills().then((result) => { skillCatalog.value = result }).catch((error) => { skillCatalogError.value = error.message }).finally(() => { skillCatalogLoading.value = false }),
  ])
  scrollToLatest()
})
onBeforeUnmount(() => clearInterval(runTimer))
</script>

<template>
  <div class="view-stack agent-view">
    <PageHeader
      eyebrow="Natural Language Orchestration"
      title="Agent 智能中枢"
      description="用工业自然语言描述目标，Agent 自动拆解意图、组装算法流水线，并以辨识指标驱动预处理策略持续自演进。"
    >
      <template #actions>
        <input ref="fileInput" class="visually-hidden" type="file" accept=".csv,text/csv" @change="handleCsv" />
        <button class="btn btn-primary" type="button" :disabled="uploading" @click="chooseCsv"><AppIcon :name="uploading ? 'loop' : 'upload'" :class="{ spinning: uploading }" />{{ uploading ? `子Agent执行中 ${runProgress}%` : '上传CSV并全流程运行' }}</button>
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

    <div class="agent-layout">
      <section class="panel chat-panel">
        <div class="chat-header">
          <div class="agent-avatar"><AppIcon name="spark" /></div>
          <div><strong>ProcessPilot Agent</strong><span><i></i> 工业建模智能中枢</span></div>
          <button class="icon-button" type="button" aria-label="导出当前对话" title="导出当前对话" @click="exportConversation"><AppIcon name="download" /></button>
        </div>

        <div ref="chatThread" class="chat-thread">
          <div v-for="message in messages" :key="message.id" class="message" :class="message.role === 'agent' ? 'message-agent' : 'message-user'">
            <div v-if="message.role === 'agent'" class="message-avatar"><AppIcon name="spark" :size="17" /></div>
            <div class="message-bubble" :class="{ 'rich-message': message.cards?.length, 'message-error': message.error }">
              <p>{{ message.text }}</p>
              <div v-if="message.cards?.length" class="intent-chips"><span v-for="card in message.cards" :key="card.label">{{ card.label }}：{{ card.value ?? '—' }}</span></div>
              <div v-if="message.skills?.length" class="message-skill-chain">
                <div><AppIcon name="network" :size="13" /><strong v-if="message.skillSummary?.read != null">Skill 证据核验 · 取证 {{ message.skillSummary?.read ?? 0 }} · 规划 {{ message.skillSummary?.planned ?? 0 }} · 缺证据 {{ message.skillSummary?.unavailable ?? 0 }} · 阻断 {{ message.skillSummary?.blocked ?? 0 }}</strong><strong v-else>历史 Skill 记录（未经新版证据核验）</strong><code>{{ message.skillRunId }}</code></div>
                <span v-for="skill in message.skills" :key="skill.id" :title="skill.id" :class="{ blocked: skill.status === 'blocked' || skill.status === 'unavailable' }"><AppIcon :name="skill.status === 'blocked' || skill.status === 'unavailable' ? 'alert' : 'check'" :size="11" />{{ skillActivityText(skill) }} · {{ skill.name }}</span>
              </div>
              <div v-if="message.deliverables?.length" class="message-deliverables">
                <strong><AppIcon name="download" :size="12" />结果产物</strong>
                <a v-for="item in message.deliverables" :key="item.key" :href="artifactUrl(message.runId, item.key)">{{ item.label }}</a>
              </div>
              <span>{{ message.time }}</span>
            </div>
          </div>
          <div v-if="isRunning" class="message message-agent">
            <div class="message-avatar"><AppIcon name="spark" :size="17" /></div>
            <div class="message-bubble"><p>我正在结合这次任务的数据想一下…</p></div>
          </div>
        </div>

        <div class="prompt-templates">
          <button v-for="item in (responseState?.suggestions ?? promptTemplates)" :key="item" type="button" @click="setTemplate(item)">{{ item }}</button>
        </div>
        <div v-if="latestRun?.status === 'completed'" class="agent-delivery-bar">
          <span><AppIcon name="check" :size="15" />任务 {{ latestRun.run_id }} 已完成</span>
          <a :href="artifactUrl(latestRun.run_id, 'standardized_csv')">标准化CSV</a>
          <a :href="artifactUrl(latestRun.run_id, 'cleaned_csv')">清洗CSV</a>
          <a v-if="latestRun.artifacts?.segments_csv" :href="artifactUrl(latestRun.run_id, 'segments_csv')">动态段CSV</a>
          <a v-if="latestRun.artifacts?.modeling_csv" :href="artifactUrl(latestRun.run_id, 'modeling_csv')">建模数据CSV</a>
          <a :href="artifactUrl(latestRun.run_id, 'metrics_json')">模型指标</a>
          <a :href="artifactUrl(latestRun.run_id, 'optimization_json')">寻优记录</a>
          <a v-if="reportUrl" class="report-link" :href="reportUrl"><AppIcon name="download" :size="14" />分析报告</a>
        </div>
        <div class="prompt-composer" :class="{ 'is-running': isRunning }">
          <textarea v-model="prompt" rows="3" aria-label="输入问题或工业建模指令" placeholder="例如：这批数据最大的问题是什么？为什么第3轮最好？"></textarea>
          <div class="composer-footer">
            <div><span class="composer-tag">当前任务</span><span>{{ contextRunId }}</span></div>
            <button class="send-button" type="button" :disabled="isRunning || !prompt.trim()" @click="runWorkflow">
              <AppIcon :name="isRunning ? 'loop' : 'arrow'" :class="{ spinning: isRunning }" />
              {{ isRunning ? `处理中 ${runProgress}%` : '发送' }}
            </button>
          </div>
          <div v-if="isRunning" class="composer-progress"><span :style="{ width: `${runProgress}%` }"></span></div>
        </div>
      </section>

      <aside class="agent-side-stack">
        <section class="panel intent-panel">
          <div class="section-heading compact"><div><span class="section-kicker">结构化意图</span><h2>Agent 解析结果</h2></div><StatusPill :tone="responseState ? 'success' : 'neutral'">规则匹配分 {{ (intent.confidence * 100).toFixed(0) }}%</StatusPill></div>
          <dl class="intent-list">
            <div><dt>当前任务</dt><dd><code>{{ contextRunId }}</code></dd></div>
            <div><dt>识别意图</dt><dd>{{ intentLabels[intent.key] ?? intent.key }}</dd></div>
            <div><dt>命中关键词</dt><dd>{{ intent.keywords?.join(' · ') || '通用问答' }}</dd></div>
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
          :class="{ 'is-complete': node.status === 'completed' || (!isRunning && node.status !== 'pending'), 'is-current': isRunning && index === currentNode, 'is-waiting': node.status === 'pending' || (isRunning && index > currentNode) }"
        >
          <span class="plan-node-icon"><AppIcon :name="node.icon" /></span>
          <div><span>{{ stepNumber(index) }}</span><strong>{{ node.name }}</strong><code>{{ node.tool }}</code><small>{{ node.output }}</small></div>
          <span class="plan-node-state"><AppIcon :name="node.status === 'completed' ? 'check' : isRunning && index === currentNode ? 'loop' : 'clock'" :class="{ spinning: isRunning && index === currentNode }" /></span>
        </article>
      </div>
    </section>

    <AgentTracePanel :run-id="contextRunId === '尚无任务' ? '' : contextRunId" :running="isRunning" />

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
.message-skill-chain > span.blocked { border-color: #f5c26b; color: #b45309; background: #fffbeb; }
.message-deliverables { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.message-deliverables strong, .message-deliverables a { display: inline-flex; align-items: center; gap: 3px; font-size: 7px; }
.message-deliverables strong { color: #475569; }
.message-deliverables a { padding: 3px 6px; border: 1px solid #a7f3d0; border-radius: 5px; color: #047857; background: #ecfdf5; text-decoration: none; }
@media (max-width: 680px) { .agent-delivery-bar span { width: 100%; margin-right: 0; } }
</style>
