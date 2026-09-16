import test from 'node:test'
import assert from 'node:assert/strict'
import { applyRuntimeEvents, compactRuntimeEvents, mergeRuntimeEvents, runtimeEventIsActive, visibleRuntimeEvents } from '../src/utils/runtimeEvents.js'

test('replay and incremental batches do not duplicate events', () => {
  const first = [{ sequence: 1, event_type: 'task_understanding_started' }, { sequence: 2, event_type: 'skill_selected' }]
  const merged = mergeRuntimeEvents(first, [{ sequence: 2, event_type: 'skill_selected' }, { sequence: 3, event_type: 'skill_loaded' }])
  assert.deepEqual(merged.map((event) => event.sequence), [1, 2, 3])
})

test('executor lifecycle updates DAG independently and keeps partial status', () => {
  const base = applyRuntimeEvents({}, [{ sequence: 1, event_type: 'execution_plan_created', metadata: { execution_dag: { steps: [{ executor: 'modeling' }, { executor: 'optimization' }] } } }])
  const waiting = applyRuntimeEvents(base, [{ sequence: 2, event_type: 'executor_waiting', executor: 'optimization', status: 'waiting', message: 'waiting for model artifact', metadata: {} }, { sequence: 3, event_type: 'executor_started', executor: 'modeling', status: 'executing', message: 'started', metadata: {} }])
  assert.equal(waiting.executor_results.find((item) => item.executor === 'optimization').status, 'waiting')
  assert.equal(waiting.executor_results.find((item) => item.executor === 'modeling').status, 'executing')
  const completed = applyRuntimeEvents(waiting, [{ sequence: 4, event_type: 'executor_partial', executor: 'optimization', status: 'partial', message: 'coverage warning', metadata: { warnings: ['coverage'] } }])
  assert.equal(completed.executor_results.find((item) => item.executor === 'optimization').status, 'partial')
})

test('timeline keeps operational reasons and omits noisy recall events', () => {
  const events = visibleRuntimeEvents([
    { sequence: 1, event_type: 'skill_resolution_started', status: 'executing' },
    { sequence: 2, event_type: 'capability_selected', status: 'selected', message: 'context matched' },
    { sequence: 3, event_type: 'executor_blocked', status: 'blocked', message: 'missing objective' },
  ])
  assert.deepEqual(events.map((event) => event.sequence), [2, 3])
  assert.equal(events[1].message, 'missing objective')
})

test('MCP progress is visible and updates the runtime receipt', () => {
  const event = {
    sequence: 4,
    event_type: 'mcp_tool_progress',
    stage: 'mcp:cleaning',
    status: 'executing',
    message: 'MCP run_dynamic_selection：时间对齐、清洗与训练集冻结',
    metadata: {
      tool_name: 'run_dynamic_selection',
      job_id: 'job_1',
      current_stage: { key: 'cleaning', label: '时间对齐、清洗与训练集冻结' },
      execution_timeline: [{ stage: 'cleaning', status: 'running' }],
    },
  }
  assert.equal(visibleRuntimeEvents([event])[0].event_type, 'mcp_tool_progress')
  const runtime = applyRuntimeEvents({}, [event])
  assert.equal(runtime.mcp.tool_name, 'run_dynamic_selection')
  assert.equal(runtime.mcp.current_stage.key, 'cleaning')
})

test('completed timelines never animate historical running events', () => {
  const started = { sequence: 1, event_type: 'executor_started', status: 'executing' }
  assert.equal(runtimeEventIsActive(started, 'running'), true)
  assert.equal(runtimeEventIsActive(started, 'completed'), false)
})

test('compact timeline stays bounded and keeps the terminal event', () => {
  const events = Array.from({ length: 8 }, (_, index) => ({ sequence: index + 1, event_type: index === 7 ? 'answer_generation_completed' : 'executor_started', status: index === 7 ? 'completed' : 'executing' }))
  const compact = compactRuntimeEvents(events, 4)
  assert.equal(compact.length, 4)
  assert.equal(compact.at(-1).event_type, 'answer_generation_completed')
})

test('timeline shows model lifecycle but leaves token deltas to the streaming draft', () => {
  const events = visibleRuntimeEvents([
    { sequence: 1, event_type: 'llm_generation_started', status: 'executing' },
    { sequence: 2, event_type: 'llm_response_delta', status: 'streaming', metadata: { delta: '回答' } },
    { sequence: 3, event_type: 'llm_generation_completed', status: 'completed' },
  ])
  assert.deepEqual(events.map((event) => event.sequence), [1, 3])
})
