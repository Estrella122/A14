<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { compactRuntimeEvents, runtimeEventIsActive, visibleRuntimeEvents } from '../utils/runtimeEvents'

const props = defineProps({ events: { type: Array, default: () => [] }, status: { type: String, default: 'running' }, metrics: { type: Object, default: () => ({}) }, compact: { type: Boolean, default: false } })
const rows = computed(() => visibleRuntimeEvents(props.events))
const expanded = ref(!props.compact && props.status === 'running')
const userControlled = ref(false)
const displayedRows = computed(() => expanded.value ? rows.value : compactRuntimeEvents(props.events, props.compact ? 1 : 4))
const icon = (status) => status === 'failed' || status === 'blocked' ? 'warning' : status === 'completed' || status === 'success' || status === 'available' ? 'check' : 'loop'
const isActive = (event) => runtimeEventIsActive(event, props.status)

watch(() => props.status, (status) => {
  if (!userControlled.value) expanded.value = !props.compact && status === 'running'
})

function toggleExpanded() {
  userControlled.value = true
  expanded.value = !expanded.value
}
</script>

<template>
  <section class="execution-timeline" aria-live="polite">
    <header>
      <div><strong>实时执行</strong><span class="timeline-status">{{ status === 'running' ? '进行中' : status === 'completed' ? '已完成' : '执行失败' }}</span></div>
      <button type="button" :aria-expanded="expanded" @click="toggleExpanded">{{ expanded ? '收起详情' : `展开 ${rows.length} 条记录` }}</button>
    </header>
    <ol :class="{ 'is-collapsed': !expanded }">
      <li v-for="event in displayedRows" :key="event.sequence" :class="`event-${event.status}`">
        <AppIcon :name="isActive(event) ? 'loop' : icon(event.status)" :class="{ spinning: isActive(event) }" :size="12" />
        <div><strong>{{ event.executor || event.capability_id || event.skill_id || event.stage }}</strong><p>{{ event.message }}</p></div>
        <time>{{ event.timestamp?.slice(11, 19) }}</time>
      </li>
    </ol>
    <footer v-if="metrics.event_count">事件 {{ metrics.event_count }} 条 · 平均载荷 {{ metrics.average_payload_bytes }} B</footer>
  </section>
</template>

<style scoped>
.execution-timeline{width:min(92%,620px);padding:10px 12px;border:1px solid #bfdbfe;border-radius:10px;background:#f8fbff}.execution-timeline header,.execution-timeline header>div{display:flex;align-items:center}.execution-timeline header{justify-content:space-between;gap:12px;color:#1e3a8a;font-size:9px}.execution-timeline header>div{gap:8px}.timeline-status{color:#64748b}.execution-timeline header button{padding:4px 8px;color:#315a91;font-size:8px;border:1px solid #c9dcf7;border-radius:999px;background:#fff;cursor:pointer}.execution-timeline header button:hover{border-color:#8bb0ef;background:#eff6ff}.execution-timeline ol{display:grid;gap:6px;max-height:min(48vh,430px);margin:9px 0 0;padding:0 5px 0 0;overflow:auto;list-style:none;scrollbar-width:thin}.execution-timeline ol.is-collapsed{max-height:150px}.execution-timeline li{display:grid;grid-template-columns:14px 1fr auto;gap:6px;align-items:start;color:#475569}.execution-timeline li div strong{font-size:8px}.execution-timeline li p{margin:1px 0 0;font-size:8px;line-height:1.4}.execution-timeline time,.execution-timeline footer{color:#94a3b8;font-size:7px}.execution-timeline footer{margin-top:8px}.event-failed,.event-blocked{color:#b91c1c!important}.event-partial{color:#b45309!important}
</style>
