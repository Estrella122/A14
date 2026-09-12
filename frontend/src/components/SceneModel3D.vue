<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  project: { type: Object, required: true },
  latestRun: { type: Object, default: null },
})

const sceneMeta = {
  blast_furnace: { code: 'BF—01', label: '高炉本体', accent: '#f28b54', ambient: 'rgba(242, 139, 84, .16)' },
  debutanizer_column: { code: 'DC—04', label: '脱丁烷精馏塔', accent: '#4f8fba', ambient: 'rgba(79, 143, 186, .16)' },
  industrial_dryer: { code: 'DR—03', label: '连续回转干燥器', accent: '#c99b55', ambient: 'rgba(201, 155, 85, .16)' },
}
const scene = computed(() => sceneMeta[props.project.scenarioId] ?? sceneMeta.blast_furnace)
const rotationX = ref(-7)
const rotationY = ref(-18)
const autoRotate = ref(true)
const dragging = ref(false)
const lastPointer = { x: 0, y: 0 }
let frameId
let lastFrame = 0

const modelStyle = computed(() => ({
  '--rx': `${rotationX.value}deg`,
  '--ry': `${rotationY.value}deg`,
  '--scene-accent': scene.value.accent,
  '--scene-ambient': scene.value.ambient,
}))
const points = Array.from({ length: 14 }, (_, index) => index)
const livePoint = computed(() => props.latestRun?.results?.cleaning?.timeseries_preview?.points?.at(-1) ?? null)
const liveMetrics = computed(() => [
  { label: props.project.mv, tag: props.project.mvTag, value: livePoint.value?.input, unit: props.project.mvUnit, className: 'input-pin' },
  { label: props.project.target, tag: props.project.targetTag, value: livePoint.value?.output, unit: props.project.targetUnit, className: 'output-pin' },
])

function animate(time) {
  if (autoRotate.value && !dragging.value && time - lastFrame > 32) {
    rotationY.value = (rotationY.value + .12) % 360
    lastFrame = time
  }
  frameId = window.requestAnimationFrame(animate)
}
function pointerDown(event) {
  dragging.value = true
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
  event.currentTarget.setPointerCapture(event.pointerId)
}
function pointerMove(event) {
  if (!dragging.value) return
  rotationY.value += (event.clientX - lastPointer.x) * .35
  rotationX.value = Math.max(-24, Math.min(16, rotationX.value - (event.clientY - lastPointer.y) * .2))
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
}
function pointerUp() { dragging.value = false }
function resetView() { rotationX.value = -7; rotationY.value = -18 }
function formatValue(item) {
  return Number.isFinite(Number(item.value)) ? `${Number(item.value).toFixed(2)} ${item.unit}` : '等待真实任务'
}

onMounted(() => { frameId = window.requestAnimationFrame(animate) })
onBeforeUnmount(() => window.cancelAnimationFrame(frameId))
</script>

<template>
  <section class="scene-viewport" :style="modelStyle">
    <header class="scene-toolbar">
      <div><span class="scene-live-dot"></span><strong>{{ scene.code }}</strong><small>{{ scene.label }}</small></div>
      <div class="scene-actions">
        <button type="button" :class="{ active: autoRotate }" @click="autoRotate = !autoRotate"><AppIcon :name="autoRotate ? 'pause' : 'play'" :size="14" />{{ autoRotate ? '暂停旋转' : '自动旋转' }}</button>
        <button type="button" @click="resetView">复位视角</button>
      </div>
    </header>

    <div
      class="scene-stage"
      :class="[{ dragging }, `is-${project.scenarioId}`]"
      role="img"
      :aria-label="`${scene.label}可交互三维结构示意`"
      @pointerdown="pointerDown"
      @pointermove="pointerMove"
      @pointerup="pointerUp"
      @pointercancel="pointerUp"
    >
      <div class="scene-glow"></div>
      <div class="scene-grid-floor"></div>
      <i v-for="point in points" :key="point" class="ambient-point" :style="{ '--point-index': point }"></i>

      <div class="model-rig">
        <div v-if="project.scenarioId === 'blast_furnace'" class="blast-model model-object">
          <div class="bf-feed"><i></i><i></i><i></i></div>
          <div class="bf-body"><span class="bf-band band-a"></span><span class="bf-band band-b"></span><span class="bf-band band-c"></span><span class="bf-window"></span></div>
          <div class="bf-top"></div><div class="bf-base"></div>
          <div class="bf-pipe pipe-left"></div><div class="bf-pipe pipe-right"></div>
          <div class="bf-rail"></div>
        </div>

        <div v-else-if="project.scenarioId === 'debutanizer_column'" class="column-model model-object">
          <div class="dc-shell"><i v-for="tray in 7" :key="tray" :style="{ '--tray': tray }"></i></div>
          <div class="dc-cap"></div><div class="dc-base"></div>
          <div class="dc-condenser"><span></span></div><div class="dc-reboiler"><span></span></div>
          <div class="dc-pipe pipe-top"></div><div class="dc-pipe pipe-return"></div><div class="dc-pipe pipe-feed"></div>
        </div>

        <div v-else class="dryer-model model-object">
          <div class="dryer-drum"><i v-for="ring in 5" :key="ring" :style="{ '--ring': ring }"></i><span></span></div>
          <div class="dryer-hopper"></div><div class="dryer-heater"><i></i><i></i><i></i></div>
          <div class="dryer-duct"></div><div class="dryer-outlet"></div>
          <div class="dryer-wheel wheel-a"></div><div class="dryer-wheel wheel-b"></div>
        </div>
      </div>

      <div v-for="item in liveMetrics" :key="item.tag" class="data-pin" :class="item.className">
        <span><i></i></span><div><small>{{ item.tag }}</small><strong>{{ formatValue(item) }}</strong><em>{{ item.label }}</em></div>
      </div>
      <div class="scene-instruction"><AppIcon name="cube" :size="15" /><span>拖动模型改变视角</span></div>
    </div>
  </section>
