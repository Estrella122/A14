import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { buildScene3DState, getScene3DDescriptor, listMissingSceneAssets, UNKNOWN_SCENE_3D } from '../src/data/scene3dRegistry.js'

test('detected data scene selects the 3D descriptor independently from project scene', () => {
  for (const id of ['debutanizer_column', 'thermal_power_boiler_long_tail', 'industrial_dryer', 'blast_furnace']) {
    const state = buildScene3DState({ project_scene: { id: 'debutanizer_column' }, data_scene: { id } })
    assert.equal(state.descriptor.id, id)
    assert.equal(state.isKnown, true)
  }
  const unknown = buildScene3DState({ project_scene: { id: 'debutanizer_column' }, data_scene: { id: 'new_industrial_scene' } })
  assert.equal(unknown.descriptor, UNKNOWN_SCENE_3D)
  assert.equal(unknown.isKnown, false)
  assert.equal(unknown.status, 'missing_3d_asset')
})

test('industrial dryer uses an installed GLB with semantic mesh bindings and LOD', () => {
  const dryer = getScene3DDescriptor('industrial_dryer')
  assert.equal(dryer.engine, 'three-webgl')
  assert.equal(dryer.asset_status, 'installed')
  assert.match(dryer.model_url, /\.glb$/)
  assert.ok(dryer.semantic_nodes.length >= 5)
  assert.ok(dryer.semantic_nodes.every((node) => node.mesh_name && node.description && node.palette?.base && node.palette?.highlight && Array.isArray(node.fields)))
  assert.ok(dryer.semantic_nodes.some((node) => node.fields.includes('hot_air_temperature')))
  assert.ok(dryer.semantic_nodes.some((node) => node.fields.includes('drying_air_flow')))
  assert.equal(dryer.lod.mode, 'component_visibility')
  assert.equal(buildScene3DState({ data_scene: { id: 'industrial_dryer' } }).hasAsset, true)
  const projectPreview = buildScene3DState({ project_scene: { id: 'industrial_dryer' }, data_scene: { id: null } })
  assert.equal(projectPreview.descriptor.id, 'industrial_dryer')
  assert.equal(projectPreview.hasAsset, true)
  assert.equal(projectPreview.source, 'project_preview')
})

test('detected data scene overrides the project preview scene', () => {
  const state = buildScene3DState({
    project_scene: { id: 'industrial_dryer' },
    data_scene: { id: 'blast_furnace' },
  })
  assert.equal(state.descriptor.id, 'blast_furnace')
  assert.equal(state.source, 'data_scene')
})

test('boiler and debutanizer retain independent semantic field bindings', () => {
  const boiler = getScene3DDescriptor('thermal_power_boiler_long_tail')
  const column = getScene3DDescriptor('debutanizer_column')
  assert.ok(boiler.semantic_nodes.some((node) => node.fields.includes('secondary_fan_outlet_flow')))
  assert.ok(column.semantic_nodes.some((node) => node.fields.includes('bottom_butane_content')))
  assert.equal(boiler.semantic_nodes.some((node) => node.fields.includes('bottom_butane_content')), false)
})

test('scenes without installed models expose explicit missing asset contracts', () => {
  const missing = listMissingSceneAssets()
  assert.ok(missing.some((item) => item.scene_id === 'blast_furnace' && item.required_asset === 'blast_furnace.glb'))
  assert.ok(missing.some((item) => item.scene_id === 'thermal_power_boiler_long_tail'))
  assert.equal(buildScene3DState({ data_scene: { id: 'debutanizer_column' } }).hasAsset, false)
})

test('runtime source loads GLB and never constructs primitive equipment', async () => {
  const source = await readFile(new URL('../src/components/SceneModel3D.vue', import.meta.url), 'utf8')
  assert.match(source, /GLTFLoader/)
  assert.match(source, /OrbitControls/)
  assert.match(source, /DRACOLoader/)
  assert.match(source, /MeshoptDecoder/)
  assert.match(source, /disposeObject/)
  assert.match(source, /animateCamera/)
  assert.match(source, /selectedNode\.description/)
  assert.match(source, /applyEquipmentPalette/)
  assert.match(source, /applySelectionContrast/)
  assert.doesNotMatch(source, /(Box|Cylinder|Sphere|Capsule)Geometry/)
  assert.doesNotMatch(source, /dom-css3d|shape-/)
})
