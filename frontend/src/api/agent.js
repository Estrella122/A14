import { apiRequest } from './client'

export async function sendAgentMessage(message, runId = null, previousIntent = null, previousIntents = []) {
  const payload = await apiRequest('/agent/chat/', {
    method: 'POST',
    body: { message, run_id: runId, previous_intent: previousIntent, previous_intents: previousIntents },
  })
  return payload.data
}

export async function startAgentLiveRun(message, runId = null, previousIntent = null, previousIntents = []) {
  const payload = await apiRequest('/agent/chat/live/', {
    method: 'POST',
    body: { message, run_id: runId, previous_intent: previousIntent, previous_intents: previousIntents },
  })
  return payload.data
}

export async function getAgentSkillEvents(skillRunId, after = 0, { signal } = {}) {
  const payload = await apiRequest(`/agent/skill-runs/${encodeURIComponent(skillRunId)}/events/?after=${encodeURIComponent(after)}`, { signal })
  return payload.data
}

// TODO(api): 当前 trace 由可审计的阶段证据生成；后续可接入更细粒度的工具事件流，失败时保留 mock 降级。
export async function getAgentTrace(runId, { signal } = {}) {
  if (!runId) throw new Error('尚无可读取的 Agent 任务')
  const payload = await apiRequest(`/agent/runs/${encodeURIComponent(runId)}/trace/`, { signal })
  return payload.data
}

export async function getAgentSkills({ signal } = {}) {
  const payload = await apiRequest('/agent/skills/', { signal })
  return payload.data
}

export async function createAgentPlan(message, runId = null) {
  const payload = await apiRequest('/agent/plans/', { method: 'POST', body: { message, run_id: runId } })
  return payload.data
}

export async function runAgentSkillPlan({ message, runId, plan = null }) {
  const payload = await apiRequest('/agent/skill-runs/', { method: 'POST', body: { message, run_id: runId, plan } })
  return payload.data
}

export async function getAgentSkillRun(skillRunId, { signal } = {}) {
  const payload = await apiRequest(`/agent/skill-runs/${encodeURIComponent(skillRunId)}/`, { signal })
  return payload.data
}
