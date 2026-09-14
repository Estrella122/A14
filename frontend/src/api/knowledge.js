import { apiRequest } from './client'

export async function getKnowledgeSummary() {
  const payload = await apiRequest('/knowledge/summary/')
  return payload.data
}

export async function searchKnowledge(query, sceneId = '') {
  const params = new URLSearchParams({ q: query })
  if (sceneId) params.set('scene_id', sceneId)
  const payload = await apiRequest(`/knowledge/search/?${params}`)
  return payload.data
}

export async function submitRoutingFeedback(body) {
  const payload = await apiRequest('/knowledge/feedback/', { method: 'POST', body })
  return payload.data
}
