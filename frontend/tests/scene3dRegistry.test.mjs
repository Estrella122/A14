import assert from 'node:assert/strict'
import test from 'node:test'

import { buildScene3DState, getScene3DDescriptor, UNKNOWN_SCENE_3D } from '../src/data/scene3dRegistry.js'

test('five requested scene cases resolve from detected data scene', () => {
  for (const id of ['debutanizer_column', 'thermal_power_boiler_long_tail', 'industrial_dryer', 'blast_furnace']) {
    const state = buildScene3DState({ project_scene: { id: 'debutanizer_column' }, data_scene: { id } })
    assert.equal(state.descriptor.id, id)
    assert.equal(state.isKnown, true)
    assert.ok(state.descriptor.nodes.length >= 3)
    assert.ok(state.descriptor.flows.length >= 2)
  }
  const unknown = buildScene3DState({ project_scene: { id: 'debutanizer_column' }, data_scene: { id: 'new_industrial_scene' } })
  assert.equal(unknown.descriptor, UNKNOWN_SCENE_3D)
  assert.equal(unknown.isKnown, false)
})

test('boiler and debutanizer have independent semantic node bindings', () => {
  const boiler = getScene3DDescriptor('thermal_power_boiler_long_tail')
  const column = getScene3DDescriptor('debutanizer_column')
  assert.ok(boiler.nodes.some((node) => node.fields.includes('secondary_fan_outlet_flow')))
  assert.ok(column.nodes.some((node) => node.fields.includes('bottom_butane_content')))
  assert.equal(boiler.nodes.some((node) => node.fields.includes('bottom_butane_content')), false)
})

test('registry uses the existing 3D runtime for every scene', () => {
  for (const id of ['debutanizer_column', 'thermal_power_boiler_long_tail', 'industrial_dryer', 'blast_furnace', 'steel_industry_energy', 'vapor_pressure_soft_sensor']) {
    assert.equal(getScene3DDescriptor(id).engine, 'dom-css3d')
  }
})
