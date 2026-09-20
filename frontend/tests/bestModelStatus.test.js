import test from 'node:test'
import assert from 'node:assert/strict'
import { pipelineStatus } from '../src/utils/executionStatus.js'

test('selected model with warnings is a result, while historical no-winner stays unchanged', () => {
  const run = { status: 'completed', results: { optimization: { optimization_outcome: 'best_available_candidate', best_round: 3 } } }
  assert.equal(pipelineStatus(run), '已选出最佳模型（附质量提示）')
  assert.equal(pipelineStatus({ status: 'needs_review', results: { optimization: { optimization_outcome: 'no_feasible_candidate' } } }), '搜索结束，无合格候选')
})
