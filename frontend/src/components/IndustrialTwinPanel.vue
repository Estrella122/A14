<script setup>
import { computed, ref, watch } from 'vue'
import StatusPill from './StatusPill.vue'
import { useEChart } from '../composables/useEChart'
import { sceneStateFromProject, sceneFromRun } from '../composables/useSceneBinding'
import { resolveScene3DView } from '../data/scene3dRegistry'

const props = defineProps({ project: { type: Object, required: true }, latestRun: { type: Object, default: null }, sceneState: { type: Object, default: null } })
const selectedId = ref('')
const sparkline = ref(null)
const effectiveSceneState = computed(() => props.sceneState ?? {
  project_scene: sceneStateFromProject(props.project),
  data_scene: sceneFromRun(props.latestRun),
})
const visualScene = computed(() => resolveScene3DView(effectiveSceneState.value))
const scenarioId = computed(() => visualScene.value.descriptor.id || props.project.scenarioId || 'blast_furnace')
const isBlastFurnace = computed(() => scenarioId.value === 'blast_furnace')
const isDebutanizer = computed(() => scenarioId.value === 'debutanizer_column')
const isDryer = computed(() => scenarioId.value === 'industrial_dryer')
const sceneLayouts = {
  blast_furnace: { description: '炼铁高炉设备拓扑与当前任务关键变量', input: [18, 60], output: [78, 78] },
  debutanizer_column: { description: '脱丁烷塔设备拓扑与当前任务关键变量', input: [78, 43], output: [70, 79] },
  industrial_dryer: { description: '工业干燥器设备拓扑与当前任务关键变量', input: [17, 60], output: [80, 74] },
}
const twinDefinition = computed(() => sceneLayouts[scenarioId.value] ?? sceneLayouts.blast_furnace)
const sceneDescription = computed(() => twinDefinition.value.description)
const visualFallback = computed(() => visualScene.value.usedProjectFallback)
const sceneDisplayNote = computed(() => visualFallback.value
  ? `本次数据识别为${effectiveSceneState.value.data_scene.display_name}，暂无适用设备资产，当前展示项目拓扑且不绑定跨场景测点`
  : '设备图为结构示意，数值仅来自同场景真实任务')
const preview = computed(() => props.latestRun?.results?.cleaning?.timeseries_preview?.points ?? [])
const metrics = computed(() => {
  if (!props.latestRun || visualFallback.value || !preview.value.length) return []
  const last = preview.value.at(-1)
  const rows = []
  if (Number.isFinite(Number(last?.input))) rows.push({ id: 'runtime-input', role: 'input', label: props.project.mv, value: Number(last.input).toFixed(2), unit: props.project.mvUnit, status: 'normal', x: twinDefinition.value.input[0], y: twinDefinition.value.input[1], trend: preview.value.slice(-24).map((point) => Number(point.input)).filter(Number.isFinite) })
  if (Number.isFinite(Number(last?.output))) rows.push({ id: 'runtime-output', role: 'output', label: props.project.target, value: Number(last.output).toFixed(3), unit: props.project.targetUnit, status: 'normal', x: twinDefinition.value.output[0], y: twinDefinition.value.output[1], trend: preview.value.slice(-24).map((point) => Number(point.output)).filter(Number.isFinite) })
  return rows
})
watch([scenarioId, metrics], () => { selectedId.value = metrics.value[0]?.id ?? '' }, { immediate: true })
const selected = computed(() => metrics.value.find((item) => item.id === selectedId.value) ?? null)
const sparklineOption = computed(() => ({
  animationDuration: 450,
  grid: { left: 8, right: 8, top: 15, bottom: 8 },
  tooltip: { trigger: 'axis', valueFormatter: (value) => `${value} ${selected.value?.unit ?? ''}` },
  xAxis: { type: 'category', show: false, data: selected.value?.trend?.map((_, index) => index) ?? [] },
  yAxis: { type: 'value', show: false, scale: true },
  series: [{ type: 'line', data: selected.value?.trend ?? [], smooth: .28, symbol: 'none', lineStyle: { color: selected.value?.status === 'warning' ? '#fb7185' : '#38bdf8', width: 2.2 }, areaStyle: { color: selected.value?.status === 'warning' ? 'rgba(251,113,133,.12)' : 'rgba(56,189,248,.12)' } }],
}))
useEChart(sparkline, sparklineOption)
</script>

