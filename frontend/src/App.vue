<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './components/AppIcon.vue'
import StatusPill from './components/StatusPill.vue'
import { navGroups, navItems, projects } from './data/projectData'
import OverviewView from './views/OverviewView.vue'
import AgentWorkflowView from './views/AgentWorkflowView.vue'
import DataAssetsView from './views/DataAssetsView.vue'
import CleaningView from './views/CleaningView.vue'
import DataSelectionView from './views/DataSelectionView.vue'
import ModelingView from './views/ModelingView.vue'
import OptimizationView from './views/OptimizationView.vue'
import DeliveryView from './views/DeliveryView.vue'
import PipelineBuilderView from './views/PipelineBuilderView.vue'
import ExperimentTrackerView from './views/ExperimentTrackerView.vue'
import CommandPalette from './components/CommandPalette.vue'
import { useLatestPipelineRun } from './composables/useLatestPipelineRun'

const viewMap = {
  '/overview/': OverviewView,
  '/agent-review/': AgentWorkflowView,
  '/scenario-data/': DataAssetsView,
  '/standard-check/': CleaningView,
  '/data-selection/': DataSelectionView,
  '/identification-modeling/': ModelingView,
  '/closed-loop-optimization/': OptimizationView,
  '/report-export/': DeliveryView,
  '/pipeline-builder/': PipelineBuilderView,
  '/experiments/': ExperimentTrackerView,
}

