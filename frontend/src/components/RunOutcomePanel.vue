<script setup>
import { computed } from 'vue'
const props = defineProps({ run: { type: Object, default: null } })
const report = computed(() => props.run?.results?.optimization)
const visible = computed(() => report.value && report.value.optimization_outcome !== 'qualified_candidate')
const labels = { searching: '闭环寻优正在计算', no_feasible_candidate: '搜索已结束，没有合格候选', insufficient_input: '拟合或评价条件不足', failed: '寻优发生程序或服务异常', cancelled: '寻优已取消', timed_out: '寻优已超时', unknown: '历史记录不完整' }
const count = computed(() => report.value?.candidate_counts || {})
const states = { running: '计算中', completed: '数值评价完成', infeasible: '不可行 / 未计算', failed: '异常失败', cancelled: '已取消', timed_out: '已超时' }
function metric(value) { return value == null ? '未计算' : Number(value).toPrecision(4) }
</script>
<template>
  <section v-if="visible" class="run-outcome" aria-label="本次数值任务状态">
    <h2>{{ labels[report.optimization_outcome] || '寻优结果待核对' }}</h2>
    <p>{{ report.stop_reason || run.error?.message || (report.execution_status === 'running' ? '根据逐轮持久化记录更新，暂未取得的指标不会补为零。' : '暂未取得停止原因。') }}</p>
    <p class="candidate-counts">计划上限 {{ count.planned ?? '未记录' }} · <strong>已尝试 {{ count.attempted ?? '暂未取得记录' }}</strong> · 数值评价完成 {{ count.evaluated ?? '未记录' }} · 满足约束 {{ count.feasible ?? '未记录' }} · 不可行 {{ count.infeasible ?? '未记录' }} · 异常 {{ count.failed ?? '未记录' }} · 未执行 {{ count.not_executed ?? '未记录' }}</p>
    <p>{{ count.evaluated > 0 ? '候选拟合已执行，当前没有合格赢家。' : '尚未取得有效拟合模型；建模准备完成不代表辨识成功。' }}{{ report.execution_status === 'running' ? '' : ' 正式模型评审未执行；清洗结果与已保存候选可继续查看。' }}</p>
    <p v-if="report.updated_at">最后记录：{{ report.updated_at }}<span v-if="report.execution_status === 'running'"> · 当前第 {{ count.attempted }} 组候选</span></p>
    <p v-else>历史未记录逐轮更新时间。</p>
    <details v-if="report.iterations?.length"><summary>查看 {{ report.iterations.length }} 组候选及原因</summary><div class="candidate-table"><table><thead><tr><th>轮次</th><th>实际状态</th><th>训练行 / 真实目标</th><th>验证 R²</th><th>覆盖率</th><th>结果原因</th></tr></thead><tbody><tr v-for="row in report.iterations" :key="row.round_id || row.round"><td>{{ row.candidate_index ?? row.round }}</td><td>{{ states[row.status] || row.status }}</td><td>{{ row.training_rows ?? '未计算' }} / {{ row.target_observations ?? '未计算' }}</td><td>{{ metric(row.r2) }}</td><td>{{ row.coverage == null ? '未计算' : `${(row.coverage * 100).toFixed(2)}%` }}</td><td>{{ row.reason_message || row.rejection_reason || row.error || (row.feasible ? '满足约束' : '暂未取得原因') }}</td></tr></tbody></table></div></details>
  </section>
</template>
<style scoped>
.run-outcome{padding:18px 22px;margin:0 0 20px;background:#fffbf2;border:1px solid #e7d6af;border-radius:12px;line-height:1.7;color:#594c33;min-width:0}.run-outcome h2{font-size:17px;margin:0 0 8px}.run-outcome p{font-size:13px;margin:6px 0;overflow-wrap:anywhere}.run-outcome summary{cursor:pointer;font-weight:600}.candidate-table{overflow:auto;max-height:400px}table{border-collapse:collapse;width:100%;font-size:12px;text-align:left}th,td{padding:8px 10px;border-bottom:1px solid #e9dfcd;min-width:65px}td:last-child{min-width:210px}
</style>
