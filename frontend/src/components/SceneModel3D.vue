<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import AppIcon from './AppIcon.vue'
import { buildScene3DState } from '../data/scene3dRegistry'

const modelCache = new Map()
const props = defineProps({ sceneState: { type: Object, required: true }, latestRun: { type: Object, default: null } })
const canvas = ref(null)
const viewport = ref(null)
const loadStatus = ref('idle')
const loadError = ref('')
const loadProgress = ref(0)
const selectedNodeId = ref(null)
const fallbackVisible = ref(false)
const scene3d = computed(() => buildScene3DState(props.sceneState))
const descriptor = computed(() => scene3d.value.descriptor)
const previewRow = computed(() => props.latestRun?.results?.standardization?.preview?.at(-1) ?? {})
const fieldMetadata = computed(() => Object.fromEntries((props.latestRun?.results?.standardization?.mapping?.mappings ?? []).filter((item) => item.standard).map((item) => [item.standard, item])))
const nodeRows = computed(() => descriptor.value.semantic_nodes.map((node) => {
  const values = node.fields.filter((field) => previewRow.value[field] !== undefined && previewRow.value[field] !== null).map((field) => ({ field, value: previewRow.value[field], metadata: fieldMetadata.value[field] ?? {} }))
  return { ...node, values, live: values.some((item) => Number.isFinite(Number(item.value))) }
}))
const selectedNode = computed(() => nodeRows.value.find((node) => node.id === selectedNodeId.value) ?? null)

let renderer
let threeScene
let camera
let controls
let currentModel
let resizeObserver
let frameId
let environmentTexture
let loadGeneration = 0
let semanticObjects = new Map()
let hoveredObject = null
let selectedObject = null
let pointerDownAt = null
let homeView = null
let cameraTween = null
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()
const clock = new THREE.Clock()