function normalizePath(path) {
  if (!path || path === '/' || path === '/index.html') return '/overview/'
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
const { latestRun } = useLatestPipelineRun()
const latestRunScenarioId = computed(() => latestRun.value?.results?.standardization?.scenario?.scenario_id ?? latestRun.value?.scenario_request ?? null)
const activeLatestRun = computed(() => {
  if (!latestRun.value) return null
  if (!latestRunScenarioId.value || latestRunScenarioId.value === 'auto') return latestRun.value
  return latestRunScenarioId.value === currentProject.value.scenarioId ? latestRun.value : null
})
const runtimeStandardization = computed(() => latestRun.value?.results?.standardization ?? {})
const runtimeDictionary = computed(() => runtimeStandardization.value.dictionary ?? [])
const runtimeInput = computed(() => runtimeDictionary.value.find((item) => item.role === 'manipulated') ?? runtimeDictionary.value.find((item) => item.role === 'disturbance'))
const runtimeOutput = computed(() => runtimeDictionary.value.find((item) => item.role === 'controlled'))
const effectiveProject = computed(() => {
  if (!activeLatestRun.value) return currentProject.value
  const scenario = runtimeStandardization.value.scenario?.scenario_name ?? '待识别工业场景'
  return {
    ...currentProject.value,
    name: `${scenario}建模任务`,
    shortName: scenario,
    scene: scenario,
    unit: activeLatestRun.value.original_name,
    badge: '当前 CSV 真实运行',
    mv: runtimeInput.value?.display_name ?? runtimeInput.value?.standard_name ?? '主要输入变量',
    mvTag: runtimeInput.value?.standard_name ?? '—',
    mvUnit: runtimeInput.value?.unit ?? '',
    target: runtimeOutput.value?.display_name ?? runtimeOutput.value?.standard_name ?? '被控输出变量',
    targetTag: runtimeOutput.value?.standard_name ?? '—',
    targetUnit: runtimeOutput.value?.unit ?? '',
    runId: activeLatestRun.value.run_id,
  }
})
const activeItem = computed(() => navItems.find((item) => item.path === activePath.value) ?? navItems[0])
const activeView = computed(() => viewMap[activePath.value] ?? OverviewView)
const toast = ref(null)
const commandPaletteOpen = ref(false)
let toastTimer

function navigate(path) {
  const normalized = normalizePath(path)
  if (normalized !== activePath.value) window.history.pushState({}, '', normalized)
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
watch(latestRunScenarioId, (scenarioId) => {
  const detectedProject = projects.find((project) => project.scenarioId === scenarioId)
  if (detectedProject) currentProjectId.value = detectedProject.id
})

watch([activePath, effectiveProject], () => {
  document.title = `${activeItem.value.label} · ${effectiveProject.value.shortName} · ProcessPilot`
}, { immediate: true })

onMounted(() => { window.addEventListener('popstate', handlePopState); window.addEventListener('keydown', handleGlobalKeydown) })
onBeforeUnmount(() => {
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('keydown', handleGlobalKeydown)
  window.clearTimeout(toastTimer)
})
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <a class="brand-lockup" href="/overview/" @click.prevent="navigate('/overview/')">
        <span class="brand-symbol"><i></i><b></b><em></em></span>
        <span class="brand-copy"><strong>ProcessPilot</strong><small>APC Modeling Agent</small></span>
      </a>

      <div class="sidebar-project-card">
        <span class="sidebar-project-label">当前项目</span>
        <strong>{{ effectiveProject.shortName }}</strong>
        <small>{{ effectiveProject.unit }}</small>
        <span class="sidebar-project-status"><i></i>{{ effectiveProject.badge }}</span>
      </div>

      <nav class="side-navigation" aria-label="主功能导航">
        <div v-for="group in navGroups" :key="group.label" class="nav-group">
          <span class="nav-group-label">{{ group.label }}</span>
          <a
            v-for="item in group.items"
            :key="item.path"
            :href="item.path"
            :class="{ active: activePath === item.path }"
            :aria-current="activePath === item.path ? 'page' : undefined"
            :title="item.label"
            @click.prevent="navigate(item.path)"
          >
            <AppIcon :name="item.icon" />
            <span>{{ item.label }}</span>
            <i v-if="item.path === '/closed-loop-optimization/'" class="nav-live-dot" aria-label="正在运行"></i>
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
      <header class="content-topbar">
        <div class="mobile-brand"><span class="brand-symbol small"><i></i><b></b><em></em></span><strong>ProcessPilot</strong></div>
        <div class="topbar-context">
          <span class="topbar-breadcrumb">工作台 <AppIcon name="chevron" :size="14" /> {{ activeItem.label }}</span>
          <label class="project-selector" aria-label="切换当前项目场景">
            <select v-model="currentProjectId">
              <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.shortName }} · {{ project.target }}</option>
            </select>
          </label>
          <StatusPill :tone="activeLatestRun ? 'success' : 'neutral'" class="demo-mode"><span class="demo-pulse"></span>{{ activeLatestRun ? '当前CSV真实运行' : '等待CSV' }}</StatusPill>
        </div>
        <div class="topbar-actions">
          <button class="command-trigger" type="button" aria-label="打开全局命令面板" @click="commandPaletteOpen = true"><AppIcon name="spark" :size="15" /><span>搜索命令</span><kbd>⌘ K</kbd></button>
          <div class="topbar-health"><span><i></i>后端模板服务</span><strong>ONLINE</strong></div>
          <button class="icon-button topbar-icon" type="button" aria-label="查看任务通知" @click="showToast({ tone: activeLatestRun ? 'success' : 'info', title: '任务通知', message: activeLatestRun ? `当前场景任务 ${activeLatestRun.run_id} 状态：${activeLatestRun.status}` : '当前场景尚无 CSV 流水线任务。' })"><AppIcon name="bell" /><i class="notification-dot"></i></button>
          <button class="help-button" type="button" aria-label="打开 Agent 帮助" @click="navigate('/agent-review/'); showToast({ tone: 'info', title: 'Agent 帮助', message: '已打开 Agent 中枢，可上传 CSV 或直接输入问题。' })">?</button>
        </div>
      </header>

      <main class="content-main">
        <component
          :is="activeView"
          :key="`${activePath}-${effectiveProject.id}`"
          :project="effectiveProject"
          @navigate="navigate"
          @notify="showToast"
          @strategy-accepted="handleStrategyAccepted"
        />
      </main>

      <footer class="app-footer">
        <span>ProcessPilot · 基于 Agent 的流程工业建模数据智能优选与闭环寻优系统</span>
        <span>Demo Build 2026.07 · A14 和利时企业命题</span>
      </footer>
    </div>

    <Transition name="toast">
      <div v-if="toast" class="app-toast" :class="`is-${toast.tone}`" role="status" aria-live="polite">
        <span class="toast-icon"><AppIcon :name="toast.tone === 'success' ? 'check' : toast.tone === 'warning' ? 'alert' : 'spark'" /></span>
        <div><strong>{{ toast.title }}</strong><p>{{ toast.message }}</p></div>
        <button type="button" aria-label="关闭通知" @click="closeToast">×</button>
      </div>
    </Transition>
    <CommandPalette :open="commandPaletteOpen" :nav-items="navItems" @close="commandPaletteOpen = false" @select="executeCommand" />
  </div>
</template>
