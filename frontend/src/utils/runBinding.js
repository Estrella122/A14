export function runIdFromUrl(url) {
  return new URL(url, 'http://localhost').searchParams.get('run_id') || null
}

export function pathWithRun(path, runId) {
  const url = new URL(path, 'http://localhost')
  if (runId) url.searchParams.set('run_id', runId)
  else url.searchParams.delete('run_id')
  return `${url.pathname}${url.search}${url.hash}`
}

export function selectedRunId() { return runIdFromUrl(window.location.href) }

export function selectRun(runId, { replace = false } = {}) {
  const next = pathWithRun(window.location.href, runId)
  if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
    window.history[replace ? 'replaceState' : 'pushState']({}, '', next)
  }
  window.dispatchEvent(new CustomEvent('processpilot:run-selected', { detail: runId }))
}

export function createRunResponseGuard() {
  let sequence = 0
  return { next: () => ++sequence, current: token => token === sequence, invalidate: () => ++sequence }
}

export async function loadExplicitRunForSubmission(sourceRun, activeRun, loadRun, getSelection) {
  if (!sourceRun || activeRun?.run_id === sourceRun) return activeRun
  const loaded = await loadRun(sourceRun)
  if (getSelection() !== sourceRun) throw new Error('任务已切换，请在当前任务重新发送。')
  if (loaded?.run_id !== sourceRun) throw new Error('返回结果与选定任务不一致。')
  return loaded
}
