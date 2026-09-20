<script setup>
import { computed } from 'vue'
const props = defineProps({ report: { type: Object, required: true } })
const rounds = computed(() => props.report.iterations ?? [])
const scores = computed(() => rounds.value.filter((row) => row.score != null && Number.isFinite(Number(row.score))))
const points = computed(() => {
  const values = scores.value.map((row) => Number(row.score))
  const min = Math.min(...values)
  const spread = Math.max(...values) - min || 1
  return values.map((value, index) => `${16 + index * 388 / Math.max(1, values.length - 1)},${104 - (value - min) / spread * 80}`).join(' ')
})
const metric = (value, digits = 2) => value != null && Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—'
</script>

<template>
  <section class="chat-optimization">
    <h3>闭环寻优 · {{ report.candidate_counts?.attempted ?? (report.iterations ? rounds.length : '暂未取得') }} 轮记录</h3>
    <p>{{ report.objective || '当前运行的候选比较结果' }}</p>
    <figure v-if="scores.length">
      <svg viewBox="0 0 420 125" role="img" aria-label="各轮候选得分变化，详细数值见下表">
        <path d="M16 16V108H404" fill="none" stroke="#d9e3db" />
        <polyline :points="points" fill="none" stroke="#357953" stroke-width="2.5" stroke-linejoin="round" />
      </svg>
      <figcaption>候选得分随轮次变化；高分不代表已通过约束。</figcaption>
    </figure>
    <details>
      <summary>展开每轮参数、指标与约束结果</summary>
      <div class="round-table" tabindex="0" aria-label="寻优轮次表，可横向滚动">
        <table>
          <thead><tr><th>轮次</th><th>Top K</th><th>时滞</th><th>R²</th><th>RMSE</th><th>得分</th><th>约束</th><th>原因</th></tr></thead>
          <tbody><tr v-for="row in rounds" :key="row.round"><td>{{ row.round }}</td><td>{{ row.top_k ?? '—' }}</td><td>{{ row.max_lag ?? '—' }}</td><td>{{ metric(row.r2, 3) }}</td><td>{{ metric(row.rmse) }}</td><td>{{ metric(row.score) }}</td><td>{{ row.feasible === true ? '通过' : row.feasible === false ? '未通过' : '未评估' }}</td><td>{{ row.reason_message || row.rejection_reason || row.error || '暂未取得' }}</td></tr></tbody>
        </table>
      </div>
    </details>
    <p v-if="report.stopping?.stop_reason">停止原因：{{ report.stopping.stop_reason }}</p>
  </section>
</template>

<style scoped>
.chat-optimization { border-top:1px solid #e0e7e1; padding-top:18px; }
h3 { font-size:16px; } p,figcaption { font-size:13px; color:#596b60; line-height:1.7; }
figure { margin:16px 0; } svg { display:block; width:100%; } summary { cursor:pointer; font-size:13px; padding:10px 0; }
.round-table { overflow:auto; max-height:320px; margin-top:8px; } table { width:100%; border-collapse:collapse; font-size:12px; white-space:nowrap; }
th,td { padding:9px; text-align:right; border-bottom:1px solid #e6ebe7; } th { position:sticky; top:0; background:#f4f7f4; }
</style>
