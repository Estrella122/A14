import assert from 'node:assert/strict'
import test from 'node:test'

import { buildSceneState, sceneFromRun } from '../src/composables/useSceneBinding.js'

const project = { scenarioId: 'debutanizer_column', scene: '脱丁烷塔' }

function runFor(id, name, status = 'confirmed') {
  return {
    runtime_trace: { final_scene: id, scene_status: status, scene_confidence: 0.948 },
    results: { standardization: { scenario: { scenario_id: id, display_name: name } } },
  }
}

test('xinan data remains independent from the project scene', () => {
  const state = buildSceneState(project, runFor('thermal_power_boiler_long_tail', '热电锅炉长尾数据'))
  assert.equal(state.project_scene.id, 'debutanizer_column')
  assert.equal(state.data_scene.id, 'thermal_power_boiler_long_tail')
  assert.equal(state.data_scene.display_name, '热电锅炉长尾数据')
  assert.equal(state.is_mismatch, true)
  assert.match(state.mismatch_text, /两者独立，不影响本次分析/)
})

test('vapor pressure scene replaces the prior run data scene', () => {
  const state = buildSceneState(project, runFor('vapor_pressure_soft_sensor', '蒸气压力软测量', 'uncertain'))
  assert.equal(state.data_scene.id, 'vapor_pressure_soft_sensor')
  assert.equal(state.data_scene.status_label, '候选场景')
  assert.equal(state.is_mismatch, true)
})

test('matching debutanizer data reports no mismatch', () => {
  const state = buildSceneState(project, runFor('debutanizer_column', '脱丁烷塔'))
  assert.equal(state.is_mismatch, false)
})

test('scene priority prefers final over selected and standardization', () => {
  const run = runFor('thermal_power_boiler_long_tail', '热电锅炉长尾数据')
  run.runtime_trace.selected_scene = 'debutanizer_column'
  run.results.standardization.scenario.scenario_id = 'vapor_pressure_soft_sensor'
  assert.equal(sceneFromRun(run).id, 'thermal_power_boiler_long_tail')
})