function cloneMaterial(material) {
  const cloned = material.clone()
  for (const key of Object.keys(cloned)) {
    if (cloned[key]?.isTexture) cloned[key] = cloned[key].clone()
  }
  return cloned
}
function cloneAsset(source) {
  const clone = source.clone(true)
  clone.traverse((object) => {
    if (!object.isMesh) return
    object.geometry = object.geometry.clone()
    object.material = Array.isArray(object.material) ? object.material.map(cloneMaterial) : cloneMaterial(object.material)
    object.castShadow = true
    object.receiveShadow = true
  })
  return clone
}
function disposeObject(root) {
  root?.traverse((object) => {
    if (!object.isMesh) return
    object.geometry?.dispose()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    for (const material of materials) {
      for (const value of Object.values(material || {})) if (value?.isTexture) value.dispose()
      material?.dispose()
    }
  })
}
function clearModel() {
  if (currentModel && threeScene) threeScene.remove(currentModel)
  disposeObject(currentModel)
  currentModel = null
  semanticObjects = new Map()
  selectedObject = null
  hoveredObject = null
}
function configureSemanticObjects() {
  semanticObjects = new Map()
  for (const node of descriptor.value.semantic_nodes) {
    const object = currentModel.getObjectByName(node.mesh_name)
    if (!object) continue
    object.userData.semanticNodeId = node.id
    object.traverse((child) => { child.userData.semanticNodeId = node.id })
    semanticObjects.set(node.id, object)
  }
  applyEquipmentPalette()
}
function eachMaterial(object, visit) {
  const seen = new Set()
  object?.traverse((child) => {
    if (!child.isMesh) return
    for (const material of (Array.isArray(child.material) ? child.material : [child.material])) {
      if (!material || seen.has(material)) continue
      seen.add(material)
      visit(material)
    }
  })
}
function applyEquipmentPalette() {
  for (const node of descriptor.value.semantic_nodes) {
    const object = semanticObjects.get(node.id)
    if (!object || !node.palette) continue
    const equipmentColor = new THREE.Color(node.palette.base)
    eachMaterial(object, (material) => {
      if (!material.color) return
      const original = material.color.clone()
      const hsl = {}; original.getHSL(hsl)
      const safetyColor = node.id !== 'maintenance_platform' && hsl.s > .62 && (hsl.h < .18 || hsl.h > .95)
      const color = equipmentColor.clone().lerp(original, safetyColor ? .58 : .14)
      color.multiplyScalar(safetyColor ? .78 : .9 + hsl.l * .18)
      material.color.copy(color)
      material.metalness = node.palette.metalness
      material.roughness = node.palette.roughness
      if (material.emissive) material.emissive.set(0x000000)
      material.emissiveIntensity = 0
      material.userData.runtimeBaseColor = material.color.getHex()
    })
  }
}
function resetRuntimeMaterials() {
  for (const object of semanticObjects.values()) eachMaterial(object, (material) => {
    if (material.userData.runtimeBaseColor !== undefined) material.color.setHex(material.userData.runtimeBaseColor)
    if (material.emissive) material.emissive.set(0x000000)
    material.emissiveIntensity = 0
  })
}
function applySelectionContrast() {
  if (!selectedNodeId.value) return
  for (const node of descriptor.value.semantic_nodes) {
    const object = semanticObjects.get(node.id)
    const isSelected = node.id === selectedNodeId.value
    const highlight = new THREE.Color(node.palette?.highlight || descriptor.value.accent)
    eachMaterial(object, (material) => {
      if (!material.color) return
      if (isSelected) {
        material.color.lerp(highlight, .52)
        if (material.emissive) material.emissive.copy(highlight)
        material.emissiveIntensity = .72
      } else {
        material.color.multiplyScalar(.28)
        material.emissiveIntensity *= .08
      }
    })
  }
}
function setCamera(config = descriptor.value.camera) {
  if (!camera || !controls) return
  camera.position.set(...config.position)
  controls.target.set(...config.target)
  controls.minDistance = config.minDistance
  controls.maxDistance = config.maxDistance
  controls.update()
}
function fitCameraToModel() {
  if (!currentModel || !camera || !controls) return
  const framingDetails = new Set(['maintenance_platform', 'process_piping', 'exhaust_outlet'])
  const coreObjects = [...semanticObjects.entries()].filter(([nodeId]) => !framingDetails.has(nodeId)).map(([, object]) => object)
  const box = new THREE.Box3()
  for (const object of coreObjects.length ? coreObjects : [currentModel]) box.expandByObject(object)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const maxSize = Math.max(size.x, size.y, size.z)
  const distance = (maxSize * .76) / Math.tan(THREE.MathUtils.degToRad(camera.fov * .5))
  // Match the source CAD's authored isometric viewpoint instead of looking
  // almost along the dryer drum axis.
  const direction = new THREE.Vector3(1, .48, 1).normalize()
  const position = center.clone().add(direction.multiplyScalar(distance))
  controls.target.copy(center)
  camera.position.copy(position)
  controls.minDistance = Math.max(2, maxSize * .14)
  controls.maxDistance = maxSize * 4
  camera.near = Math.max(.02, maxSize / 1000)
  camera.far = maxSize * 12
  camera.updateProjectionMatrix()
  controls.update()
  homeView = { position: position.clone(), target: center.clone(), minDistance: controls.minDistance, maxDistance: controls.maxDistance }
}
function focusNode(nodeId) {
  const object = semanticObjects.get(nodeId)
  if (!object || !camera || !controls) return
  selectedNodeId.value = nodeId
  selectedObject = object
  const box = new THREE.Box3().setFromObject(object)
  const center = box.getCenter(new THREE.Vector3())
  const dimensions = box.getSize(new THREE.Vector3())
  const size = Math.max(dimensions.x, dimensions.y, dimensions.z)
  const direction = camera.position.clone().sub(controls.target).normalize()
  animateCamera(center.clone().add(direction.multiplyScalar(Math.max(3.8, size * 1.45))), center)
}
function animateCamera(position, target, duration = 620) {
  cameraTween = {
    startedAt: performance.now(), duration,
    fromPosition: camera.position.clone(), fromTarget: controls.target.clone(),
    toPosition: position.clone(), toTarget: target.clone(),
  }
  controls.enabled = false
}
function updateCameraTween(now) {
  if (!cameraTween) return
  const linear = Math.min(1, (now - cameraTween.startedAt) / cameraTween.duration)
  const progress = 1 - Math.pow(1 - linear, 3)
  camera.position.lerpVectors(cameraTween.fromPosition, cameraTween.toPosition, progress)
  controls.target.lerpVectors(cameraTween.fromTarget, cameraTween.toTarget, progress)
  if (linear >= 1) { cameraTween = null; controls.enabled = true }
}
function resetCamera() {
  selectedNodeId.value = null
  selectedObject = null
  if (!homeView) { setCamera(); return }
  controls.minDistance = homeView.minDistance
  controls.maxDistance = homeView.maxDistance
  animateCamera(homeView.position, homeView.target)
}
function materialVisual(object, color, intensity) {
  object?.traverse((child) => {
    if (!child.isMesh) return
    const materials = Array.isArray(child.material) ? child.material : [child.material]
    for (const material of materials) {
      if (!material.emissive) continue
      material.emissive.set(color)
      material.emissiveIntensity = intensity
    }
  })
}
function dynamicValue(nodeId, field) {
  const node = nodeRows.value.find((item) => item.id === nodeId)
  const row = node?.values.find((item) => item.field === field)
  return Number.isFinite(Number(row?.value)) ? Number(row.value) : null
}
function applyDataDynamics(elapsed) {
  const heaterTemperature = dynamicValue('air_heater', 'hot_air_temperature')
  if (heaterTemperature !== null) materialVisual(semanticObjects.get('air_heater'), 0xff6b2e, .12 + Math.min(1, Math.abs(heaterTemperature) / 240) * .55)
  const exhaustTemperature = dynamicValue('exhaust_outlet', 'exhaust_temperature')
  if (exhaustTemperature !== null) materialVisual(semanticObjects.get('exhaust_outlet'), 0xff8a4c, .08 + Math.min(.5, Math.abs(exhaustTemperature) / 400))
  const airFlow = dynamicValue('supply_fan', 'drying_air_flow')
  if (airFlow !== null) {
    const speed = .15 + Math.min(2.2, Math.log10(Math.abs(airFlow) + 1) * .32)
    materialVisual(semanticObjects.get('supply_fan'), 0x4aa7dc, .08 + .12 * (1 + Math.sin(elapsed * speed * 2)))
    materialVisual(semanticObjects.get('process_piping'), descriptor.value.accent, .15 + .18 * (1 + Math.sin(elapsed * speed * 2)))
  }
  const drumSpeed = dynamicValue('dryer_drum', 'drum_speed')
  if (drumSpeed !== null) materialVisual(semanticObjects.get('dryer_drum'), 0x9c6b43, .05 + .08 * (1 + Math.sin(elapsed * Math.min(1.1, Math.abs(drumSpeed) * .03))))
  const productTemperature = dynamicValue('dryer_drum', 'product_temperature')
  if (productTemperature !== null) materialVisual(semanticObjects.get('dryer_drum'), 0xa94f24, Math.min(.25, Math.abs(productTemperature) / 600))
  if (hoveredObject) materialVisual(hoveredObject, 0x62c8ff, .65)
  if (selectedObject) materialVisual(selectedObject, descriptor.value.accent, .5)
}
function applyDistanceLod() {
  const lod = descriptor.value.lod
  if (!lod || lod.mode !== 'component_visibility' || !camera || !controls) return
  const detailObject = semanticObjects.get(lod.detail_node)
  if (detailObject) detailObject.visible = camera.position.distanceTo(controls.target) <= lod.hide_beyond
}
function renderLoop(now) {
  resetRuntimeMaterials()
  applyDataDynamics(clock.getElapsedTime())
  applySelectionContrast()
  applyDistanceLod()
  updateCameraTween(now)
  controls?.update()
  if (renderer && threeScene && camera) renderer.render(threeScene, camera)
  frameId = window.requestAnimationFrame(renderLoop)
}
function resize() {
  if (!renderer || !camera || !viewport.value) return
  const { clientWidth: width, clientHeight: height } = viewport.value
  renderer.setSize(width, height, false)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  camera.aspect = width / Math.max(height, 1)
  camera.updateProjectionMatrix()
}
function initRenderer() {
  threeScene = new THREE.Scene()
  threeScene.background = new THREE.Color(0x0d1921)
  threeScene.fog = new THREE.Fog(0x0d1921, 34, 76)
  camera = new THREE.PerspectiveCamera(42, 1, .1, 120)
  renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.28
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  const pmrem = new THREE.PMREMGenerator(renderer)
  environmentTexture = pmrem.fromScene(new RoomEnvironment(), .035).texture
  threeScene.environment = environmentTexture
  pmrem.dispose()
  controls = new OrbitControls(camera, canvas.value)
  controls.enableDamping = true
  controls.dampingFactor = .065
  controls.enablePan = true
  controls.screenSpacePanning = true
  const hemi = new THREE.HemisphereLight(0xb8d5e4, 0x242c30, 1.45)
  threeScene.add(hemi)
  const key = new THREE.DirectionalLight(0xfff2df, 3.1)
  key.position.set(-9, 16, 11)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -20, right: 20, top: 18, bottom: -18, far: 55 })
  key.shadow.bias = -.00025
  threeScene.add(key)
  const rim = new THREE.DirectionalLight(0x67a9d8, 1.35)
  rim.position.set(14, 8, -12)
  threeScene.add(rim)
  const grid = new THREE.GridHelper(40, 40, 0x31516b, 0x172c3d)
  grid.position.y = .01
  grid.material.opacity = .34
  grid.material.transparent = true
  threeScene.add(grid)
  setCamera()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(viewport.value)
  resize()
  clock.start()
  frameId = window.requestAnimationFrame(renderLoop)
}
async function loadModel() {
  const generation = ++loadGeneration
  clearModel()
  fallbackVisible.value = false
  selectedNodeId.value = null
  loadError.value = ''
  loadProgress.value = 0
  if (!scene3d.value.hasAsset) { loadStatus.value = 'missing_3d_asset'; return }
  loadStatus.value = 'loading'
  try {
    const url = descriptor.value.model_url
    const requestUrl = `${url}${url.includes('?') ? '&' : '?'}v=${descriptor.value.asset_version ?? 1}`
    if (!modelCache.has(requestUrl)) {
      const [{ GLTFLoader }, { DRACOLoader }, { MeshoptDecoder }] = await Promise.all([
        import('three/examples/jsm/loaders/GLTFLoader.js'),
        import('three/examples/jsm/loaders/DRACOLoader.js'),
        import('three/examples/jsm/libs/meshopt_decoder.module.js'),
      ])
      const loader = new GLTFLoader()
      const draco = new DRACOLoader()
      draco.setDecoderPath('/draco/')
      loader.setDRACOLoader(draco)
      loader.setMeshoptDecoder(MeshoptDecoder)
      const request = loader.loadAsync(requestUrl, (event) => { if (event.total) loadProgress.value = Math.round(event.loaded / event.total * 100) }).finally(() => draco.dispose())
      modelCache.set(requestUrl, request)
    }
    const gltf = await modelCache.get(requestUrl)
    if (generation !== loadGeneration) return
    currentModel = cloneAsset(gltf.scene)
    const transform = descriptor.value.transform
    currentModel.scale.setScalar(transform.scale)
    currentModel.position.set(...transform.position)
    currentModel.rotation.set(...transform.rotation)
    threeScene.add(currentModel)
    configureSemanticObjects()
    fitCameraToModel()
    loadStatus.value = 'ready'
  } catch (error) {
    if (generation !== loadGeneration) return
    loadError.value = error?.message || String(error)
    loadStatus.value = 'error'
  }
}
function pick(event, isClick = false) {
  if (!renderer || !camera || !currentModel) return
  const rect = canvas.value.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const hit = raycaster.intersectObject(currentModel, true).find((item) => item.object.userData.semanticNodeId)
  const nodeId = hit?.object?.userData?.semanticNodeId
  hoveredObject = nodeId ? semanticObjects.get(nodeId) : null
  canvas.value.style.cursor = nodeId ? 'pointer' : 'grab'
  if (isClick && nodeId) focusNode(nodeId)
}
function pointerDown(event) {
  if (cameraTween) { cameraTween = null; controls.enabled = true }
  pointerDownAt = { x: event.clientX, y: event.clientY }
}
function pointerUp(event) {
  if (!pointerDownAt) return
  if (Math.hypot(event.clientX - pointerDownAt.x, event.clientY - pointerDownAt.y) < 5) pick(event, true)
  pointerDownAt = null
}
function formatValue(item) {
  const value = Number(item.value)
  const unit = item.metadata.expected_unit || item.metadata.detected_unit || ''
  return `${Math.abs(value) >= 1000 ? value.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) : value.toFixed(2)}${unit ? ` ${unit}` : ''}`
}

