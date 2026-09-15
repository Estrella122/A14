<script setup>
import { nextTick, ref, watch } from 'vue'
import { apiBaseUrl } from '../api/client'
defineProps({ charts: { type: Array, required: true } })
const imageUrl = (chart) => chart.url.startsWith('/api/') ? apiBaseUrl + chart.url.slice(4) : chart.url
const failed = ref({})
const expanded = ref(null)
const dialog = ref(null)
watch(expanded, async (value) => {
  await nextTick()
  if (value && !dialog.value.open) dialog.value.showModal()
  else if (!value && dialog.value.open) dialog.value.close()
})
</script>

<template>
  <div class="chat-charts">
    <figure v-for="chart in charts" :key="chart.url">
      <header><strong>{{ chart.title }}</strong><button type="button" @click="expanded = chart">放大查看</button></header>
      <p v-if="failed[chart.url]" role="status">图表加载失败，请重试或下载文件。</p>
      <img v-else :src="imageUrl(chart)" :alt="chart.title" loading="lazy" @error="failed[chart.url] = true" />
      <figcaption>{{ chart.caption }}</figcaption>
      <a :href="`${imageUrl(chart)}?download=1`" download>下载 SVG</a>
      <button v-if="failed[chart.url]" type="button" @click="failed[chart.url] = false">重新加载</button>
    </figure>
    <dialog ref="dialog" class="chart-dialog" @cancel="expanded = null" @close="expanded = null">
      <template v-if="expanded">
        <header><strong>{{ expanded.title }}</strong><button type="button" autofocus @click="expanded = null">关闭大图</button></header>
        <img :src="imageUrl(expanded)" :alt="expanded.title" />
        <p>{{ expanded.caption }}</p>
      </template>
    </dialog>
  </div>
</template>

<style scoped>
.chat-charts { display:grid; gap:18px; margin:18px 0; }
figure { margin:0; padding:14px; border:1px solid #dce5df; border-radius:12px; background:#fff; }
header { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; font-size:14px; }
img { width:100%; height:auto; display:block; }
figcaption,.chart-dialog p { color:#64746a; font-size:12px; line-height:1.7; margin:8px 0; }
button,a { font:inherit; font-size:12px; color:#28623f; cursor:pointer; }
button { border:1px solid #d8e4dc; border-radius:8px; padding:7px 10px; background:#f6faf7; }
.chart-dialog[open] { display:block; position:fixed; inset:5vh 3vw; width:94vw; max-height:90dvh; overflow:auto; z-index:100; border:1px solid #cbdacf; border-radius:16px; padding:24px; margin:auto; }
.chart-dialog::backdrop { background:#14271cb3; }
.chart-dialog img { max-height:70vh; object-fit:contain; }
</style>
