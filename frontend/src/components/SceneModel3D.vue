<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { buildScene3DState } from '../data/scene3dRegistry'

const props = defineProps({
  sceneState: { type: Object, required: true },
  latestRun: { type: Object, default: null },
})

const scene3d = computed(() => buildScene3DState(props.sceneState))
const scene = computed(() => scene3d.value.descriptor)
const rotationX = ref(-6)
const rotationY = ref(-12)
const zoom = ref(1)
const autoRotate = ref(false)
const dragging = ref(false)
const selectedNodeId = ref(null)
const lastPointer = { x: 0, y: 0 }
let frameId
let lastFrame = 0

const modelStyle = computed(() => ({
  '--rx': `${rotationX.value}deg`, '--ry': `${rotationY.value}deg`, '--zoom': zoom.value,
  '--scene-accent': scene.value.accent, '--scene-ambient': scene.value.ambient,
}))
const previewRow = computed(() => props.latestRun?.results?.standardization?.preview?.at(-1) ?? {})
const fieldMetadata = computed(() => Object.fromEntries(
  (props.latestRun?.results?.standardization?.mapping?.mappings ?? [])
    .filter((item) => item.standard)
    .map((item) => [item.standard, item]),
))
const nodeRows = computed(() => scene.value.nodes.map((node) => {
  const field = node.fields.find((name) => previewRow.value[name] !== undefined && previewRow.value[name] !== null)
  const metadata = fieldMetadata.value[field] ?? {}
  const rawValue = field ? previewRow.value[field] : null
  return { ...node, field, rawValue, displayName: metadata.display_name || field || '暂无实时字段', unit: metadata.expected_unit || metadata.detected_unit || '', live: Number.isFinite(Number(rawValue)) }
}))
const nodesById = computed(() => Object.fromEntries(nodeRows.value.map((node) => [node.id, node])))
const flowRows = computed(() => scene.value.flows.map(([from, to]) => {
  const a = nodesById.value[from]
  const b = nodesById.value[to]
  if (!a || !b) return null
  const dx = b.x - a.x
  const dy = b.y - a.y
  return { from, to, x: a.x, y: a.y, width: Math.hypot(dx, dy), angle: Math.atan2(dy, dx) * 180 / Math.PI, live: a.live || b.live }
}).filter(Boolean))
const selectedNode = computed(() => nodesById.value[selectedNodeId.value] ?? nodeRows.value[0] ?? null)

function animate(time) {
  if (autoRotate.value && !dragging.value && time - lastFrame > 32) {
    rotationY.value = (rotationY.value + 0.08) % 360
    lastFrame = time
  }
  frameId = window.requestAnimationFrame(animate)
}
function pointerDown(event) {
  if (event.target.closest('.semantic-node')) return
  dragging.value = true
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
  event.currentTarget.setPointerCapture(event.pointerId)
}
function pointerMove(event) {
  if (!dragging.value) return
  rotationY.value += (event.clientX - lastPointer.x) * 0.3
  rotationX.value = Math.max(-24, Math.min(16, rotationX.value - (event.clientY - lastPointer.y) * 0.18))
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
}
function pointerUp() { dragging.value = false }
function onWheel(event) { zoom.value = Math.max(0.72, Math.min(1.5, zoom.value - event.deltaY * 0.001)) }
function resetView() { rotationX.value = -6; rotationY.value = -12; zoom.value = 1 }
function formatValue(node) {
  if (!node?.live) return '等待测点'
  const value = Number(node.rawValue)
  return `${Math.abs(value) >= 1000 ? value.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) : value.toFixed(2)}${node.unit ? ` ${node.unit}` : ''}`
}

watch(() => scene.value.id, () => { selectedNodeId.value = scene.value.nodes[0]?.id ?? null; resetView() }, { immediate: true })
onMounted(() => { frameId = window.requestAnimationFrame(animate) })
onBeforeUnmount(() => { if (frameId) window.cancelAnimationFrame(frameId) })
</script>

