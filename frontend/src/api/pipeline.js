import { apiBaseUrl, apiRequest } from './client'

export async function uploadPipelineFile(file, options = {}) {
  const form = new FormData()
  form.append('file', file)
  form.append('scenario_id', options.scenarioId ?? 'auto')
  form.append('project_scene', options.projectSceneId ?? '')
  form.append('instruction', options.instruction ?? '')
  form.append('resample_rule', options.resampleRule ?? '10s')
  form.append('max_lag', String(options.maxLag ?? 60))
  form.append('overrides', JSON.stringify(options.overrides ?? {}))
  const response = await fetch(`${apiBaseUrl}/pipeline/runs/`, { method: 'POST', body: form })
  const payload = await response.json()
  if (!response.ok || payload?.ok === false) throw new Error(payload?.message || `运行失败（HTTP ${response.status}）`)
  return payload.data
}

export async function getLatestPipelineRun() {
  const payload = await apiRequest('/pipeline/runs/latest/')
  return payload.data
}

// TODO(api): 当前 GET 已返回运行摘要；后续数据量增大时补充服务端分页，接口失败则使用集中 mock 降级。
export async function listPipelineRuns({ signal, scenarioId } = {}) {
  const query = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ''
  const payload = await apiRequest(`/pipeline/runs/${query}`, { signal })
  return payload.data
}

export async function rerunPipeline(runId, options = {}) {
  const payload = await apiRequest(`/pipeline/runs/${runId}/rerun/`, {
    method: 'POST',
    body: {
      resample_rule: options.resampleRule ?? '10s',
      max_lag: options.maxLag ?? 60,
      scenario_id: options.scenarioId,
      overrides: options.overrides,
    },
  })
  return payload.data
}

export function artifactUrl(runId, key) {
  return `${apiBaseUrl}/pipeline/runs/${runId}/artifacts/${key}/`
}

export function announcePipelineUpdate(snapshot) {
  try { window.localStorage.setItem('processpilot-latest-run', JSON.stringify({ snapshot, announced_at: Date.now() })) } catch { /* Cross-tab sync is optional. */ }
  window.dispatchEvent(new CustomEvent('processpilot:pipeline-updated', { detail: snapshot }))
}
