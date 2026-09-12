import test from 'node:test'
import assert from 'node:assert/strict'

import { artifactChain, capabilityCards, dagNodes, executorHighlights } from '../src/utils/runtimeObservability.js'

test('case A exposes semantic capability reasons and score breakdown', () => {
  const capabilities = ['DATA_PROFILING', 'DATA_QUALITY_ANALYSIS', 'TREND_ANALYSIS', 'ANOMALY_DETECTION'].map((candidate) => ({
    candidate, selected: true, status: 'selected', final_score: .992, semantic_intent_score: .98,
    context_fit_score: .99, data_precondition_score: 1, scene_fit_score: .95,
    dependency_readiness_score: 1, lexical_recall_score: .2, reason: '语义目标与数据上下文满足',
  }))
  const cards = capabilityCards({ capabilities })
  assert.deepEqual(cards.map((item) => item.id), ['DATA_PROFILING', 'DATA_QUALITY_ANALYSIS', 'TREND_ANALYSIS', 'ANOMALY_DETECTION'])
  assert.ok(cards.every((item) => item.ui_status === 'selected' && item.reason && item.lexical_recall_score < item.semantic_intent_score))
})

test('case B shows deferred segmentation becoming success after cleaning', () => {
  const runtime = {
    execution_dag: { steps: [
      { id: 'cleaning', executor: 'cleaning', readiness_status: 'executable', produces_artifacts: ['CLEANED_TRAIN'] },
      { id: 'segmentation', executor: 'segmentation', readiness_status: 'deferred', dependencies: ['cleaning'],
        missing_artifacts: ['CLEANED_TRAIN'], requires_artifacts: ['CLEANED_TRAIN'], produces_artifacts: ['SELECTED_SEGMENTS'] },
    ] },
    executor_results: [{ executor: 'cleaning', status: 'success' }, { executor: 'segmentation', status: 'success', reason: '分段完成' }],
  }
  const segmentation = dagNodes(runtime)[1]
  assert.deepEqual(segmentation.lifecycle, ['deferred', 'success'])
  assert.deepEqual(segmentation.waiting, [{ artifact: 'CLEANED_TRAIN', producer: 'cleaning' }])
})

test('case C shows optimization waiting for modeling artifact', () => {
  const nodes = dagNodes({ execution_dag: { steps: [
    { id: 'modeling', executor: 'modeling', produces_artifacts: ['MODEL_ARTIFACT'] },
    { id: 'optimization', executor: 'optimization', readiness_status: 'deferred', missing_artifacts: ['MODEL_ARTIFACT'], requires_artifacts: ['MODEL_ARTIFACT'] },
  ] }, executor_results: [] })
  assert.deepEqual(nodes[1].waiting, [{ artifact: 'MODEL_ARTIFACT', producer: 'modeling' }])
  assert.equal(nodes[1].status, 'deferred')
})

test('case D keeps optimization partial and exposes feasibility metrics', () => {
  const result = { executor: 'optimization', status: 'partial', metrics: { candidate_count: 12,
    validation_scores: { r2: .9989545, coverage: .0104 }, test_score: { r2: .9981521 }, constraints: { min_coverage: .05 } } }
  const node = dagNodes({ execution_dag: { steps: [{ id: 'optimization', executor: 'optimization', readiness_status: 'deferred' }] }, executor_results: [result] })[0]
  assert.equal(node.status, 'partial')
  assert.deepEqual(executorHighlights(result).map((item) => item[0]), ['候选数', 'Validation R²', 'Test R²', '训练覆盖率', '最低覆盖率'])
})

test('case E separates missing contracts from artifact readiness', () => {
  const card = capabilityCards({ capabilities: [{ candidate: 'OPTIMIZATION', status: 'blocked', selected: false,
    artifact_readiness: { MODEL_ARTIFACT: true }, artifact_readiness_score: 1,
    missing_artifacts: [], missing_contract_fields: ['objective'], reason: '缺少显式执行合同' }] })[0]
  assert.equal(card.ui_status, 'blocked')
  assert.deepEqual(card.missing_artifacts, [])
  assert.deepEqual(card.missing_contract_fields, ['objective'])
})

test('artifact chain hides full hash by default while retaining provenance', () => {
  const row = artifactChain({ artifacts: [{ artifact_id: 'a1', artifact_type: 'MODEL_ARTIFACT', producer: 'modeling', run_id: 'r1', source_execution_id: 'e1', content_hash: 'a'.repeat(64), path: '/advanced/path' }] })[0]
  assert.equal(row.short_hash, `${'a'.repeat(12)}…`)
  assert.equal(row.producer_label, 'modeling Executor')
  assert.equal(row.source_execution_id, 'e1')
})
