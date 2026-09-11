import { onBeforeUnmount, onMounted, ref } from 'vue'
import { getLatestPipelineRun, listPipelineRuns } from '../api/pipeline'

export function useLatestPipelineRun(scenarioIdSource = null) {
  const latestRun = ref(null)
  const pipelineError = ref('')
  let refreshTimer

  function expectedScenarioId() {
    return typeof scenarioIdSource === 'function' ? scenarioIdSource() : scenarioIdSource?.value ?? scenarioIdSource
  }

  function runScenarioId(snapshot) {
    return snapshot?.results?.standardization?.scenario?.scenario_id ?? null
  }

  function matchesCurrentScenario(snapshot) {
    const expected = expectedScenarioId()
    return !expected || runScenarioId(snapshot) === expected
  }

  async function refreshPipeline() {
    try {
      let snapshot = await getLatestPipelineRun()
      if (snapshot && !matchesCurrentScenario(snapshot)) {
        const history = await listPipelineRuns()
        snapshot = history.find(matchesCurrentScenario) ?? null
      }
      latestRun.value = snapshot
      pipelineError.value = ''
    } catch (error) {
      pipelineError.value = error.message
    }
  }

  function handleUpdate(event) {
    if (matchesCurrentScenario(event.detail)) latestRun.value = event.detail
    else refreshPipeline()
  }
  function handleStorage(event) {
    if (event.key !== 'processpilot-latest-run' || !event.newValue) return
    try {
      const snapshot = JSON.parse(event.newValue).snapshot
      if (matchesCurrentScenario(snapshot)) latestRun.value = snapshot
      else refreshPipeline()
    } catch { refreshPipeline() }
  }

  onMounted(() => {
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

  return { latestRun, pipelineError, refreshPipeline }
}
