import { writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import * as THREE from 'three'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'

// Node does not expose FileReader, while Three's GLTFExporter uses it to
// assemble the final binary blob. This small standards-compatible adapter is
// enough for geometry-only assets and keeps generation deterministic.
globalThis.FileReader ??= class FileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((result) => {
      this.result = result
      this.onloadend?.({ target: this })
    })
  }

  readAsDataURL(blob) {
    blob.arrayBuffer().then((result) => {
      this.result = `data:${blob.type};base64,${Buffer.from(result).toString('base64')}`
      this.onloadend?.({ target: this })
    })
  }
}

const scriptDir = dirname(fileURLToPath(import.meta.url))
const outputDir = resolve(scriptDir, '../public/models')
const TAU = Math.PI * 2

const material = (name, color, metalness = 0.58, roughness = 0.46) => {
  const value = new THREE.MeshStandardMaterial({ color, metalness, roughness })
  value.name = name
  return value
}

const steel = material('painted_steel', 0x5e6a70, 0.7, 0.38)
const darkSteel = material('structural_steel', 0x313b40, 0.76, 0.4)
const warmSteel = material('furnace_shell', 0x6f5145, 0.62, 0.48)
const silver = material('stainless_steel', 0x9aa5a9, 0.82, 0.25)
const blue = material('process_blue', 0x356d84, 0.62, 0.4)
const orange = material('safety_orange', 0xd6792d, 0.48, 0.44)
const yellow = material('safety_yellow', 0xd5ad35, 0.45, 0.46)
const concrete = material('concrete', 0x6e7272, 0.05, 0.9)
const black = material('rubber_dark', 0x202529, 0.35, 0.78)

function mesh(group, geometry, sourceMaterial, name, position = [0, 0, 0], rotation = [0, 0, 0]) {
  const value = new THREE.Mesh(geometry, sourceMaterial)
  value.name = name
  value.position.set(...position)
  value.rotation.set(...rotation)
  value.castShadow = true
  value.receiveShadow = true
  group.add(value)
  return value
}

function box(group, size, position, sourceMaterial = darkSteel, name = 'structure') {
  return mesh(group, new THREE.BoxGeometry(...size), sourceMaterial, name, position)
}

function cylinder(group, radiusTop, radiusBottom, height, position, sourceMaterial = steel, name = 'vessel', segments = 32) {
  return mesh(group, new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments), sourceMaterial, name, position)
}

function ring(group, majorRadius, tubeRadius, position, sourceMaterial = darkSteel, name = 'ring') {
  return mesh(group, new THREE.TorusGeometry(majorRadius, tubeRadius, 8, 40), sourceMaterial, name, position, [Math.PI / 2, 0, 0])
}

function sphere(group, radius, position, sourceMaterial = steel, name = 'dome', scale = [1, 1, 1]) {
  const value = mesh(group, new THREE.SphereGeometry(radius, 24, 14), sourceMaterial, name, position)
  value.scale.set(...scale)
  return value
}

function pipeSegment(group, start, end, radius = 0.18, sourceMaterial = blue, name = 'pipe') {
  const from = new THREE.Vector3(...start)
  const to = new THREE.Vector3(...end)
  const direction = to.clone().sub(from)
  const value = mesh(group, new THREE.CylinderGeometry(radius, radius, direction.length(), 14), sourceMaterial, name)
  value.position.copy(from.clone().add(to).multiplyScalar(0.5))
  value.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize())
  return value
}

function pipe(group, points, radius = 0.18, sourceMaterial = blue, name = 'process_pipe') {
  for (let index = 1; index < points.length; index += 1) {
    pipeSegment(group, points[index - 1], points[index], radius, sourceMaterial, `${name}_${index}`)
    if (index < points.length - 1) sphere(group, radius * 1.05, points[index], sourceMaterial, `${name}_elbow_${index}`)
  }
}

function beamFrame(group, center, width, depth, height, sourceMaterial = darkSteel, prefix = 'frame') {
  const [x, y, z] = center
  const beam = 0.18
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(group, [beam, height, beam], [x + sx * width / 2, y + height / 2, z + sz * depth / 2], sourceMaterial, `${prefix}_post`)
  for (const level of [y + 0.3, y + height * 0.5, y + height]) {
    box(group, [width + beam, beam, beam], [x, level, z - depth / 2], sourceMaterial, `${prefix}_beam`)
    box(group, [width + beam, beam, beam], [x, level, z + depth / 2], sourceMaterial, `${prefix}_beam`)
    box(group, [beam, beam, depth + beam], [x - width / 2, level, z], sourceMaterial, `${prefix}_beam`)
    box(group, [beam, beam, depth + beam], [x + width / 2, level, z], sourceMaterial, `${prefix}_beam`)
  }
}