defineExpose({ focusNode, resetCamera })

watch(() => descriptor.value.id, async () => { await nextTick(); if (renderer) loadModel() })
onMounted(async () => { initRenderer(); await loadModel() })
onBeforeUnmount(() => {
  loadGeneration += 1
  if (frameId) window.cancelAnimationFrame(frameId)
  resizeObserver?.disconnect()
  clearModel()
  controls?.dispose()
  environmentTexture?.dispose()
  renderer?.dispose()
  renderer?.forceContextLoss()
})
</script>

<template>
  <section class="scene-shell" :style="{ '--scene-accent': descriptor.accent }">
    <header class="scene-toolbar">
      <div><span class="live-dot"></span><strong>{{ descriptor.code }}</strong><small>{{ descriptor.label }}</small></div>
      <div class="toolbar-actions">
        <span class="asset-state" :class="loadStatus">{{ loadStatus === 'ready' ? 'GLB 已加载' : loadStatus === 'loading' ? `加载 ${loadProgress}%` : loadStatus }}</span>
        <button type="button" :disabled="loadStatus !== 'ready'" @click="resetCamera"><AppIcon name="target" :size="13" />复位相机</button>
      </div>
    </header>

    <div ref="viewport" class="webgl-viewport">
      <canvas ref="canvas" aria-label="工业设备 WebGL 三维场景" @pointermove="pick" @pointerdown="pointerDown" @pointerup="pointerUp" @pointerleave="hoveredObject = null"></canvas>
      <div v-if="loadStatus === 'loading'" class="state-overlay loading-state"><span class="loader"></span><strong>正在加载真实 GLB 设备模型</strong><small>{{ descriptor.model_url }} · {{ loadProgress }}%</small></div>
      <div v-else-if="loadStatus === 'missing_3d_asset'" class="state-overlay missing-state">
        <AppIcon name="cube" :size="35" /><span>missing_3d_asset</span>
        <strong>当前场景已识别为{{ descriptor.label }}，但真实 3D 模型资产尚未安装。</strong>
        <small>需要补充 {{ descriptor.required_asset || '对应场景 GLB/GLTF' }}</small>
        <button v-if="descriptor.semantic_nodes.length" type="button" @click="fallbackVisible = !fallbackVisible">{{ fallbackVisible ? '关闭简化示意图' : '使用简化示意图' }}</button>
      </div>
      <div v-else-if="loadStatus === 'error'" class="state-overlay error-state"><strong>真实 3D 模型加载失败</strong><small>{{ loadError }}</small><button type="button" @click="loadModel">重新加载</button></div>

      <div v-if="fallbackVisible && loadStatus === 'missing_3d_asset'" class="explicit-fallback"><strong>简化示意图 · 非真实 3D 模型</strong><div><button v-for="node in descriptor.semantic_nodes" :key="node.id" type="button">{{ node.label }}</button></div></div>

      <aside v-if="loadStatus === 'ready' && selectedNode" class="device-inspector">
        <span>{{ selectedNode.module }}</span><strong>{{ selectedNode.label }}</strong><small>{{ selectedNode.mesh_name }}</small>
        <p class="device-description">{{ selectedNode.description }}</p>
        <div v-if="selectedNode.values.length" class="measurement-list"><p v-for="item in selectedNode.values" :key="item.field"><span>{{ item.metadata.display_name || item.field }}</span><b>{{ formatValue(item) }}</b><code>{{ item.field }}</code></p></div>
        <p v-else class="no-measurement">当前快照没有与此设备绑定的可用值。</p>
        <em>状态：{{ selectedNode.live ? '实时数据已绑定' : '模型节点可用，等待数据' }}</em>
      </aside>
      <div v-if="loadStatus === 'ready'" class="controls-hint">左键旋转 · 滚轮缩放 · 右键平移 · 点击设备聚焦</div>
    </div>
  </section>
