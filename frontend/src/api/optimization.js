import { apiDownload, apiRequest } from './client'

export function listOptimizationStudies(projectCode, { signal } = {}) {
  const query = new URLSearchParams({ project_code: projectCode })
  return apiRequest(`/optimization/studies/?${query}`, { signal })
}

export function createOptimizationStudy(payload, { signal } = {}) {
  return apiRequest('/optimization/studies/', { method: 'POST', body: payload, signal })
}

export function runOptimizationStep(studyId, { signal } = {}) {
  return apiRequest(`/optimization/studies/${studyId}/step/`, { method: 'POST', signal })
}

export function acceptOptimizationStudy(studyId, { signal } = {}) {
  return apiRequest(`/optimization/studies/${studyId}/accept/`, { method: 'POST', signal })
}

export function downloadOptimizationStudy(studyId, format = 'csv', { signal } = {}) {
  return apiDownload(`/optimization/studies/${studyId}/export/?format=${format}`, { signal })
}