<template>
  <section class="twin-panel">
    <div class="twin-heading"><div><span class="section-kicker">Industrial Process Topology</span><h2>工业场景设备拓扑</h2><p>{{ sceneDescription }}；{{ sceneDisplayNote }}。</p></div><div><StatusPill :tone="metrics.length ? 'success' : visualFallback ? 'brand' : 'neutral'" dot>{{ metrics.length ? '真实任务测点' : visualFallback ? '项目拓扑回退' : '等待真实数据' }}</StatusPill><span>{{ latestRun?.run_id ?? project.code }}</span></div></div>
    <div class="twin-stage">
      <svg v-if="isBlastFurnace" viewBox="0 0 1000 420" role="img" aria-label="钢铁高炉数字孪生设备示意图">
        <defs><linearGradient id="blastShell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#17375b"/><stop offset="1" stop-color="#0a1e35"/></linearGradient></defs>
        <g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/></g>
        <path class="furnace-shell" fill="url(#blastShell)" d="M410 35H590L575 92L625 165L605 300Q595 360 500 378Q405 360 395 300L375 165L425 92Z"/>
        <path class="furnace-zone" d="M425 92H575M390 165H610M401 300H599"/>
        <text x="464" y="72">炉喉</text><text x="463" y="138">炉身</text><text x="463" y="236">炉腹</text><text x="463" y="338">炉缸</text>
        <path class="flow-line" d="M500 5V48M155 255H397M603 255H850M500 375V410"/>
        <text x="520" y="22">矿石 / 焦炭</text><text x="160" y="240">热风 / 富氧</text><text x="720" y="240">炉顶煤气</text><text x="520" y="405">铁水</text>
      </svg>
      <svg v-else-if="isDebutanizer" viewBox="0 0 1000 420" role="img" aria-label="脱丁烷塔数字孪生设备示意图">
        <defs><linearGradient id="columnShell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0a1d33"/><stop offset=".5" stop-color="#1a4568"/><stop offset="1" stop-color="#0a1d33"/></linearGradient></defs>
        <g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/></g>
        <path class="column-shell" fill="url(#columnShell)" d="M405 74Q405 39 440 39H515Q550 39 550 74V334Q550 369 515 369H440Q405 369 405 334Z"/>
        <g class="column-trays"><path d="M416 96H539M416 128H539M416 160H539M416 192H539M416 224H539M416 256H539M416 288H539M416 320H539"/><circle cx="441" cy="96" r="3"/><circle cx="510" cy="128" r="3"/><circle cx="447" cy="160" r="3"/><circle cx="515" cy="192" r="3"/><circle cx="442" cy="224" r="3"/><circle cx="511" cy="256" r="3"/></g>
        <path class="flow-line feed-flow" d="M85 210H405"/><text x="100" y="193">混合进料</text>
        <path class="flow-line vapor-flow" d="M477 39V20H670V66"/><rect class="heat-exchanger" x="670" y="42" width="135" height="49" rx="24"/><path class="exchanger-coil" d="M690 66Q706 49 722 66T754 66T786 66"/><text x="700" y="34">塔顶冷凝器</text>
        <path class="reflux-drum" d="M696 122H829Q849 122 849 142T829 162H696Q676 162 676 142T696 122Z"/><path class="flow-line" d="M738 91V122M760 162V194H550M849 142H932"/><text x="712" y="146">回流罐</text><text x="865" y="128">C₄轻组分</text>
        <path class="reboiler" d="M654 306Q622 306 622 338T654 370H759Q791 370 791 338T759 306Z"/><path class="reboiler-coil" d="M647 338Q665 316 683 338T719 338T755 338"/><path class="flow-line liquid-flow" d="M477 369V392H706V370M622 338H550M791 338H920"/><text x="667" y="298">塔底再沸器</text><text x="824" y="326">C₅⁺重组分</text>
        <text x="446" y="64">精馏段</text><text x="446" y="351">提馏段</text>
      </svg>
      <svg v-else-if="isDryer" viewBox="0 0 1000 420" role="img" aria-label="工业回转干燥器数字孪生设备示意图">
        <defs><linearGradient id="dryerShell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#225273"/><stop offset=".52" stop-color="#0e2c46"/><stop offset="1" stop-color="#071827"/></linearGradient></defs>
        <g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/></g>
        <path class="dryer-hopper" d="M140 58H274L250 130H164Z"/><path class="flow-line solid-flow" d="M207 130V171H330"/><text x="164" y="45">湿料料斗</text>
        <g class="dryer-unit"><path class="dryer-shell" fill="url(#dryerShell)" d="M320 136L725 113Q766 111 775 149L804 273Q811 307 770 310L365 333Q326 335 318 298L289 174Q282 139 320 136Z"/><path class="dryer-rib" d="M378 133L416 330M478 127L516 324M578 121L616 318M678 116L716 312"/><ellipse class="dryer-end" cx="305" cy="235" rx="25" ry="101" transform="rotate(-13 305 235)"/><ellipse class="dryer-end" cx="789" cy="211" rx="25" ry="101" transform="rotate(-13 789 211)"/></g>
        <circle class="dryer-fan" cx="123" cy="276" r="39"/><path class="fan-blade" d="M123 276L104 247Q135 242 123 276M123 276L153 268Q149 298 123 276M123 276L112 306Q87 286 123 276"/><rect class="dryer-heater" x="180" y="246" width="88" height="58" rx="8"/><path class="heater-coil" d="M196 275Q207 257 218 275T240 275T262 275"/><path class="flow-line hot-flow" d="M162 276H289"/><text x="75" y="337">热风机</text><text x="190" y="326">空气加热器</text>
        <path class="dryer-cyclone" d="M852 48H935L925 184L894 245L863 184Z"/><path class="flow-line exhaust-flow" d="M795 150H881V48M935 83H978"/><text x="856" y="32">尾气旋风分离</text><text x="937" y="70">湿尾气</text>
        <path class="product-chute" d="M767 311H842L875 385H817Z"/><path class="flow-line solid-flow" d="M798 309L842 385H954"/><text x="852" y="374">干燥产品</text>
        <path class="support" d="M382 331L363 367H432L415 329M687 314L669 355H738L720 312"/>
      </svg>
      <svg v-else viewBox="0 0 1000 420" role="img" aria-label="通用流程工业设备占位图"><g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/></g><rect class="generic-vessel" x="370" y="52" width="260" height="315" rx="125"/><path class="furnace-zone" d="M370 150H630M370 250H630"/><path class="flow-line" d="M80 210H370M630 210H920"/><text x="425" y="215">通用反应设备</text></svg>

      <button v-for="item in metrics" :key="item.id" class="twin-sensor" :class="{ 'is-warning': item.status === 'warning', 'is-active': selectedId === item.id }" :style="{ left: `${item.x}%`, top: `${item.y}%` }" type="button" @click="selectedId = item.id"><i></i><span>{{ item.label }}</span><strong>{{ item.value }} <small>{{ item.unit }}</small></strong></button>
      <div v-if="!metrics.length" class="twin-empty">{{ visualFallback ? '当前数据与项目拓扑不同，已停止绑定跨场景测点。' : '暂无真实测点快照；上传 CSV 后显示关键输入与输出。' }}</div>
      <div class="twin-legend"><span><i class="normal"></i>正常测点</span><span><i class="warning"></i>需要关注</span><span><b></b>物料流向</span></div>
      <aside v-if="selected" class="sensor-popover"><div><span>MEASUREMENT TREND</span><button type="button" aria-label="关闭测点趋势" @click="selectedId = ''">×</button></div><strong>{{ selected.label }}</strong><p>{{ selected.value }} <small>{{ selected.unit }}</small><StatusPill :tone="selected.status === 'warning' ? 'warning' : 'success'">{{ selected.status === 'warning' ? '偏离稳态带' : '运行正常' }}</StatusPill></p><div ref="sparkline" class="sensor-sparkline"></div></aside>
    </div>
  </section>
