import { onBeforeUnmount, onMounted, ref } from 'vue'
import { getLatestPipelineRun } from '../api/pipeline'

export function useLatestPipelineRun() {
  const latestRun = ref(null)
  const pipelineError = ref('')
  let refreshTimer

  async function refreshPipeline() {
    try {
      latestRun.value = await getLatestPipelineRun()
      pipelineError.value = ''
    } catch (error) {
      pipelineError.value = error.message
    }
  }

  function handleUpdate(event) { latestRun.value = event.detail }
  function handleStorage(event) {
    if (event.key !== 'processpilot-latest-run' || !event.newValue) return
    try { latestRun.value = JSON.parse(event.newValue).snapshot } catch { refreshPipeline() }
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