function platform(group, radius, y, sourceMaterial = yellow, prefix = 'platform') {
  ring(group, radius, 0.14, [0, y, 0], sourceMaterial, `${prefix}_deck`)
  for (let angle = 0; angle < TAU; angle += Math.PI / 8) {
    const x = Math.cos(angle) * radius
    const z = Math.sin(angle) * radius
    box(group, [0.07, 1.05, 0.07], [x, y + 0.52, z], sourceMaterial, `${prefix}_rail_post`)
  }
  ring(group, radius, 0.055, [0, y + 1.02, 0], sourceMaterial, `${prefix}_handrail`)
}

function ladder(group, x, y0, y1, z, sourceMaterial = yellow, prefix = 'ladder') {
  pipeSegment(group, [x - 0.32, y0, z], [x - 0.32, y1, z], 0.055, sourceMaterial, `${prefix}_rail`)
  pipeSegment(group, [x + 0.32, y0, z], [x + 0.32, y1, z], 0.055, sourceMaterial, `${prefix}_rail`)
  for (let y = y0 + 0.25; y < y1; y += 0.42) pipeSegment(group, [x - 0.32, y, z], [x + 0.32, y, z], 0.045, sourceMaterial, `${prefix}_rung`)
}

function semantic(scene, id) {
  const group = new THREE.Group()
  group.name = id
  group.userData.semantic_node = id
  scene.add(group)
  return group
}

function addGround(group, width, depth) {
  box(group, [width, 0.34, depth], [0, -0.17, 0], concrete, 'reinforced_concrete_foundation')
}

function createBlastFurnace() {
  const scene = new THREE.Scene()
  scene.name = 'blast_furnace_cad'
  scene.userData = {
    asset_kind: 'original_reference_based_cad',
    reference_url: 'https://3dwarehouse.sketchup.com/model/0481c007-bad9-4ed1-a3a8-a478bc9e83fd/Blast-Furnace',
    author: 'ProcessPilot',
    license: 'ProcessPilot original project asset',
  }
  const furnace = semantic(scene, 'furnace_body')
  const burden = semantic(scene, 'burden_system')
  const blast = semantic(scene, 'hot_blast')
  const hearth = semantic(scene, 'hearth')

  addGround(hearth, 34, 26)
  cylinder(hearth, 4.15, 4.3, 3.0, [0, 1.5, 0], warmSteel, 'hearth_shell', 48)
  cylinder(furnace, 4.4, 4.15, 3.2, [0, 4.55, 0], warmSteel, 'bosh', 48)
  cylinder(furnace, 4.15, 4.4, 3.2, [0, 7.75, 0], warmSteel, 'belly', 48)
  cylinder(furnace, 2.6, 4.15, 9.2, [0, 13.95, 0], warmSteel, 'stack_shell', 48)
  cylinder(furnace, 2.45, 2.6, 2.2, [0, 19.65, 0], steel, 'throat', 40)
  for (const y of [3, 5.8, 8.9, 12.2, 15.5, 18.5]) ring(furnace, y < 9 ? 4.35 : 2.7 + (18.5 - y) * 0.16, 0.12, [0, y, 0], darkSteel, 'shell_stiffener')
  for (const y of [6.1, 11.2, 16.4]) platform(furnace, y === 6.1 ? 4.85 : 3.6, y, yellow, 'inspection_platform')
  ladder(furnace, 3.65, 6.2, 16.5, 0, yellow, 'furnace_ladder')

  cylinder(burden, 1.9, 2.4, 1.7, [0, 21.6, 0], steel, 'bell_hopper', 40)
  cylinder(burden, 1.45, 1.9, 1.9, [0, 23.35, 0], steel, 'charging_hopper', 40)
  cylinder(burden, 0.95, 1.45, 1.2, [0, 24.9, 0], darkSteel, 'top_receiver', 32)
  ring(burden, 2.35, 0.12, [0, 21.1, 0], yellow, 'top_service_platform')
  beamFrame(burden, [-7.5, 0, 0], 3.2, 4.1, 20.5, darkSteel, 'skip_tower')
  pipeSegment(burden, [-8.6, 1.1, 0], [-1.5, 22.1, 0], 0.24, darkSteel, 'skip_rail_left')
  pipeSegment(burden, [-7.7, 1.1, 0], [-0.6, 22.1, 0], 0.24, darkSteel, 'skip_rail_right')
  box(burden, [2.0, 1.1, 1.8], [-4.8, 11.1, 0], orange, 'skip_car')
  for (let angle = 0; angle < TAU; angle += Math.PI / 2) {
    const x = Math.cos(angle) * 1.8
    const z = Math.sin(angle) * 1.8
    pipe(burden, [[x, 23.7, z], [x * 1.45, 22.6, z * 1.45], [x * 2.5, 22.6, z * 2.5], [x * 3.2, 17.8, z * 3.2]], 0.38, darkSteel, 'top_gas_offtake')
  }

  ring(blast, 4.55, 0.34, [0, 4.2, 0], orange, 'bustle_main')
  for (let angle = 0; angle < TAU; angle += Math.PI / 6) {
    const x1 = Math.cos(angle) * 4.55
    const z1 = Math.sin(angle) * 4.55
    const x2 = Math.cos(angle) * 3.75
    const z2 = Math.sin(angle) * 3.75
    pipeSegment(blast, [x1, 4.2, z1], [x2, 3.3, z2], 0.16, orange, 'tuyere_stock')
  }
  for (const [index, x] of [8.2, 12.0, 15.8].entries()) {
    cylinder(blast, 1.55, 1.72, 11.4, [x, 5.7, -2.4], steel, `hot_blast_stove_${index + 1}`, 36)
    sphere(blast, 1.55, [x, 11.4, -2.4], steel, `stove_dome_${index + 1}`, [1, 0.72, 1])
    ring(blast, 1.73, 0.11, [x, 1.1, -2.4], darkSteel, 'stove_base_ring')
    ladder(blast, x + 1.62, 1.0, 10.9, -2.4, yellow, 'stove_ladder')
  }
  pipe(blast, [[15.8, 11.6, -2.4], [15.8, 14.2, -2.4], [8.2, 14.2, -2.4], [8.2, 12.0, -2.4]], 0.42, blue, 'stove_header')
  pipe(blast, [[8.2, 2.2, -2.4], [5.8, 2.2, -2.4], [5.8, 4.2, 0], [4.5, 4.2, 0]], 0.46, orange, 'hot_blast_main')

  cylinder(hearth, 2.3, 2.7, 6.7, [-10.5, 3.35, 7], darkSteel, 'dust_catcher', 36)
  cylinder(hearth, 0.9, 2.3, 2.3, [-10.5, 7.85, 7], darkSteel, 'dust_catcher_cone', 36)
  pipe(hearth, [[-10.5, 9, 7], [-10.5, 15.2, 7], [-4.5, 15.2, 7], [-3.8, 17.8, 3.8]], 0.52, darkSteel, 'gas_cleaning_main')
  beamFrame(hearth, [0, 0, 7.4], 12, 7.2, 5.4, darkSteel, 'cast_house')
  box(hearth, [13, 0.24, 7.7], [0, 5.4, 7.4], steel, 'cast_house_roof')
  pipe(hearth, [[0, 1.2, 3.9], [0, 0.55, 6.4], [4.8, 0.55, 9.2]], 0.25, orange, 'iron_runner')
  for (const z of [8.5, 10.2]) box(hearth, [18, 0.13, 0.13], [0, 0.08, z], darkSteel, 'torpedo_rail')

  return scene
}