</template>

<style scoped>
.twin-panel { overflow: hidden; color: #d9e8fa; border: 1px solid #173758; border-radius: 14px; background: radial-gradient(circle at 58% 35%, rgba(18,78,128,.38), transparent 34%), linear-gradient(135deg, #071321, #0b223b 55%, #071827); box-shadow: 0 16px 38px rgba(7, 24, 39, .16); }
.twin-heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; padding: 18px 21px 8px; }.twin-heading h2 { margin-top: 4px; color: #f2f8ff; font-size: 18px; }.twin-heading p { margin-top: 5px; color: #7594b5; font-size: 10px; }.twin-heading > div:last-child { display: flex; align-items: center; gap: 10px; color: #6e8ba8; font: 9px monospace; }
.twin-stage { position: relative; min-height: 390px; overflow: hidden; }.twin-stage > svg { display: block; width: 100%; min-width: 760px; height: 390px; }.twin-grid path { fill: none; stroke: rgba(89,150,201,.07); stroke-width: 1; }.furnace-shell, .generic-vessel { stroke: #4ba3d8; stroke-width: 2; }.furnace-zone { fill: none; stroke: rgba(94,184,235,.55); stroke-width: 2; stroke-dasharray: 4 5; }.twin-stage svg text { fill: #628aae; font: 12px 'PingFang SC', sans-serif; }.flow-line { fill: none; stroke: #48b7ed; stroke-width: 2; stroke-dasharray: 9 8; animation: flow 1.4s linear infinite; }.generic-vessel { fill: rgba(23,55,91,.7); }
.column-shell { stroke: #55b5e9; stroke-width: 2.4; }.column-trays path { fill: none; stroke: rgba(118,207,248,.62); stroke-width: 2; }.column-trays circle { fill: #67e8f9; filter: drop-shadow(0 0 4px rgba(103,232,249,.75)); }.heat-exchanger, .reflux-drum, .reboiler { fill: rgba(15,53,80,.82); stroke: #54acd9; stroke-width: 2; }.exchanger-coil, .reboiler-coil { fill: none; stroke: #7dd3fc; stroke-width: 1.8; }.feed-flow { stroke: #a78bfa; }.vapor-flow { stroke: #67e8f9; }.liquid-flow { stroke: #60a5fa; }
.dryer-hopper, .dryer-cyclone, .product-chute { fill: rgba(19,55,79,.88); stroke: #51a9d7; stroke-width: 2; }.dryer-shell, .dryer-end { stroke: #5ab8e6; stroke-width: 2.3; }.dryer-end { fill: rgba(12,38,60,.92); }.dryer-rib { fill: none; stroke: rgba(122,207,245,.38); stroke-width: 2; }.dryer-unit { transform-origin: 545px 222px; animation: drumHum 2.8s ease-in-out infinite; }.dryer-fan { fill: rgba(11,42,66,.9); stroke: #4eb1e2; stroke-width: 2; }.fan-blade { fill: rgba(73,189,235,.58); animation: fanPulse 1.4s ease-in-out infinite; transform-origin: 123px 276px; }.dryer-heater { fill: rgba(75,45,18,.6); stroke: #f59e42; stroke-width: 2; }.heater-coil { fill: none; stroke: #fb923c; stroke-width: 2; }.support { fill: rgba(15,45,68,.9); stroke: #417ca3; }.hot-flow { stroke: #fb923c; }.solid-flow { stroke: #a78bfa; }.exhaust-flow { stroke: #94a3b8; }
.twin-sensor { position: absolute; z-index: 3; display: grid; min-width: 110px; padding: 7px 9px 7px 17px; color: #d9e9f8; text-align: left; border: 1px solid rgba(65,160,216,.32); border-radius: 7px; background: rgba(5,20,34,.78); backdrop-filter: blur(8px); transform: translate(-50%, -50%); }.twin-sensor i { position: absolute; left: -5px; top: 50%; width: 10px; height: 10px; border: 2px solid #082138; border-radius: 50%; background: #34d399; box-shadow: 0 0 9px #34d399; transform: translateY(-50%); }.twin-sensor span { color: #7899b8; font-size: 8px; }.twin-sensor strong { margin-top: 3px; font: 700 12px monospace; }.twin-sensor small { color: #6f8ca8; font-size: 7px; }.twin-sensor.is-warning i { background: #fb7185; box-shadow: 0 0 9px #fb7185; animation: alarm 1.1s ease-in-out infinite; }.twin-sensor.is-warning strong { color: #fda4af; }.twin-sensor.is-active { border-color: #56b8ef; box-shadow: 0 0 0 2px rgba(56,189,248,.12); }
.sensor-popover { position: absolute; z-index: 5; top: 18px; right: 18px; width: 245px; padding: 13px; border: 1px solid rgba(75,163,216,.4); border-radius: 10px; background: rgba(5,19,33,.92); box-shadow: 0 14px 30px rgba(0,0,0,.28); backdrop-filter: blur(12px); }.sensor-popover > div:first-child { display: flex; justify-content: space-between; color: #4e789e; font: 8px monospace; }.sensor-popover button { color: #7595b5; border: 0; background: transparent; }.sensor-popover > strong { display: block; margin-top: 7px; font-size: 12px; }.sensor-popover > p { display: flex; align-items: center; gap: 8px; margin-top: 4px; font: 700 17px monospace; }.sensor-popover p small { color: #7595b5; font-size: 9px; }.sensor-popover .status-pill { margin-left: auto; font-family: inherit; }.sensor-sparkline { height: 82px; margin-top: 5px; }
.twin-legend { position: absolute; left: 20px; bottom: 12px; display: flex; gap: 15px; color: #6889a8; font-size: 8px; }.twin-legend span { display: flex; align-items: center; gap: 5px; }.twin-legend i { width: 7px; height: 7px; border-radius: 50%; }.twin-legend i.normal { background: #34d399; }.twin-legend i.warning { background: #fb7185; }.twin-legend b { width: 21px; border-top: 1px dashed #48b7ed; }
.twin-empty { position: absolute; left: 50%; bottom: 38px; padding: 9px 13px; color: #87a6c4; font-size: 10px; border: 1px dashed rgba(96, 165, 250, .35); border-radius: 8px; background: rgba(5, 20, 34, .82); transform: translateX(-50%); }
@keyframes flow { to { stroke-dashoffset: -34; } } @keyframes alarm { 50% { opacity: .42; transform: translateY(-50%) scale(1.45); } } @keyframes drumHum { 50% { transform: translateY(-1.5px); } } @keyframes fanPulse { 50% { opacity: .62; transform: scale(.92); } }
@media (max-width: 760px) { .twin-stage { overflow-x: auto; }.sensor-popover { position: sticky; left: 12px; bottom: 12px; margin: -110px 12px 12px auto; }.twin-heading > div:last-child > span:last-child { display: none; } }
</style>