</template>

<style scoped>
.scene-viewport { position: relative; min-width: 0; overflow: hidden; color: #dce8f4; border: 1px solid rgba(125,154,184,.22); border-radius: 14px; background: #0b1724; box-shadow: 0 22px 60px rgba(14,35,55,.16); }
.scene-toolbar { position: relative; z-index: 8; display: flex; justify-content: space-between; align-items: center; min-height: 56px; padding: 0 17px; border-bottom: 1px solid rgba(149,175,202,.14); background: rgba(11,23,36,.82); backdrop-filter: blur(12px); }
.scene-toolbar > div:first-child { display: grid; grid-template-columns: 8px auto 1fr; gap: 8px; align-items: center; }.scene-toolbar strong { color: #fff; font: 650 11px "SFMono-Regular", Consolas, monospace; letter-spacing: .08em; }.scene-toolbar small { color: #738aa1; font-size: 10px; }.scene-live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--scene-accent); box-shadow: 0 0 0 4px var(--scene-ambient); }
.scene-actions { display: flex; gap: 6px; }.scene-actions button { display: inline-flex; gap: 6px; align-items: center; min-height: 30px; padding: 0 9px; color: #91a4b8; font-size: 9px; border: 1px solid rgba(139,164,190,.18); border-radius: 6px; background: rgba(255,255,255,.025); transition: 180ms ease; }.scene-actions button:hover,.scene-actions button.active { color: #f4f8fc; border-color: rgba(177,199,220,.3); background: rgba(255,255,255,.07); }.scene-actions button:active { transform: scale(.97); }
.scene-stage { position: relative; min-height: clamp(410px, 55vw, 630px); overflow: hidden; cursor: grab; touch-action: none; isolation: isolate; background: radial-gradient(circle at 50% 48%, var(--scene-ambient), transparent 29%), linear-gradient(180deg, #0b1724, #0c1b2a); }.scene-stage.dragging { cursor: grabbing; }.scene-stage::after { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .18; background-image: radial-gradient(rgba(255,255,255,.8) .45px, transparent .6px); background-size: 7px 7px; mask-image: linear-gradient(to bottom, transparent, #000 30%, #000 70%, transparent); }
.scene-glow { position: absolute; left: 50%; top: 45%; width: 48%; aspect-ratio: 1; border-radius: 50%; background: var(--scene-ambient); filter: blur(65px); transform: translate(-50%,-50%); animation: breathe 6s ease-in-out infinite; }
.scene-grid-floor { position: absolute; left: 50%; bottom: -21%; width: 125%; height: 63%; opacity: .22; background-image: linear-gradient(rgba(114,147,177,.34) 1px, transparent 1px),linear-gradient(90deg,rgba(114,147,177,.34) 1px,transparent 1px); background-size: 54px 54px; transform: translateX(-50%) perspective(430px) rotateX(62deg); transform-origin: center bottom; mask-image: radial-gradient(ellipse, #000 20%, transparent 67%); }
.ambient-point { --angle: calc(var(--point-index) * 25.7deg); position: absolute; left: calc(50% + cos(var(--angle)) * 37%); top: calc(48% + sin(var(--angle)) * 32%); width: 2px; height: 2px; border-radius: 50%; background: var(--scene-accent); box-shadow: 0 0 8px var(--scene-accent); animation: blink calc(2.5s + var(--point-index) * .11s) ease-in-out infinite; }
.model-rig { position: absolute; inset: 7% 13% 8%; display: grid; place-items: center; perspective: 1100px; }.model-object { position: relative; width: min(55vw, 420px); height: min(50vw, 480px); transform-style: preserve-3d; transform: rotateX(var(--rx)) rotateY(var(--ry)); transition: transform 80ms linear; filter: drop-shadow(0 34px 28px rgba(0,0,0,.34)); }
.bf-body { position: absolute; left: 31%; top: 12%; width: 38%; height: 67%; clip-path: polygon(28% 0,72% 0,66% 15%,88% 39%,75% 82%,64% 100%,36% 100%,25% 82%,12% 39%,34% 15%); background: linear-gradient(90deg,#172b3d 0%,#49627a 42%,#273f54 67%,#102333 100%); border: 1px solid rgba(209,224,237,.22); box-shadow: inset 18px 0 20px rgba(255,255,255,.05), inset -22px 0 24px rgba(0,0,0,.35); transform: translateZ(28px); }.bf-top { position: absolute; left: 39%; top: 6%; width: 22%; height: 12%; border-radius: 48% 48% 12% 12%; background: linear-gradient(90deg,#13283b,#536c82 48%,#1b3347); transform: translateZ(31px); }.bf-base { position:absolute;left:35%;bottom:12%;width:30%;height:10%;border-radius:8px 8px 20px 20px;background:#102434;transform:translateZ(18px)}
.bf-band { position:absolute;left:13%;width:74%;height:6px;border:1px solid rgba(203,220,233,.3);border-radius:50%;background:#1d3548;box-shadow:0 5px 12px rgba(0,0,0,.28)}.band-a{top:25%}.band-b{top:49%}.band-c{top:72%}.bf-window { position:absolute;left:38%;top:75%;width:24%;height:12%;border-radius:45% 45% 8px 8px;background:radial-gradient(circle at 50% 100%,#ffd29b,#d76538 45%,rgba(198,72,38,.15) 75%);box-shadow:0 0 22px rgba(242,139,84,.62)}
.bf-feed { position:absolute;left:46%;top:0;width:8%;height:13%;background:#1b3346;transform:translateZ(22px)}.bf-feed i { position:absolute;left:50%;width:5px;height:5px;border-radius:50%;background:#d4a66c;animation:feed 2.4s linear infinite}.bf-feed i:nth-child(2){animation-delay:.8s}.bf-feed i:nth-child(3){animation-delay:1.6s}.bf-pipe { position:absolute;top:51%;width:26%;height:13%;border:9px solid #1d384d;border-bottom:0}.pipe-left{left:10%;border-right:0;border-radius:22px 0 0}.pipe-right{right:10%;border-left:0;border-radius:0 22px 0 0}.bf-rail{position:absolute;left:26%;bottom:8%;width:48%;height:4px;background:#20394d;box-shadow:0 13px 0 #20394d}
.column-model { height:min(53vw,500px) }.dc-shell { position:absolute;left:42%;top:9%;width:17%;height:73%;border:1px solid rgba(209,226,238,.3);border-radius:50% / 4%;background:linear-gradient(90deg,#102537,#4c687f 43%,#71889b 51%,#29475d 72%,#0c2030);box-shadow:inset 9px 0 15px rgba(255,255,255,.07),inset -15px 0 18px rgba(0,0,0,.36);transform:translateZ(35px)}.dc-shell i{position:absolute;left:5%;top:calc(var(--tray)*11%);width:90%;height:3px;border-radius:50%;background:rgba(203,220,233,.33);box-shadow:0 2px 6px rgba(0,0,0,.35)}.dc-cap,.dc-base{position:absolute;left:42%;width:17%;height:7%;border-radius:50%;background:linear-gradient(90deg,#142a3b,#607a8e 50%,#172f42);transform:translateZ(37px)}.dc-cap{top:6%}.dc-base{top:78%}.dc-condenser,.dc-reboiler{position:absolute;width:28%;height:12%;border:1px solid rgba(190,213,230,.25);border-radius:38px;background:linear-gradient(180deg,#385970,#172f42);box-shadow:inset 0 5px 8px rgba(255,255,255,.05)}.dc-condenser{right:5%;top:14%;transform:translateZ(-20px)}.dc-reboiler{right:5%;bottom:10%;transform:translateZ(4px)}.dc-condenser span,.dc-reboiler span{position:absolute;inset:28% 12%;border-top:2px solid #7193ad;border-bottom:2px solid #7193ad}.dc-pipe{position:absolute;border:7px solid #18364b}.pipe-top{left:50%;top:10%;width:30%;height:11%;border-bottom:0;border-left:0;border-radius:0 17px 0 0}.pipe-return{left:56%;top:22%;width:27%;height:18%;border-top:0;border-left:0;border-radius:0 0 17px}.pipe-feed{left:20%;top:46%;width:24%;height:7px;border-width:5px 0 0}.dc-pipe.pipe-feed{border-top:7px solid #18364b}
.dryer-model { width:min(61vw,520px);height:min(43vw,390px) }.dryer-drum { position:absolute;left:22%;top:25%;width:61%;height:38%;border:1px solid rgba(210,226,237,.25);border-radius:50% / 19%;background:linear-gradient(180deg,#49677d,#122b3e 48%,#081c2b);box-shadow:inset 0 13px 18px rgba(255,255,255,.06),inset 0 -18px 22px rgba(0,0,0,.28);transform:rotateZ(-5deg) translateZ(28px)}.dryer-drum::after{content:"";position:absolute;right:-2%;top:0;width:11%;height:100%;border-radius:50%;background:radial-gradient(ellipse at 42% 45%,#31556e,#0a1b29 63%);border:2px solid #527087}.dryer-drum i{position:absolute;left:calc(var(--ring)*15%);top:-2%;width:4px;height:104%;border-radius:50%;background:#5f7a8e;opacity:.62}.dryer-drum span{position:absolute;left:18%;top:27%;width:48%;height:5px;border-radius:50%;background:rgba(201,155,85,.5);box-shadow:0 0 18px rgba(201,155,85,.35)}.dryer-hopper{position:absolute;left:3%;top:6%;width:25%;height:31%;clip-path:polygon(8% 0,92% 0,70% 100%,30% 100%);background:linear-gradient(90deg,#142c3d,#466175,#152d3f);transform:translateZ(-14px)}.dryer-heater{position:absolute;left:1%;bottom:12%;width:24%;height:20%;border:1px solid #455f72;border-radius:8px;background:#112839}.dryer-heater i{position:absolute;top:25%;width:4px;height:50%;border-radius:3px;background:#d68d4d;box-shadow:0 0 10px rgba(214,141,77,.5)}.dryer-heater i:nth-child(1){left:28%}.dryer-heater i:nth-child(2){left:49%}.dryer-heater i:nth-child(3){left:70%}.dryer-duct{position:absolute;left:18%;top:52%;width:18%;height:10%;background:#163246;transform:translateZ(16px)}.dryer-outlet{position:absolute;right:0;top:45%;width:20%;height:12%;border:7px solid #163246;border-left:0;border-radius:0 20px 20px 0}.dryer-wheel{position:absolute;bottom:12%;width:10%;aspect-ratio:1;border:8px solid #162e40;border-radius:50%;background:#0c1d2b}.wheel-a{left:38%}.wheel-b{right:22%}
.data-pin { position:absolute;z-index:7;display:flex;gap:9px;align-items:center;pointer-events:none;animation:float 4s ease-in-out infinite}.data-pin>span{position:relative;width:34px;height:1px;background:rgba(173,199,220,.45)}.data-pin>span::after{content:"";position:absolute;right:0;top:-3px;width:7px;height:7px;border-radius:50%;background:var(--scene-accent);box-shadow:0 0 10px var(--scene-accent)}.data-pin div{display:grid;gap:2px;padding:8px 10px;border:1px solid rgba(149,177,202,.2);border-radius:7px;background:rgba(9,22,34,.76);backdrop-filter:blur(10px)}.data-pin small{color:#6f879e;font:8px monospace}.data-pin strong{color:#eef5fb;font:650 11px monospace}.data-pin em{color:#8499ad;font-size:8px;font-style:normal}.input-pin{left:6%;top:31%}.output-pin{right:6%;top:56%;flex-direction:row-reverse;animation-delay:-1.7s}.output-pin>span::after{left:0;right:auto}
.scene-instruction{position:absolute;left:50%;bottom:18px;z-index:7;display:flex;gap:7px;align-items:center;padding:7px 10px;color:#6f879d;font-size:9px;border:1px solid rgba(136,161,185,.13);border-radius:6px;background:rgba(8,20,31,.62);transform:translateX(-50%);pointer-events:none}
@keyframes breathe{50%{opacity:.55;transform:translate(-50%,-50%) scale(1.08)}}@keyframes blink{50%{opacity:.18;transform:scale(.65)}}@keyframes float{50%{transform:translateY(-7px)}}@keyframes feed{0%{top:0;opacity:0}20%{opacity:1}100%{top:88%;opacity:0}}
@media (max-width:760px){.scene-stage{min-height:440px}.model-rig{inset:12% 0 12%}.model-object{width:340px;height:400px}.dryer-model{width:390px;height:330px}.data-pin{transform:scale(.86)}.input-pin{left:3%;top:24%}.output-pin{right:3%;top:70%}.scene-toolbar small{display:none}}
@media (prefers-reduced-motion:reduce){.scene-glow,.ambient-point,.data-pin,.bf-feed i{animation:none}.model-object{transition:none}}
</style>