function createDebutanizer() {
  const scene = new THREE.Scene()
  scene.name = 'debutanizer_column_cad'
  scene.userData = {
    asset_kind: 'original_reference_based_cad',
    reference_url: 'https://sketchfab.com/3d-models/cellier-blumenthal-distillation-column-623d365bf31b4d139d7cc5a8cdc37f7d',
    author: 'ProcessPilot',
    license: 'ProcessPilot original project asset',
  }
  const shell = semantic(scene, 'column_shell')
  const condenser = semantic(scene, 'condenser')
  const reflux = semantic(scene, 'reflux_drum')
  const reboiler = semantic(scene, 'reboiler')
  const feed = semantic(scene, 'feed_line')

  addGround(feed, 28, 21)
  cylinder(shell, 2.15, 2.15, 22, [0, 12.6, 0], silver, 'fractionation_column_shell', 48)
  sphere(shell, 2.15, [0, 23.55, 0], silver, 'column_top_head', [1, 0.45, 1])
  sphere(shell, 2.15, [0, 1.65, 0], silver, 'column_bottom_head', [1, 0.45, 1])
  cylinder(shell, 1.75, 1.75, 1.8, [0, 0.7, 0], darkSteel, 'support_skirt', 40)
  for (let y = 3; y <= 22; y += 1.65) ring(shell, 2.18, 0.075, [0, y, 0], darkSteel, 'tray_stiffener')
  for (const y of [5.2, 10.2, 15.2, 20.2]) platform(shell, 2.72, y, yellow, 'tray_access_platform')
  ladder(shell, 2.35, 1.0, 23.3, 0, yellow, 'column_ladder')
  for (const y of [4.2, 8.5, 12.8, 17.1, 21.4]) {
    pipeSegment(shell, [2.05, y, 0], [2.7, y, 0], 0.14, blue, 'instrument_nozzle')
    cylinder(shell, 0.21, 0.21, 0.22, [2.84, y, 0], blue, 'instrument_flange', 16).rotation.z = Math.PI / 2
  }

  const condenserBody = cylinder(condenser, 1.25, 1.25, 6.4, [7.1, 21.2, -1.8], blue, 'overhead_condenser_shell', 36)
  condenserBody.rotation.z = Math.PI / 2
  for (const x of [4.3, 9.9]) {
    const head = cylinder(condenser, 1.34, 1.34, 0.38, [x, 21.2, -1.8], darkSteel, 'condenser_channel_head', 32)
    head.rotation.z = Math.PI / 2
  }
  for (const x of [5.3, 8.9]) box(condenser, [0.55, 2.6, 1.5], [x, 19.6, -1.8], darkSteel, 'condenser_saddle')
  pipe(condenser, [[0, 24.0, 0], [0, 25.3, 0], [7.1, 25.3, 0], [7.1, 22.45, -1.8]], 0.3, blue, 'overhead_vapour_line')
  pipe(condenser, [[10.3, 21.2, -1.8], [11.5, 21.2, -1.8], [11.5, 17.3, -1.8]], 0.24, blue, 'condensate_line')

  const drum = cylinder(reflux, 1.35, 1.35, 5.2, [8.9, 15.6, -1.8], steel, 'reflux_accumulator', 36)
  drum.rotation.z = Math.PI / 2
  for (const x of [7.2, 10.6]) box(reflux, [0.55, 2.0, 1.4], [x, 14.15, -1.8], darkSteel, 'drum_saddle')
  pipe(reflux, [[8.9, 14.25, -1.8], [8.9, 11.8, -1.8], [4.0, 11.8, -1.8], [4.0, 18.4, 0], [2.1, 18.4, 0]], 0.22, blue, 'reflux_return')
  for (const x of [7.6, 10.2]) {
    cylinder(reflux, 0.58, 0.58, 0.68, [x, 1.0, -5.8], blue, 'reflux_pump_motor', 24)
    cylinder(reflux, 0.74, 0.74, 0.45, [x, 0.48, -5.8], darkSteel, 'reflux_pump_case', 24)
    pipe(reflux, [[x, 1.3, -5.8], [x, 5.0, -5.8], [8.9, 5.0, -1.8], [8.9, 14.25, -1.8]], 0.14, blue, 'pump_suction')
  }

  const kettle = cylinder(reboiler, 1.2, 1.2, 6.5, [-6.3, 5.2, 0.8], orange, 'kettle_reboiler', 36)
  kettle.rotation.z = Math.PI / 2
  for (const x of [-8.5, -4.1]) box(reboiler, [0.6, 2.3, 1.5], [x, 3.8, 0.8], darkSteel, 'reboiler_saddle')
  pipe(reboiler, [[-3.05, 5.2, 0.8], [-2.45, 5.2, 0.8], [-2.45, 3.4, 0], [-2.1, 3.4, 0]], 0.32, orange, 'bottoms_to_reboiler')
  pipe(reboiler, [[-6.3, 6.4, 0.8], [-6.3, 9.0, 0.8], [-2.1, 9.0, 0]], 0.28, orange, 'vapour_return')
  pipe(reboiler, [[-9.55, 5.2, 0.8], [-11.0, 5.2, 0.8], [-11.0, 1.2, 0.8]], 0.18, orange, 'steam_supply')

  beamFrame(feed, [-8.0, 0, -6.5], 7.5, 3.0, 9.0, darkSteel, 'pipe_rack')
  pipe(feed, [[-12.0, 7.7, -6.0], [-4.0, 7.7, -6.0], [-4.0, 12.6, 0], [-2.1, 12.6, 0]], 0.27, blue, 'feed_main')
  pipe(feed, [[-12.0, 6.8, -6.8], [-2.0, 6.8, -6.8], [-2.0, 2.2, 0]], 0.18, blue, 'utility_header')
  for (const x of [-10, -7.6, -5.2]) {
    cylinder(feed, 0.48, 0.48, 0.32, [x, 7.7, -6], yellow, 'feed_valve', 16).rotation.z = Math.PI / 2
    mesh(feed, new THREE.TorusGeometry(0.42, 0.055, 8, 20), yellow, 'valve_handwheel', [x, 8.35, -6], [Math.PI / 2, 0, 0])
  }

  return scene
}

async function exportScene(scene, filename) {
  const exporter = new GLTFExporter()
  const result = await exporter.parseAsync(scene, { binary: true, onlyVisible: true })
  const output = resolve(outputDir, filename)
  await writeFile(output, Buffer.from(result))
  console.log(`${filename}: ${result.byteLength.toLocaleString()} bytes`)
}

await exportScene(createBlastFurnace(), 'blast_furnace.glb')
await exportScene(createDebutanizer(), 'debutanizer_column.glb')
