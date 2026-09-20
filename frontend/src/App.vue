<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './components/AppIcon.vue'
import StatusPill from './components/StatusPill.vue'
import { navGroups, navItems, projects } from './data/projectData'
import CommandPalette from './components/CommandPalette.vue'
import { pathWithRun, selectedRunId } from './utils/runBinding'
import { useLatestPipelineRun, getRunScenarioId } from './composables/useLatestPipelineRun'
import { buildSceneState } from './composables/useSceneBinding'
import { apiRequest } from './api/client'

const viewMap = {
  '/portal/': defineAsyncComponent(() => import('./views/PortalView.vue')),
  '/user/': defineAsyncComponent(() => import('./views/AgentWorkflowView.vue')),
  '/overview/': defineAsyncComponent(() => import('./views/OverviewView.vue')),
  '/agent-review/': defineAsyncComponent(() => import('./views/AgentWorkflowView.vue')),
  '/digital-twin/': defineAsyncComponent(() => import('./views/DigitalTwinView.vue')),
  '/scenario-data/': defineAsyncComponent(() => import('./views/DataAssetsView.vue')),
  '/standard-check/': defineAsyncComponent(() => import('./views/CleaningView.vue')),
  '/data-selection/': defineAsyncComponent(() => import('./views/DataSelectionView.vue')),
  '/identification-modeling/': defineAsyncComponent(() => import('./views/ModelingView.vue')),
  '/closed-loop-optimization/': defineAsyncComponent(() => import('./views/OptimizationView.vue')),
  '/report-export/': defineAsyncComponent(() => import('./views/DeliveryView.vue')),
  '/pipeline-builder/': defineAsyncComponent(() => import('./views/PipelineBuilderView.vue')),
  '/experiments/': defineAsyncComponent(() => import('./views/ExperimentTrackerView.vue')),
  '/knowledge-base/': defineAsyncComponent(() => import('./views/KnowledgeBaseView.vue')),
  '/mcp-center/': defineAsyncComponent(() => import('./views/McpCenterView.vue')),
}

function normalizePath(path) {
  if (!path || path === '/' || path === '/index.html') return '/portal/'
  const cleanPath = path.replace(/index\.html$/, '')
  return cleanPath.endsWith('/') ? cleanPath : `${cleanPath}/`
}

function getStoredProject() {
  try {
    const stored = window.localStorage.getItem('processpilot-project')
    return projects.some((project) => project.id === stored) ? stored : projects[0].id
  } catch {
    return projects[0].id
  }
}

const activePath = ref(normalizePath(window.location.pathname))
const currentProjectId = ref(getStoredProject())
const currentProject = computed(() => projects.find((project) => project.id === currentProjectId.value) ?? projects[0])
const { latestRun, pipelineError } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(currentProject.value, latestRun.value))
const dataSceneText = computed(() => sceneState.value.data_scene.display_name)
const effectiveProject = computed(() => projects.find(project => project.scenarioId === getRunScenarioId(latestRun.value)) ?? currentProject.value)
const dataSceneStatus = computed(() => sceneState.value.data_scene_status_label)
const activeLatestRun = computed(() => latestRun.value)
const isPortal = computed(() => activePath.value === '/portal/')
const isUserBoard = computed(() => activePath.value === '/user/')
const isStaffBoard = computed(() => !isPortal.value && !isUserBoard.value)
const activeItem = computed(() => {
  if (isPortal.value) return { label: '入口选择', shortLabel: '入口', path: '/portal/', icon: 'dashboard' }
  if (isUserBoard.value) return { label: '用户板块', shortLabel: '用户', path: '/user/', icon: 'spark' }
  return navItems.find((item) => item.path === activePath.value) ?? navItems[0]
})
const activeView = computed(() => viewMap[activePath.value] ?? viewMap['/portal/'])
const toast = ref(null)
const commandPaletteOpen = ref(false)
let toastTimer
let healthTimer
const mcpHealth = ref({ configured: false, online: false })

async function refreshHealth() {
  try {
    const payload = await apiRequest('/health/')
    mcpHealth.value = payload.mcp ?? { configured: false, online: false }
  } catch {
    mcpHealth.value = { configured: true, online: false }
  }
}