<template>
  <section class="scene-viewport" :style="modelStyle">
    <header class="scene-toolbar">
      <div><span class="scene-live-dot"></span><strong>{{ scene.code }}</strong><small>{{ scene.label }}</small></div>
      <div class="scene-actions">
        <button type="button" :class="{ active: autoRotate }" @click="autoRotate = !autoRotate"><AppIcon :name="autoRotate ? 'pause' : 'play'" :size="14" />{{ autoRotate ? '暂停' : '旋转' }}</button>
        <button type="button" @click="zoom = Math.min(1.5, zoom + .12)" aria-label="放大场景">+</button>
        <button type="button" @click="zoom = Math.max(.72, zoom - .12)" aria-label="缩小场景">−</button>
        <button type="button" @click="resetView">复位</button>
      </div>
    </header>

    <div class="scene-stage" :class="[{ dragging, unknown: !scene3d.isKnown }, `model-${scene.id}`]" role="application"
      :aria-label="`${scene.label}可交互三维结构`" @pointerdown="pointerDown" @pointermove="pointerMove"
      @pointerup="pointerUp" @pointercancel="pointerUp" @wheel.prevent="onWheel">
      <div class="scene-glow"></div><div class="scene-grid-floor"></div>
      <div v-if="!scene3d.isKnown" class="unknown-state"><AppIcon name="cube" :size="34" /><strong>未找到场景模型</strong><span>{{ scene3d.requestedId || '等待数据场景识别' }}</span></div>

      <div v-else class="model-rig">
        <div class="flow-layer" aria-hidden="true">
          <i v-for="flow in flowRows" :key="`${flow.from}-${flow.to}`" :class="{ live: flow.live }"
            :style="{ left: `${flow.x}%`, top: `${flow.y}%`, width: `${flow.width}%`, transform: `rotate(${flow.angle}deg)` }"></i>
        </div>
        <button v-for="node in nodeRows" :key="node.id" type="button" class="semantic-node"
          :class="[`shape-${node.shape}`, { live: node.live, selected: selectedNodeId === node.id }]"
          :style="{ left: `${node.x}%`, top: `${node.y}%` }" @click.stop="selectedNodeId = node.id">
          <span class="equipment-body"><i></i><i></i><i></i></span>
          <span class="node-label"><strong>{{ node.label }}</strong><small>{{ node.module }}</small></span>
        </button>
      </div>

      <aside v-if="selectedNode" class="node-inspector">
        <span>{{ selectedNode.module }}</span><strong>{{ selectedNode.label }}</strong>
        <div><small>{{ selectedNode.displayName }}</small><b>{{ formatValue(selectedNode) }}</b></div>
        <em>{{ selectedNode.fields.join(' · ') }}</em>
      </aside>
      <div class="scene-instruction"><AppIcon name="cube" :size="14" /><span>拖动旋转 · 滚轮缩放 · 点击设备查看测点</span></div>
    </div>
  </section>
</template>