</template>

<style scoped>
.scene-shell{overflow:hidden;color:#dce8f4;border:1px solid rgba(125,154,184,.22);border-radius:14px;background:#07131f;box-shadow:0 22px 60px rgba(14,35,55,.18)}.scene-toolbar{position:relative;z-index:5;display:flex;align-items:center;justify-content:space-between;min-height:56px;padding:0 17px;border-bottom:1px solid rgba(149,175,202,.14);background:rgba(8,20,32,.94)}.scene-toolbar>div:first-child{display:grid;grid-template-columns:8px auto 1fr;gap:8px;align-items:center}.live-dot{width:7px;height:7px;border-radius:50%;background:var(--scene-accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--scene-accent) 18%,transparent)}.scene-toolbar strong{color:#fff;font:650 11px monospace;letter-spacing:.08em}.scene-toolbar small{color:#758ca2;font-size:10px}.toolbar-actions{display:flex;gap:8px;align-items:center}.asset-state{padding:5px 7px;color:#9aabba;font:8px monospace;border:1px solid rgba(142,169,193,.18);border-radius:5px}.asset-state.ready{color:#65d8af;border-color:rgba(101,216,175,.3)}.asset-state.error,.asset-state.missing_3d_asset{color:#f0aa68}.toolbar-actions button,.state-overlay button{display:inline-flex;gap:5px;align-items:center;min-height:30px;padding:0 10px;color:#d9e5ef;font-size:9px;border:1px solid rgba(145,174,198,.24);border-radius:6px;background:rgba(255,255,255,.05)}.toolbar-actions button:disabled{opacity:.4}.webgl-viewport{position:relative;min-height:clamp(500px,58vw,680px)}canvas{position:absolute;inset:0;width:100%;height:100%;outline:none}.state-overlay{position:absolute;inset:0;z-index:3;display:grid;place-content:center;justify-items:center;gap:9px;padding:30px;text-align:center;background:radial-gradient(circle at center,rgba(29,58,80,.72),rgba(7,19,31,.96) 58%)}.state-overlay>span{color:var(--scene-accent);font:9px monospace;letter-spacing:.1em}.state-overlay strong{max-width:540px;color:#eef5fa;font-size:15px;line-height:1.55}.state-overlay small{color:#72889b;font:9px monospace}.loader{width:26px;height:26px;border:2px solid rgba(255,255,255,.12);border-top-color:var(--scene-accent);border-radius:50%;animation:spin .8s linear infinite}.explicit-fallback{position:absolute;inset:76px 8% 62px;z-index:4;display:grid;align-content:center;gap:20px;padding:28px;border:1px dashed rgba(235,169,104,.35);border-radius:12px;background:rgba(8,20,31,.94);text-align:center}.explicit-fallback>strong{color:#e8a663;font-size:11px}.explicit-fallback>div{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}.explicit-fallback button{padding:9px 12px;color:#aabac8;font-size:9px;border:1px solid #2a4052;border-radius:6px;background:#102333}.device-inspector{position:absolute;top:18px;right:16px;z-index:3;display:grid;width:min(292px,45%);padding:14px;border:1px solid rgba(145,177,202,.25);border-radius:9px;background:rgba(5,17,28,.9);backdrop-filter:blur(14px)}.device-inspector>span{color:var(--scene-accent);font-size:8px}.device-inspector>strong{margin-top:4px;color:#fff;font-size:13px}.device-inspector>small{margin-top:2px;color:#597085;font:7px monospace}.device-description{margin:10px 0 0;color:#a9bac8;font-size:9px;line-height:1.65}.measurement-list{display:grid;gap:7px;margin-top:10px}.measurement-list p{display:grid;grid-template-columns:1fr auto;gap:2px 10px;margin:0;padding-top:7px;border-top:1px solid rgba(143,170,194,.14)}.measurement-list span{color:#879bad;font-size:8px}.measurement-list b{font:650 10px monospace}.measurement-list code{grid-column:1/-1;color:#597086;font-size:7px}.device-inspector em,.no-measurement{margin:8px 0 0;color:#748a9d;font-size:8px;font-style:normal}.controls-hint{position:absolute;left:16px;bottom:17px;z-index:2;color:#658096;font-size:8px;pointer-events:none}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:760px){.webgl-viewport{min-height:560px}.device-inspector{top:12px;right:12px;bottom:auto;width:calc(100% - 24px);max-width:none}.scene-toolbar small{display:none}.asset-state{display:none}}@media(prefers-reduced-motion:reduce){.loader{animation:none}}
</style>
