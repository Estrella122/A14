export function mergeRuntimeEvents(existing = [], incoming = []) {
  const bySequence = new Map(existing.map((event) => [event.sequence, event]))
  incoming.forEach((event) => bySequence.set(event.sequence, event))
  return [...bySequence.values()].sort((left, right) => left.sequence - right.sequence)
}

export function applyRuntimeEvents(runtime = {}, events = []) {
  const next = {
    capabilities: [...(runtime.capabilities ?? [])],
    execution_dag: runtime.execution_dag ?? { steps: [], target_groups: [] },
    skill_loading: { ...(runtime.skill_loading ?? {}) },
    executor_results: [...(runtime.executor_results ?? [])],
    artifacts: [...(runtime.artifacts ?? [])],
  }
  for (const event of events) {
    if (event.event_type.startsWith('capability_') && event.metadata?.candidate) {
      const candidate = event.metadata.candidate
      next.capabilities = [...next.capabilities.filter((item) => item.candidate !== candidate.candidate), candidate]
    }
    if (event.event_type === 'execution_plan_created') next.execution_dag = event.metadata?.execution_dag ?? next.execution_dag
    if (event.event_type === 'skill_loaded') next.skill_loading = { ...next.skill_loading, loaded: true, loaded_files: event.metadata?.loaded_files ?? [], skill_name: event.skill_id }
    if (event.event_type.startsWith('executor_')) {
      const result = { executor: event.executor, skill_id: event.executor, status: event.status, reason: event.message, duration_ms: event.metadata?.duration_ms, warnings: event.metadata?.warnings ?? [] }
      next.executor_results = [...next.executor_results.filter((item) => (item.executor ?? item.skill_id) !== event.executor), result]
    }
    if (event.event_type === 'artifact_produced' && event.metadata?.artifact) {
      const artifact = event.metadata.artifact
      const key = artifact.artifact_id ?? artifact.key ?? `${event.executor}-${event.sequence}`
      next.artifacts = [...next.artifacts.filter((item) => (item.artifact_id ?? item.key) !== key), artifact]
    }
  }
  return next
}

export function visibleRuntimeEvents(events = []) {
  const keyTypes = new Set(['task_understanding_started', 'task_understanding_completed', 'skill_selected', 'skill_loaded', 'execution_plan_created', 'executor_waiting', 'executor_started', 'executor_completed', 'executor_partial', 'executor_blocked', 'executor_failed', 'artifact_produced', 'answer_generation_started', 'llm_generation_started', 'llm_generation_completed', 'llm_generation_failed', 'answer_generation_completed', 'run_failed'])
  return events.filter((event) => keyTypes.has(event.event_type) || event.event_type.startsWith('capability_') && ['selected', 'blocked', 'deferred'].includes(event.status))
}

export function runtimeEventIsActive(event, runStatus) {
  return runStatus === 'running' && ['executing', 'queued', 'waiting'].includes(event?.status)
}

export function compactRuntimeEvents(events = [], limit = 4) {
  const rows = visibleRuntimeEvents(events)
  if (rows.length <= limit) return rows
  const terminal = [...rows].reverse().find((event) => ['answer_generation_completed', 'run_failed'].includes(event.event_type))
  const latest = rows.slice(-limit)
  if (!terminal || latest.includes(terminal)) return latest
  return [...latest, terminal].slice(-limit)
}
