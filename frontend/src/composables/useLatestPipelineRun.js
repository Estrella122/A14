import { computed, onBeforeUnmount, onMounted, ref, toValue } from 'vue'
import { getLatestPipelineRun, getPipelineRun } from '../api/pipeline'
import { selectedRunId, selectRun, createRunResponseGuard } from '../utils/runBinding'

export function getRunScenarioId(run) {
  const trace = run?.runtime_trace ?? {}
  const standardTrace = run?.results?.standardization?.runtime_trace ?? {}
  return trace.final_scene ?? standardTrace.final_scene ?? trace.selected_scene ?? standardTrace.selected_scene ?? trace.agent_scene ?? standardTrace.agent_scene ?? trace.detected_scene ?? standardTrace.detected_scene ?? run?.detected_scene ?? trace.scene_id ?? standardTrace.scene_id ?? run?.results?.standardization?.scenario?.scenario_id ?? null
}

export function useLatestPipelineRun(expectedScenarioId = null) {
  const rawLatestRun = ref(null)
  const pipelineError = ref('')
  const guard = createRunResponseGuard()
  let refreshTimer
  let disposed = false
  const latestRun = computed({
    get() {
      const run = rawLatestRun.value
      if (selectedRunId() || !toValue(expectedScenarioId)) return run
      const actual = getRunScenarioId(run)
      return !actual || actual === 'auto' || actual === toValue(expectedScenarioId) ? run : null
    },
    set(run) { rawLatestRun.value = run },
  })
  async function refreshPipeline() {
    const id = selectedRunId()
    const token = guard.next()
    try {
      const run = id ? await getPipelineRun(id) : await getLatestPipelineRun()
      if (disposed || !guard.current(token) || selectedRunId() !== id) return
      if (id && run?.run_id !== id) throw new Error('返回任务与所选任务不一致')
      rawLatestRun.value = run
      pipelineError.value = ''
      if (!id && run) selectRun(run.run_id, { replace: true })
    } catch (error) {
      if (!guard.current(token) || disposed) return
      rawLatestRun.value = null
      pipelineError.value = `所选任务不可用：${error.message}。未切换到其他任务。`
    }
  }
  function scheduleRefresh() {
    window.clearTimeout(refreshTimer)
    if (disposed) return
    const delay = document.hidden ? 30000 : ['queued', 'running'].includes(rawLatestRun.value?.status) ? 2000 : 15000
    refreshTimer = window.setTimeout(async () => { await refreshPipeline(); scheduleRefresh() }, delay)
  }
  function handleSelection() { guard.invalidate(); rawLatestRun.value = null; refreshPipeline() }
  function handleUpdate(event) {
    if (event.detail?.run_id === selectedRunId()) { guard.invalidate(); rawLatestRun.value = event.detail }
  }
  function handleVisibility() { if (!document.hidden) refreshPipeline(); scheduleRefresh() }
  onMounted(() => {
    refreshPipeline().finally(scheduleRefresh)
    window.addEventListener('processpilot:pipeline-updated', handleUpdate)
    window.addEventListener('processpilot:run-selected', handleSelection)
    window.addEventListener('popstate', handleSelection)
    document.addEventListener('visibilitychange', handleVisibility)
  })
  onBeforeUnmount(() => {
    disposed = true; guard.invalidate(); window.clearTimeout(refreshTimer)
    window.removeEventListener('processpilot:pipeline-updated', handleUpdate)
    window.removeEventListener('processpilot:run-selected', handleSelection)
    window.removeEventListener('popstate', handleSelection)
    document.removeEventListener('visibilitychange', handleVisibility)
  })
  return { latestRun, rawLatestRun, pipelineError, refreshPipeline }
}
