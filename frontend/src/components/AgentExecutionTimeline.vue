<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { visibleRuntimeEvents } from '../utils/runtimeEvents'

const props = defineProps({ events: { type: Array, default: () => [] }, status: { type: String, default: 'running' }, metrics: { type: Object, default: () => ({}) } })
const rows = computed(() => visibleRuntimeEvents(props.events))
const icon = (status) => status === 'failed' || status === 'blocked' ? 'warning' : status === 'completed' || status === 'success' || status === 'available' ? 'check' : 'loop'
</script>

<template>
  <section class="execution-timeline" aria-live="polite">
    <header><strong>实时执行</strong><span>{{ status === 'running' ? '进行中' : status === 'completed' ? '已完成' : '执行失败' }}</span></header>
    <ol>
      <li v-for="event in rows" :key="event.sequence" :class="`event-${event.status}`">
        <AppIcon :name="icon(event.status)" :class="{ spinning: ['executing', 'queued', 'waiting'].includes(event.status) }" :size="12" />
        <div><strong>{{ event.executor || event.capability_id || event.skill_id || event.stage }}</strong><p>{{ event.message }}</p></div>
        <time>{{ event.timestamp?.slice(11, 19) }}</time>
      </li>
    </ol>
    <footer v-if="metrics.event_count">事件 {{ metrics.event_count }} 条 · 平均载荷 {{ metrics.average_payload_bytes }} B</footer>
  </section>
</template>

<style scoped>
.execution-timeline{width:min(92%,620px);padding:10px 12px;border:1px solid #bfdbfe;border-radius:10px;background:#f8fbff}.execution-timeline header{display:flex;justify-content:space-between;color:#1e3a8a;font-size:9px}.execution-timeline ol{display:grid;gap:6px;margin:9px 0 0;padding:0;list-style:none}.execution-timeline li{display:grid;grid-template-columns:14px 1fr auto;gap:6px;align-items:start;color:#475569}.execution-timeline li div strong{font-size:8px}.execution-timeline li p{margin:1px 0 0;font-size:8px;line-height:1.4}.execution-timeline time,.execution-timeline footer{color:#94a3b8;font-size:7px}.execution-timeline footer{margin-top:8px}.event-failed,.event-blocked{color:#b91c1c!important}.event-partial{color:#b45309!important}
</style>
