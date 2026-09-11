<script setup>
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { mockTwin } from '../data/mockData'
import { useEChart } from '../composables/useEChart'

const props = defineProps({ project: { type: Object, required: true }, latestRun: { type: Object, default: null } })
const selectedId = ref('temp')
const sparkline = ref(null)
const isBlastFurnace = computed(() => props.project.scenarioId === 'blast_furnace')
const preview = computed(() => props.latestRun?.results?.cleaning?.timeseries_preview?.points ?? [])
const metrics = computed(() => {
  // TODO(mock): 后端增加实时测点快照后，以 tag/value/status/trend 直接替换当前任务末点与演示趋势的合成逻辑。
  const last = preview.value.at(-1)
  return mockTwin.metrics.map((item) => {
    const blastLabels = { temp: ['热风温度', '℃'], gas: ['鼓风流量', 'm³/min'], slabIn: ['炉顶温度', '℃'], slabOut: ['铁水硅含量', '%'] }
    const sceneItem = isBlastFurnace.value && blastLabels[item.id] ? { ...item, label: blastLabels[item.id][0], unit: blastLabels[item.id][1] } : item
    if (item.id === 'gas' && Number.isFinite(Number(last?.input))) return { ...sceneItem, label: props.project.mv, value: Number(last.input).toFixed(1), unit: props.project.mvUnit, trend: preview.value.slice(-24).map((point) => Number(point.input)) }
    if (item.id === 'slabOut' && Number.isFinite(Number(last?.output))) return { ...sceneItem, label: props.project.target, value: Number(last.output).toFixed(3), unit: props.project.targetUnit, trend: preview.value.slice(-24).map((point) => Number(point.output)) }
    return sceneItem
  })
})
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
    <div class="twin-heading"><div><span class="section-kicker">Industrial Digital Twin</span><h2>工业场景数字孪生</h2><p>{{ isBlastFurnace ? '炼铁高炉传感器、炉料与铁水质量状态' : `${project.shortName}流程测点占位` }}</p></div><div><StatusPill :tone="latestRun ? 'success' : 'warning'" dot>{{ latestRun ? '任务数据映射' : '演示数据' }}</StatusPill><span>{{ latestRun?.run_id ?? project.code }}</span></div></div>
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
      <svg v-else-if="false" viewBox="0 0 1000 420" role="img" aria-label="加热炉数字孪生设备示意图">
        <defs>
          <linearGradient id="furnaceShell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#17375b" stop-opacity=".9"/><stop offset="1" stop-color="#0a1e35" stop-opacity=".94"/></linearGradient>
          <radialGradient id="fireGlow"><stop offset="0" stop-color="#ffb347" stop-opacity=".48"/><stop offset="1" stop-color="#ff6b35" stop-opacity="0"/></radialGradient>
          <filter id="softGlow"><feGaussianBlur stdDeviation="7"/></filter>
        </defs>
        <g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/><path d="M100 0V420M200 0V420M300 0V420M400 0V420M500 0V420M600 0V420M700 0V420M800 0V420M900 0V420"/></g>
        <ellipse cx="505" cy="230" rx="230" ry="150" fill="url(#fireGlow)" filter="url(#softGlow)"/>
        <path class="furnace-shell" d="M260 110 Q260 75 295 75 H720 Q755 75 755 110 V310 H260Z" fill="url(#furnaceShell)"/>
        <path class="furnace-roof" d="M282 110Q360 54 438 110Q516 54 594 110Q672 54 733 110"/>
        <path class="furnace-zone" d="M425 112V310M590 112V310"/><text x="335" y="143">预热段</text><text x="487" y="143">加热段</text><text x="650" y="143">均热段</text>
        <g class="burners"><path d="M303 201l30-16v32zM468 201l30-16v32zM633 201l30-16v32z"/><circle cx="340" cy="201" r="26"/><circle cx="505" cy="201" r="31"/><circle cx="670" cy="201" r="27"/></g>
        <path class="slab" d="M82 294H882"/><path class="slab-block" d="M125 277h92v31h-92zM316 277h92v31h-92zM505 277h92v31h-92zM696 277h92v31h-92z"/>
        <path class="flow-line" d="M55 294H245M758 294H930"/><path class="flow-line gas-flow" d="M74 200H275M102 200V238H303M102 200V164H303"/>
        <path class="chimney" d="M485 75V24H553V75"/><path class="flow-line smoke-flow" d="M519 68V5"/>
        <text x="68" y="327">钢坯入口</text><text x="848" y="327">钢坯出口</text><text x="67" y="186">燃气总管</text><text x="566" y="31">烟气</text>
      </svg>
      <svg v-else viewBox="0 0 1000 420" role="img" aria-label="通用流程工业设备占位图"><g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/></g><rect class="generic-vessel" x="370" y="52" width="260" height="315" rx="125"/><path class="furnace-zone" d="M370 150H630M370 250H630"/><path class="flow-line" d="M80 210H370M630 210H920"/><text x="425" y="215">通用反应设备</text></svg>

      <button v-for="item in metrics" :key="item.id" class="twin-sensor" :class="{ 'is-warning': item.status === 'warning', 'is-active': selectedId === item.id }" :style="{ left: `${item.x}%`, top: `${item.y}%` }" type="button" @click="selectedId = item.id"><i></i><span>{{ item.label }}</span><strong>{{ item.value }} <small>{{ item.unit }}</small></strong></button>
      <div class="twin-legend"><span><i class="normal"></i>正常测点</span><span><i class="warning"></i>需要关注</span><span><b></b>物料流向</span></div>
      <aside v-if="selected" class="sensor-popover"><div><span>MEASUREMENT TREND</span><button type="button" aria-label="关闭测点趋势" @click="selectedId = ''">×</button></div><strong>{{ selected.label }}</strong><p>{{ selected.value }} <small>{{ selected.unit }}</small><StatusPill :tone="selected.status === 'warning' ? 'warning' : 'success'">{{ selected.status === 'warning' ? '偏离稳态带' : '运行正常' }}</StatusPill></p><div ref="sparkline" class="sensor-sparkline"></div></aside>
    </div>
  </section>
