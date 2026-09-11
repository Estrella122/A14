<script setup>
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { mockTwin } from '../data/mockData'
import { useEChart } from '../composables/useEChart'

const props = defineProps({ project: { type: Object, required: true }, latestRun: { type: Object, default: null } })
const selectedId = ref('si')
const sparkline = ref(null)
const isBlastFurnace = computed(() => /高炉|blast.furnace/i.test(`${props.project.scene} ${props.project.shortName} ${props.project.scenarioId}`))
const preview = computed(() => props.latestRun?.results?.cleaning?.timeseries_preview?.points ?? [])
const metrics = computed(() => {
  // TODO(mock): 后端增加实时测点快照后，以 tag/value/status/trend 直接替换当前任务末点与演示趋势的合成逻辑。
  const last = preview.value.at(-1)
  return mockTwin.metrics.map((item) => {
    if (item.id === 'blast' && Number.isFinite(Number(last?.input))) return { ...item, label: props.project.mv, value: Number(last.input).toFixed(1), unit: props.project.mvUnit, status: Number(last.input) > 0 ? 'normal' : 'warning', trend: preview.value.slice(-24).map((point) => Number(point.input)) }
    if (item.id === 'si' && Number.isFinite(Number(last?.output))) return { ...item, label: props.project.target, value: Number(last.output).toFixed(3), unit: props.project.targetUnit, status: Number(last.output) >= 0.1 && Number(last.output) <= 1.5 ? 'normal' : 'warning', trend: preview.value.slice(-24).map((point) => Number(point.output)) }
    return item
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
    <div class="twin-heading"><div><span class="section-kicker">Industrial Digital Twin</span><h2>工业场景数字孪生</h2><p>{{ isBlastFurnace ? '炼铁高炉过程测点、煤气流与铁水质量状态' : '通用流程设备测点占位' }}</p></div><div><StatusPill :tone="latestRun ? 'success' : 'warning'" dot>{{ latestRun ? '任务数据映射' : '场景占位数据' }}</StatusPill><span>{{ latestRun?.run_id ?? project.code }}</span></div></div>
    <div class="twin-stage">
      <svg v-if="isBlastFurnace" viewBox="0 0 1000 420" role="img" aria-label="炼铁高炉数字孪生设备示意图">
        <defs>
          <linearGradient id="furnaceShell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#17375b" stop-opacity=".9"/><stop offset="1" stop-color="#0a1e35" stop-opacity=".94"/></linearGradient>
          <radialGradient id="fireGlow"><stop offset="0" stop-color="#ffb347" stop-opacity=".48"/><stop offset="1" stop-color="#ff6b35" stop-opacity="0"/></radialGradient>
          <filter id="softGlow"><feGaussianBlur stdDeviation="7"/></filter>
        </defs>
        <g class="twin-grid"><path d="M0 70H1000M0 140H1000M0 210H1000M0 280H1000M0 350H1000"/><path d="M100 0V420M200 0V420M300 0V420M400 0V420M500 0V420M600 0V420M700 0V420M800 0V420M900 0V420"/></g>
        <ellipse cx="515" cy="250" rx="180" ry="120" fill="url(#fireGlow)" filter="url(#softGlow)"/>
        <path class="furnace-shell" d="M405 48H615L650 135L618 302Q610 346 570 365H450Q410 346 402 302L370 135Z" fill="url(#furnaceShell)"/>
        <path class="furnace-roof" d="M405 48L430 20H590L615 48M389 184H631M405 294H615"/>
        <path class="furnace-zone" d="M390 135H630M402 232H618"/><text x="475" y="115">炉身</text><text x="475" y="214">炉腹</text><text x="475" y="283">炉缸</text>
        <g class="burners"><path d="M360 292l48-18v31zM660 292l-48-18v31z"/><circle cx="410" cy="289" r="22"/><circle cx="610" cy="289" r="22"/></g>
        <path class="flow-line" d="M510 5V42M610 80H820V26M402 286H210M618 328H884"/>
        <path class="flow-line gas-flow" d="M82 286H394M626 286H790"/>
        <path class="flow-line smoke-flow" d="M630 82H820V18"/>
        <path class="slab" d="M618 328H884"/><circle cx="884" cy="328" r="7" class="slab-block"/>
        <text x="448" y="18">矿焦料批</text><text x="826" y="30">炉顶煤气</text><text x="82" y="274">热风 / 富氧</text><text x="798" y="316">铁水出铁口</text>
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
