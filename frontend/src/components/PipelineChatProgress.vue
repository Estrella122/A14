<script setup>
import { computed } from 'vue'
const props = defineProps({ run: { type: Object, required: true } })
const labels = { completed: '已完成', failed: '执行失败', needs_review: '待复核', running: '进行中', queued: '排队中', pending: '等待中' }
const current = computed(() => props.run.stages?.find(stage => stage.status === 'running') || props.run.stages?.find(stage => stage.status === 'executing'))
</script>
<template>
  <details class="pipeline-chat-progress">
    <summary>数据处理 · {{ labels[run.status] || run.status }}<span v-if="current"> · {{ current.label }}</span><small>展开查看实际步骤</small></summary>
    <p>这里展示执行进度和结果依据，不是模型内部的完整思考过程。</p>
    <ol><li v-for="stage in run.stages ?? []" :key="stage.key"><strong>{{ stage.label }} · {{ labels[stage.status] || stage.status }}</strong><span v-if="stage.elapsed_ms != null">{{ (stage.elapsed_ms / 1000).toFixed(1) }} 秒</span><p>{{ stage.message }}</p></li></ol>
    <p v-if="run.status === 'running'">后台正在处理；等待时间较长不代表失败。可以切换对话，稍后返回查看。</p>
  </details>
</template>
<style scoped>
.pipeline-chat-progress { border:1px solid #dce5df; border-radius:12px; padding:14px; margin-bottom:18px; font-size:13px; color:#395346; }
summary { cursor:pointer; line-height:1.7; } summary small { display:block; color:#68766e; } ol { padding-left:20px; } li { margin:14px 0; } li>span { margin-left:12px; } p { font-size:12px; line-height:1.7; color:#63736a; }
</style>