<style scoped>
.scene-viewport{position:relative;min-width:0;overflow:hidden;color:#dce8f4;border:1px solid rgba(125,154,184,.22);border-radius:14px;background:#091522;box-shadow:0 22px 60px rgba(14,35,55,.16)}
.scene-toolbar{position:relative;z-index:8;display:flex;justify-content:space-between;align-items:center;min-height:56px;padding:0 17px;border-bottom:1px solid rgba(149,175,202,.14);background:rgba(11,23,36,.9);backdrop-filter:blur(12px)}
.scene-toolbar>div:first-child{display:grid;grid-template-columns:8px auto 1fr;gap:8px;align-items:center}.scene-toolbar strong{color:#fff;font:650 11px "SFMono-Regular",Consolas,monospace;letter-spacing:.08em}.scene-toolbar small{color:#7890a7;font-size:10px}.scene-live-dot{width:7px;height:7px;border-radius:50%;background:var(--scene-accent);box-shadow:0 0 0 4px var(--scene-ambient)}
.scene-actions{display:flex;gap:5px}.scene-actions button{display:inline-flex;align-items:center;justify-content:center;gap:5px;min-width:30px;min-height:30px;padding:0 8px;color:#91a4b8;font-size:9px;border:1px solid rgba(139,164,190,.2);border-radius:6px;background:rgba(255,255,255,.03)}.scene-actions button:hover,.scene-actions button.active{color:#fff;background:rgba(255,255,255,.08)}
.scene-stage{position:relative;min-height:clamp(430px,55vw,630px);overflow:hidden;cursor:grab;touch-action:none;isolation:isolate;background:radial-gradient(circle at 50% 48%,var(--scene-ambient),transparent 31%),linear-gradient(180deg,#091522,#0b1a28)}.scene-stage.dragging{cursor:grabbing}.scene-stage::after{content:"";position:absolute;inset:0;z-index:-1;opacity:.13;background-image:radial-gradient(#dceaff .5px,transparent .7px);background-size:8px 8px;mask-image:linear-gradient(transparent,#000 32%,#000 76%,transparent)}
.scene-glow{position:absolute;left:50%;top:48%;width:48%;aspect-ratio:1;border-radius:50%;background:var(--scene-ambient);filter:blur(65px);transform:translate(-50%,-50%);animation:breathe 6s ease-in-out infinite}.scene-grid-floor{position:absolute;left:50%;bottom:-23%;width:130%;height:66%;opacity:.25;background-image:linear-gradient(rgba(114,147,177,.35) 1px,transparent 1px),linear-gradient(90deg,rgba(114,147,177,.35) 1px,transparent 1px);background-size:50px 50px;transform:translateX(-50%) perspective(430px) rotateX(62deg);mask-image:radial-gradient(ellipse,#000 18%,transparent 68%)}
.model-rig{position:absolute;inset:8% 6% 14%;z-index:2;transform-style:preserve-3d;transform:perspective(1100px) scale(var(--zoom)) rotateX(var(--rx)) rotateY(var(--ry));transition:transform 90ms linear}.flow-layer{position:absolute;inset:0}.flow-layer i{position:absolute;height:2px;overflow:hidden;background:rgba(123,156,184,.28);transform-origin:left center}.flow-layer i::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,var(--scene-accent),transparent);transform:translateX(-100%)}.flow-layer i.live::after{animation:flow 2.2s linear infinite}
.semantic-node{position:absolute;width:112px;height:112px;padding:0;color:inherit;border:0;background:none;transform:translate(-50%,-50%) translateZ(20px);transform-style:preserve-3d;cursor:pointer}.equipment-body{position:absolute;inset:13px 25px;border:1px solid rgba(208,227,241,.38);border-radius:9px;background:linear-gradient(110deg,#112b40,#55738a 48%,#18364b 72%);box-shadow:inset 8px 0 13px rgba(255,255,255,.07),inset -12px 0 16px rgba(0,0,0,.3),0 18px 22px rgba(0,0,0,.28);transition:180ms ease}.equipment-body i{position:absolute;left:12%;right:12%;height:2px;background:rgba(201,220,234,.28)}.equipment-body i:nth-child(1){top:25%}.equipment-body i:nth-child(2){top:50%}.equipment-body i:nth-child(3){top:75%}.node-label{position:absolute;left:50%;top:87%;display:grid;min-width:116px;padding:5px 7px;border:1px solid rgba(137,168,193,.16);border-radius:5px;background:rgba(5,17,28,.76);transform:translateX(-50%);backdrop-filter:blur(8px)}.node-label strong{font-size:9px}.node-label small{margin-top:2px;color:#7990a5;font-size:7px}.semantic-node:hover .equipment-body,.semantic-node.selected .equipment-body{border-color:var(--scene-accent);box-shadow:0 0 0 3px var(--scene-ambient),0 18px 28px rgba(0,0,0,.35)}.semantic-node.live::after{content:"";position:absolute;right:18px;top:10px;width:6px;height:6px;border-radius:50%;background:#63d8ae;box-shadow:0 0 10px #63d8ae}
.shape-column .equipment-body,.shape-stack .equipment-body,.shape-blast-furnace .equipment-body{inset:0 36px;border-radius:48% 48% 13px 13px}.shape-column{height:165px}.shape-blast-furnace .equipment-body{inset:8px 28px;clip-path:polygon(28% 0,72% 0,88% 36%,72% 82%,62% 100%,38% 100%,28% 82%,12% 36%)}.shape-exchanger .equipment-body,.shape-drum .equipment-body,.shape-dryer .equipment-body{inset:34px 5px;border-radius:50% / 30%}.shape-dryer{width:160px}.shape-fan .equipment-body{inset:24px;border-radius:50%}.shape-fan .equipment-body::after{content:"";position:absolute;inset:18%;border:6px dotted var(--scene-accent);border-radius:50%}.shape-hopper .equipment-body{clip-path:polygon(8% 10%,92% 10%,66% 92%,34% 92%)}.shape-conveyor .equipment-body{inset:45px 4px;border-radius:7px}.shape-heater .equipment-body,.shape-factory .equipment-body,.shape-substation .equipment-body,.shape-processor .equipment-body,.shape-sensor-array .equipment-body{inset:22px 14px}.shape-vessel .equipment-body,.shape-gauge .equipment-body{inset:25px;border-radius:50%}.shape-pipe .equipment-body{inset:49px 5px;border-radius:8px}
.node-inspector{position:absolute;right:16px;bottom:18px;z-index:7;display:grid;width:min(250px,42%);padding:13px 14px;border:1px solid rgba(148,180,205,.22);border-radius:9px;background:rgba(6,19,31,.86);backdrop-filter:blur(12px)}.node-inspector>span{color:var(--scene-accent);font-size:8px;letter-spacing:.08em;text-transform:uppercase}.node-inspector>strong{margin-top:4px;color:#f4f8fc;font-size:12px}.node-inspector div{display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:9px;padding-top:8px;border-top:1px solid rgba(150,176,198,.14)}.node-inspector small{color:#8297ab;font-size:8px}.node-inspector b{font:650 10px monospace}.node-inspector em{overflow:hidden;margin-top:5px;color:#60778c;font:7px monospace;text-overflow:ellipsis;white-space:nowrap}.scene-instruction{position:absolute;left:16px;bottom:18px;z-index:7;display:flex;gap:7px;align-items:center;color:#70879c;font-size:8px}.unknown-state{position:absolute;inset:0;display:grid;place-content:center;justify-items:center;gap:7px;color:#7890a5}.unknown-state strong{color:#dce7ef;font-size:14px}.unknown-state span{font:9px monospace}
@keyframes breathe{50%{opacity:.55;transform:translate(-50%,-50%) scale(1.08)}}@keyframes flow{to{transform:translateX(100%)}}
@media(max-width:760px){.scene-stage{min-height:500px}.model-rig{inset:10% 2% 20%}.semantic-node{transform:translate(-50%,-50%) scale(.78) translateZ(20px)}.node-inspector{right:12px;bottom:46px;width:calc(100% - 24px);max-width:none}.scene-instruction{left:12px;bottom:18px}.scene-toolbar small{display:none}}
@media(prefers-reduced-motion:reduce){.scene-glow,.flow-layer i::after{animation:none}.model-rig{transition:none}}
</style>
