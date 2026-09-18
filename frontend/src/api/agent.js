import { ApiError, apiRequest, secureFetch } from './client'

export async function sendAgentMessage(message, runId = null, previousIntent = null, previousIntents = [], llm = null) {
  const payload = await apiRequest('/agent/chat/', {
    method: 'POST',
    body: { message, run_id: runId, previous_intent: previousIntent, previous_intents: previousIntents, llm },
  })
  return payload.data
}

export async function startAgentLiveRun(message, runId = null, previousIntent = null, previousIntents = [], llm = null) {
  const payload = await apiRequest('/agent/chat/live/', {
    method: 'POST',
    body: { message, run_id: runId, previous_intent: previousIntent, previous_intents: previousIntents, llm },
  })
  return payload.data
}

export async function getAgentLLMProviders({ signal } = {}) {
  const payload = await apiRequest('/agent/llm/providers/', { signal })
  return payload.data
}

export async function testAgentLLMConnection(config, { signal } = {}) {
  const payload = await apiRequest('/agent/llm/test/', { method: 'POST', body: config, signal })
  return payload.data
}

export async function getAgentSkillEvents(skillRunId, after = 0, { signal } = {}) {
  const payload = await apiRequest(`/agent/skill-runs/${encodeURIComponent(skillRunId)}/events/?after=${encodeURIComponent(after)}`, { signal })
  return payload.data
}

export async function streamAgentSkillEvents(skillRunId, after = 0, { signal, onRuntime } = {}) {
  const response = await secureFetch(`/agent/skill-runs/${encodeURIComponent(skillRunId)}/stream/?after=${encodeURIComponent(after)}`, {
    signal,
    headers: { Accept: 'text/event-stream' },
  })
  if (!response.ok) throw new ApiError(`实时事件流连接失败（HTTP ${response.status}）`, response.status)
  if (!response.body) throw new ApiError('当前浏览器不支持流式响应', 0)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      if (!block || block.startsWith(':') || block.startsWith('retry:')) continue
      let eventName = 'message'
      const data = []
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
      }
      if (!data.length) continue
      const payload = JSON.parse(data.join('\n'))
      if (eventName === 'runtime') onRuntime?.(payload)
      if (eventName === 'complete') return payload
      if (eventName === 'failed') throw new Error(payload.error || 'Agent 执行失败')
    }
    if (done) break
  }
  throw new Error('Agent 实时事件流提前结束')
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