</template>

<style scoped>
.twin-panel { overflow: hidden; color: #d9e8fa; border: 1px solid #173758; border-radius: 14px; background: radial-gradient(circle at 58% 35%, rgba(18,78,128,.38), transparent 34%), linear-gradient(135deg, #071321, #0b223b 55%, #071827); box-shadow: 0 16px 38px rgba(7, 24, 39, .16); }
.twin-heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; padding: 18px 21px 8px; }.twin-heading h2 { margin-top: 4px; color: #f2f8ff; font-size: 18px; }.twin-heading p { margin-top: 5px; color: #7594b5; font-size: 10px; }.twin-heading > div:last-child { display: flex; align-items: center; gap: 10px; color: #6e8ba8; font: 9px monospace; }
.twin-stage { position: relative; min-height: 390px; overflow: hidden; }.twin-stage > svg { display: block; width: 100%; min-width: 760px; height: 390px; }.twin-grid path { fill: none; stroke: rgba(89,150,201,.07); stroke-width: 1; }.furnace-shell, .generic-vessel { stroke: #4ba3d8; stroke-width: 2; }.furnace-roof, .furnace-zone, .chimney { fill: none; stroke: rgba(94,184,235,.55); stroke-width: 2; }.furnace-zone { stroke-dasharray: 4 5; }.twin-stage svg text { fill: #628aae; font: 12px 'PingFang SC', sans-serif; }.burners path { fill: #ff9f43; }.burners circle { fill: rgba(255,118,42,.1); stroke: rgba(255,160,80,.34); }.slab { fill: none; stroke: #91acc7; stroke-width: 5; }.slab-block { fill: rgba(99,166,215,.16); stroke: #5f9fc9; }.flow-line { fill: none; stroke: #48b7ed; stroke-width: 2; stroke-dasharray: 9 8; animation: flow 1.4s linear infinite; }.gas-flow { stroke: #f7a84c; }.smoke-flow { stroke: #829bb4; }.generic-vessel { fill: rgba(23,55,91,.7); }
.twin-sensor { position: absolute; z-index: 3; display: grid; min-width: 110px; padding: 7px 9px 7px 17px; color: #d9e9f8; text-align: left; border: 1px solid rgba(65,160,216,.32); border-radius: 7px; background: rgba(5,20,34,.78); backdrop-filter: blur(8px); transform: translate(-50%, -50%); }.twin-sensor i { position: absolute; left: -5px; top: 50%; width: 10px; height: 10px; border: 2px solid #082138; border-radius: 50%; background: #34d399; box-shadow: 0 0 9px #34d399; transform: translateY(-50%); }.twin-sensor span { color: #7899b8; font-size: 8px; }.twin-sensor strong { margin-top: 3px; font: 700 12px monospace; }.twin-sensor small { color: #6f8ca8; font-size: 7px; }.twin-sensor.is-warning i { background: #fb7185; box-shadow: 0 0 9px #fb7185; animation: alarm 1.1s ease-in-out infinite; }.twin-sensor.is-warning strong { color: #fda4af; }.twin-sensor.is-active { border-color: #56b8ef; box-shadow: 0 0 0 2px rgba(56,189,248,.12); }
.sensor-popover { position: absolute; z-index: 5; top: 18px; right: 18px; width: 245px; padding: 13px; border: 1px solid rgba(75,163,216,.4); border-radius: 10px; background: rgba(5,19,33,.92); box-shadow: 0 14px 30px rgba(0,0,0,.28); backdrop-filter: blur(12px); }.sensor-popover > div:first-child { display: flex; justify-content: space-between; color: #4e789e; font: 8px monospace; }.sensor-popover button { color: #7595b5; border: 0; background: transparent; }.sensor-popover > strong { display: block; margin-top: 7px; font-size: 12px; }.sensor-popover > p { display: flex; align-items: center; gap: 8px; margin-top: 4px; font: 700 17px monospace; }.sensor-popover p small { color: #7595b5; font-size: 9px; }.sensor-popover .status-pill { margin-left: auto; font-family: inherit; }.sensor-sparkline { height: 82px; margin-top: 5px; }
.twin-legend { position: absolute; left: 20px; bottom: 12px; display: flex; gap: 15px; color: #6889a8; font-size: 8px; }.twin-legend span { display: flex; align-items: center; gap: 5px; }.twin-legend i { width: 7px; height: 7px; border-radius: 50%; }.twin-legend i.normal { background: #34d399; }.twin-legend i.warning { background: #fb7185; }.twin-legend b { width: 21px; border-top: 1px dashed #48b7ed; }
@keyframes flow { to { stroke-dashoffset: -34; } } @keyframes alarm { 50% { opacity: .42; transform: translateY(-50%) scale(1.45); } }
@media (max-width: 760px) { .twin-stage { overflow-x: auto; }.sensor-popover { position: sticky; left: 12px; bottom: 12px; margin: -110px 12px 12px auto; }.twin-heading > div:last-child > span:last-child { display: none; } }
</style>
