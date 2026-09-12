import test from 'node:test'
import assert from 'node:assert/strict'
import { applyRuntimeEvents, mergeRuntimeEvents, visibleRuntimeEvents } from '../src/utils/runtimeEvents.js'

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
