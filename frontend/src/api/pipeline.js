import { selectRun } from '../utils/runBinding'
import { apiBaseUrl, apiRequest, parseApiResponse, secureFetch } from './client'

export async function uploadPipelineFile(file, options = {}) {
  const form = new FormData()
  form.append('file', file)
  if (options.assetId) form.append('asset_id', options.assetId)
  form.append('scenario_id', options.scenarioId ?? 'auto')
  form.append('project_scene', options.projectSceneId ?? '')
  form.append('instruction', options.instruction ?? '')
  form.append('resample_rule', options.resampleRule ?? '10s')
  form.append('max_lag', String(options.maxLag ?? 60))
  form.append('overrides', JSON.stringify(options.overrides ?? {}))
  if (options.asyncAnalysis) form.append('async_analysis', 'true')
  const response = await secureFetch('/pipeline/runs/', { method: 'POST', body: form })
  const payload = await parseApiResponse(response)
  return payload.data
}

export async function getPipelineRun(runId, { signal } = {}) {
  const payload = await apiRequest(`/pipeline/runs/${encodeURIComponent(runId)}/`, { signal })
  return payload.data
}

export async function getLatestPipelineRun() {
  const payload = await apiRequest('/pipeline/runs/latest/')
  return payload.data
}

// TODO(api): 当前 GET 已返回运行摘要；后续数据量增大时补充服务端分页，接口失败则使用集中 mock 降级。
export async function listPipelineRuns({ signal, scenarioId, limit } = {}) {
  const params = new URLSearchParams()
  if (scenarioId) params.set('scenario_id', scenarioId)
  if (limit) params.set('limit', String(limit))
  const query = params.size ? `?${params}` : ''
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

export async function executePipelineWorkflow(runId, nodes, edges) {
  const payload = await apiRequest('/pipeline/workflows/execute/', {
    method: 'POST',
    body: {
      run_id: runId,
      nodes: nodes.map(({ id, type, config }) => ({ id, type, config })),
      edges: edges.map(({ from, to }) => ({ from, to })),
    },
  })
  return payload.data
}

export function artifactUrl(runId, key) {
  return `${apiBaseUrl}/pipeline/runs/${runId}/artifacts/${key}/`
}

export function announcePipelineUpdate(snapshot) {
  if (snapshot?.run_id) selectRun(snapshot.run_id)
  try { window.localStorage.setItem('processpilot-latest-run', JSON.stringify({ snapshot, announced_at: Date.now() })) } catch { /* Cross-tab sync is optional. */ }
  window.dispatchEvent(new CustomEvent('processpilot:pipeline-updated', { detail: snapshot }))
}
