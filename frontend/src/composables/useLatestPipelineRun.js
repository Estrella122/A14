import { computed, onBeforeUnmount, onMounted, ref, toValue } from 'vue'
import { getLatestPipelineRun } from '../api/pipeline'

export function getRunScenarioId(run) {
  const trace = run?.runtime_trace ?? {}
  const standardTrace = run?.results?.standardization?.runtime_trace ?? {}
  return trace.final_scene ?? standardTrace.final_scene ?? trace.selected_scene ?? standardTrace.selected_scene ?? trace.agent_scene ?? standardTrace.agent_scene ?? trace.detected_scene ?? standardTrace.detected_scene ?? run?.detected_scene ?? trace.scene_id ?? standardTrace.scene_id ?? run?.results?.standardization?.scenario?.scenario_id ?? null
}

export function useLatestPipelineRun(expectedScenarioId = null) {
  const rawLatestRun = ref(null)
  const pipelineError = ref('')
  let refreshTimer

  const latestRun = computed({
    get() {
      const run = rawLatestRun.value
      if (!toValue(expectedScenarioId)) return run
      const expected = toValue(expectedScenarioId)
      if (!run) return null
      const actual = getRunScenarioId(run)
      return !actual || actual === 'auto' || actual === expected ? run : null
    },
    set(run) { rawLatestRun.value = run },
  })

  async function refreshPipeline() {
    try {
      rawLatestRun.value = await getLatestPipelineRun()
      pipelineError.value = ''
    } catch (error) {
      pipelineError.value = error.message
    }
  }

  function handleUpdate(event) { rawLatestRun.value = event.detail }
  function handleStorage(event) {
    if (event.key !== 'processpilot-latest-run' || !event.newValue) return
    try { rawLatestRun.value = JSON.parse(event.newValue).snapshot } catch { refreshPipeline() }
  }

  onMounted(() => {
    try {
      const cached = JSON.parse(window.localStorage.getItem('processpilot-latest-run') || 'null')
      if (cached?.snapshot) rawLatestRun.value = cached.snapshot
    } catch { /* The API refresh below remains authoritative. */ }
    refreshPipeline()
    window.addEventListener('processpilot:pipeline-updated', handleUpdate)
    window.addEventListener('storage', handleStorage)
    refreshTimer = window.setInterval(refreshPipeline, 5000)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('processpilot:pipeline-updated', handleUpdate)
    window.removeEventListener('storage', handleStorage)
    window.clearInterval(refreshTimer)
  })

  return { latestRun, rawLatestRun, pipelineError, refreshPipeline }
}
