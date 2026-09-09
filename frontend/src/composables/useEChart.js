import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, BoxplotChart, GaugeChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, BoxplotChart, GaugeChart, LineChart, GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent, TooltipComponent, CanvasRenderer])

export function useEChart(elementRef, optionRef) {
  let chart
  let observer

  function render() {
    if (!elementRef.value || !elementRef.value.clientWidth || !elementRef.value.clientHeight) return
    if (!chart) chart = echarts.init(elementRef.value, null, { renderer: 'canvas' })
    chart.setOption(optionRef.value ?? {}, { notMerge: true, lazyUpdate: true })
  }

  onMounted(async () => {
    await nextTick()
    render()
    observer = new ResizeObserver(() => chart?.resize())
    if (elementRef.value) observer.observe(elementRef.value)
    window.addEventListener('processpilot:charts-visible', render)
  })

  watch(optionRef, () => nextTick(render), { deep: true })
  onBeforeUnmount(() => {
    observer?.disconnect()
    window.removeEventListener('processpilot:charts-visible', render)
    chart?.dispose()
  })

  return { render, getChart: () => chart }
}