function navigate(path) {
  const normalized = normalizePath(path)
  if (normalized !== activePath.value) window.history.pushState({}, '', pathWithRun(normalized, selectedRunId()))
  activePath.value = normalized
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handlePopState() {
  activePath.value = normalizePath(window.location.pathname)
}

function showToast(payload) {
  window.clearTimeout(toastTimer)
  toast.value = {
    tone: payload?.tone ?? 'neutral',
    title: payload?.title ?? '操作已完成',
    message: payload?.message ?? '',
  }
  toastTimer = window.setTimeout(() => { toast.value = null }, 4200)
}

function closeToast() {
  window.clearTimeout(toastTimer)
  toast.value = null
}

function handleStrategyAccepted(strategy) {
  showToast({
    tone: 'success',
    title: '闭环策略已交接给总工程',
    message: `${strategy?.strategy_version ?? '当前策略'} 已写入统一交接事件，评审与报告模块可读取该策略包。`,
  })
}

function handleSceneDetected(payload) {
  const matched = projects.find((project) => project.scenarioId === payload?.scenarioId)
  if (matched) currentProjectId.value = matched.id
  if (!isUserBoard.value) navigate(payload?.path || '/digital-twin/')
  showToast({
    tone: matched ? 'success' : 'warning',
    title: matched ? `已识别${matched.shortName}场景` : '已完成场景识别',
    message: matched
      ? (isUserBoard.value ? `任务 ${payload?.runId || ''} 已绑定场景；用户板块继续保留在 Agent 中枢。` : `任务 ${payload?.runId || ''} 已绑定对应项目、三维场景和 Skill 上下文。`)
      : '当前识别结果尚无对应的前端项目模板。',
  })
}

function executeCommand(command) {
  commandPaletteOpen.value = false
  navigate(command.path)
  if (!command.action) return
  window.setTimeout(() => {
    if (command.action === 'save-pipeline') window.dispatchEvent(new CustomEvent('processpilot:save-pipeline'))
    else window.dispatchEvent(new CustomEvent('processpilot:command', { detail: { action: command.action } }))
  }, 260)
}

function handleGlobalKeydown(event) {
  if (!isStaffBoard.value) return
  const target = event.target
  const editing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target?.isContentEditable
  const modifier = event.metaKey || event.ctrlKey
  if (modifier && event.key.toLowerCase() === 'k') { event.preventDefault(); commandPaletteOpen.value = !commandPaletteOpen.value; return }
  if (event.key === 'Escape' && commandPaletteOpen.value) { commandPaletteOpen.value = false; return }
  if (editing) return
  if (modifier && /^[1-8]$/.test(event.key)) { event.preventDefault(); navigate(navItems[Number(event.key) - 1]?.path ?? '/overview/'); return }
  if (modifier && event.key.toLowerCase() === 's') {
    event.preventDefault()
    if (activePath.value !== '/pipeline-builder/') navigate('/pipeline-builder/')
    window.setTimeout(() => window.dispatchEvent(new CustomEvent('processpilot:save-pipeline')), 260)
  }
}

watch(currentProjectId, (value, previous) => {
  try { window.localStorage.setItem('processpilot-project', value) } catch { /* local storage is optional */ }
  if (previous) showToast({ tone: 'info', title: '项目上下文已切换', message: `${currentProject.value.name} 的数据、模型与运行记录已载入。` })
})
watch([activePath, effectiveProject], () => {
  document.title = `${activeItem.value.label} · ${effectiveProject.value.shortName} · ProcessPilot`
}, { immediate: true })

onMounted(() => {
  window.addEventListener('popstate', handlePopState)
  window.addEventListener('keydown', handleGlobalKeydown)
  refreshHealth()
  healthTimer = window.setInterval(refreshHealth, 15000)
})
onBeforeUnmount(() => {
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('keydown', handleGlobalKeydown)
  window.clearTimeout(toastTimer)
  window.clearInterval(healthTimer)
})
</script>

<template>
  <div class="app-shell" :class="{ 'is-entry-shell': isPortal, 'is-user-shell': isUserBoard }">
    <aside v-if="isStaffBoard" class="app-sidebar">
      <a class="brand-lockup" href="/portal/" @click.prevent="navigate('/portal/')">
        <span class="brand-symbol"><i></i><b></b><em></em></span>
        <span class="brand-copy"><strong>ProcessPilot</strong><small>APC Modeling Agent</small></span>
      </a>

      <div class="sidebar-project-card">
        <span class="sidebar-project-label">当前项目</span>
        <strong>{{ effectiveProject.shortName }}</strong>
        <p>{{ effectiveProject.unit }}</p>
        <span class="sidebar-project-status"><i></i>{{ effectiveProject.badge }}</span>
      </div>

      <nav class="side-navigation" aria-label="主功能导航">
        <div v-for="group in navGroups" :key="group.label" class="nav-group">
          <span class="nav-group-label">{{ group.label }}</span>
          <a
            v-for="item in group.items"
            :key="item.path"
            :href="pathWithRun(item.path, selectedRunId())"
            :class="{ active: activePath === item.path }"
            :aria-current="activePath === item.path ? 'page' : undefined"
            :title="item.label"
            @click.prevent="navigate(item.path)"
          >
            <AppIcon :name="item.icon" />
            <span>{{ item.label }}</span>
            <i v-if="item.path === '/closed-loop-optimization/' && activeLatestRun?.status === 'running'" class="nav-live-dot" aria-label="正在运行"></i>
          </a>
        </div>
      </nav>

      <div class="sidebar-runtime">
        <div><span><AppIcon name="spark" :size="17" /></span><p><strong>Evidence Agent</strong><small>任务证据 · 在线</small></p><i></i></div>
        <div><span><AppIcon name="shield" :size="17" /></span><p><strong>本地执行</strong><small>任务目录 · 可追溯</small></p><i></i></div>
      </div>

      <div class="sidebar-user">
        <span class="user-avatar">YS</span>
        <div><strong>项目工程师</strong><small>APC Modeling Team</small></div>
        <button class="icon-button" type="button" aria-label="查看当前身份" @click="showToast({ tone: 'info', title: '当前身份', message: '项目工程师 · APC Modeling Team' })"><AppIcon name="more" /></button>
      </div>
    </aside>

    <div class="app-content">
      <header v-if="!isPortal && !isUserBoard" class="content-topbar">
        <div class="mobile-brand"><span class="brand-symbol small"><i></i><b></b><em></em></span><strong>ProcessPilot</strong></div>
        <div class="topbar-context">
          <span class="topbar-breadcrumb">{{ isUserBoard ? '用户板块' : '工作人员板块' }} <AppIcon name="chevron" :size="14" /> {{ activeItem.label }}</span>
          <div class="topbar-scene-pills" aria-label="数据识别场景">
            <StatusPill tone="brand">本次数据：{{ dataSceneText }} · {{ dataSceneStatus }}</StatusPill>
          </div>
        </div>
        <div class="topbar-actions">
          <button class="command-trigger" type="button" aria-label="打开全局命令面板" @click="commandPaletteOpen = true"><AppIcon name="spark" :size="15" /><span>搜索命令</span><kbd>⌘ K</kbd></button>
          <button class="btn btn-secondary" type="button" @click="navigate('/user/')"><AppIcon name="spark" />用户板块</button>
          <button class="topbar-health" :class="{ 'is-offline': !mcpHealth.online }" type="button" :title="mcpHealth.online ? `MCP 已加载 ${mcpHealth.tool_count ?? 0} 个工具` : 'MCP 服务未连接'" @click="navigate('/mcp-center/')">
            <span><i></i>后端 · MCP</span><strong>{{ mcpHealth.online ? 'ONLINE' : 'OFFLINE' }}</strong>
          </button>
          <button class="icon-button topbar-icon" type="button" aria-label="查看任务通知" @click="showToast({ tone: activeLatestRun ? 'success' : 'info', title: '任务通知', message: activeLatestRun ? `当前场景任务 ${activeLatestRun.run_id} 状态：${activeLatestRun.status}` : '当前场景尚无 CSV 流水线任务。' })"><AppIcon name="bell" /><i class="notification-dot"></i></button>
          <button class="help-button" type="button" aria-label="打开 Agent 帮助" @click="navigate('/agent-review/'); showToast({ tone: 'info', title: 'Agent 帮助', message: '已打开 Agent 中枢，可上传 CSV 或直接输入问题。' })">?</button>
        </div>
      </header>

      <main class="content-main" :class="{ 'portal-main': isPortal, 'user-main': isUserBoard }">
        <p v-if="pipelineError" role="alert" class="pipeline-error">{{ pipelineError }}</p>
        <component
          :is="activeView"
          :key="`${activePath}-${effectiveProject.id}`"
          :project="effectiveProject"
          :projects="projects"
          :current-project-id="currentProjectId"
          :user-board="isUserBoard"
          @navigate="navigate"
          @notify="showToast"
          @project-change="currentProjectId = $event"
          @strategy-accepted="handleStrategyAccepted"
          @scene-detected="handleSceneDetected"
        />
      </main>

      <footer v-if="!isPortal" class="app-footer">
        <span>ProcessPilot · 基于 Agent 的流程工业建模数据智能优选与闭环寻优系统</span>
        <span>{{ isUserBoard ? '用户板块 · Agent 智能中枢' : '工作人员板块 · 全量工程界面' }}</span>
      </footer>
    </div>

    <Transition name="toast">
      <div v-if="toast" class="app-toast" :class="`is-${toast.tone}`" role="status" aria-live="polite">
        <span class="toast-icon"><AppIcon :name="toast.tone === 'success' ? 'check' : toast.tone === 'warning' ? 'alert' : 'spark'" /></span>
        <div><strong>{{ toast.title }}</strong><p>{{ toast.message }}</p></div>
        <button type="button" aria-label="关闭通知" @click="closeToast">×</button>
      </div>
    </Transition>
    <CommandPalette v-if="isStaffBoard" :open="commandPaletteOpen" :nav-items="navItems" @close="commandPaletteOpen = false" @select="executeCommand" />
  </div>
</template>
