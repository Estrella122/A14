import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeExperimentRun } from '../src/utils/experimentRun.js'
import { defaultPipelineGraph } from '../src/data/pipelineDefinitions.js'

test('normalizes only real backend metrics and prediction rows', () => {
  const row = normalizeExperimentRun({
    run_id: 'real-1', original_name: 'plant.csv', status: 'completed',
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:09Z',
    results: { cleaning: { config: { resample_rule: '10s' } }, modeling: {
      config: { family: 'ARX', output_order: 2, input_order: 1, input_delay: 3 },
      metrics: { test: { r2: 0.72, aic: -88.4 } },
      prediction_preview: [{ split: 'test', y_true: 2, y_pred: 1.8, residual: 0.2 }, { split: 'validation', y_true: 9, y_pred: 9, residual: 0 }],
    } },
  })
  assert.equal(row.id, 'real-1')
  assert.equal(row.r2, 0.72)
  assert.deepEqual(row.actual, [2])
  assert.deepEqual(row.predicted, [1.8])
  assert.equal(row.duration, 9)
})

test('does not manufacture metrics when backend evidence is absent', () => {
  const row = normalizeExperimentRun({ run_id: 'empty', results: {} })
  assert.equal(row.r2, null)
  assert.equal(row.aic, null)
  assert.deepEqual(row.actual, [])
})

test('canonical visual pipeline is forward, connected, and unique', () => {
  const ids = defaultPipelineGraph.nodes.map((node) => node.id)
  assert.equal(new Set(ids).size, ids.length)
  assert.equal(defaultPipelineGraph.edges.length, ids.length - 1)
  assert.equal(defaultPipelineGraph.nodes[0].type, 'source')
  assert.equal(defaultPipelineGraph.nodes.at(-1).type, 'report')
})
