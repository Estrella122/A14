import test from 'node:test'
import assert from 'node:assert/strict'
import { runIdFromUrl, pathWithRun, createRunResponseGuard, loadExplicitRunForSubmission } from '../src/utils/runBinding.js'

test('explicit run survives page navigation and copied URL', () => {
  const path = pathWithRun('/report-export/', 'run-A')
  assert.equal(runIdFromUrl(path), 'run-A')
  assert.equal(runIdFromUrl(pathWithRun('/standard-check/', runIdFromUrl(path))), 'run-A')
  assert.equal(runIdFromUrl(pathWithRun(path, 'run-B')), 'run-B')
})
test('late A response cannot overwrite switched B', () => {
  const guard = createRunResponseGuard()
  const a = guard.next()
  const b = guard.next()
  assert.equal(guard.current(a), false)
  assert.equal(guard.current(b), true)
  guard.invalidate()
  assert.equal(guard.current(b), false)
})

test('fresh page sends explicit URL run even before initial snapshot loads', async () => {
  const loaded = await loadExplicitRunForSubmission('A', null, async id => ({run_id:id}), () => 'A')
  assert.equal(loaded.run_id, 'A')
  await assert.rejects(loadExplicitRunForSubmission('A', null, async () => ({run_id:'A'}), () => 'B'), /任务已切换/)
  await assert.rejects(loadExplicitRunForSubmission('A', null, async () => ({run_id:'B'}), () => 'A'), /不一致/)
})
