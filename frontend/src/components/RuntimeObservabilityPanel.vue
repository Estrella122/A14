<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { executionStatus } from '../utils/executionStatus'
import { SCORE_DIMENSIONS, artifactChain, capabilityCards, dagNodes, executorHighlights } from '../utils/runtimeObservability'

const props = defineProps({ runtime: { type: Object, default: () => ({}) } })

const capabilities = computed(() => capabilityCards(props.runtime))
const nodes = computed(() => dagNodes(props.runtime))
const artifacts = computed(() => artifactChain(props.runtime))
const loading = computed(() => props.runtime?.skill_loading ?? {})
const capabilityTone = { selected: 'success', deferred: 'warning', blocked: 'warning', skipped: 'neutral' }
const capabilityText = { selected: '已选择', deferred: '等待上游依赖', blocked: '前置条件不足', skipped: '未选择' }
const readinessText = { executable: '可执行', deferred: '等待上游依赖', blocked: '前置条件不足' }

function score(value) { return Number(value ?? 0).toFixed(3) }
function metric(value, kind) {
  if (kind === 'percent') return `${(Number(value) * 100).toFixed(2)}%`
  return typeof value === 'number' ? (Math.abs(value) < 10 && !Number.isInteger(value) ? value.toFixed(5) : value) : value
}
</script>

<template>
  <section v-if="capabilities.length || nodes.length" class="panel observability-panel">
    <div class="section-heading">
      <div><span class="section-kicker">RUNTIME DECISION OBSERVABILITY</span><h2>能力选择与执行依据</h2><p>查看为什么选择能力、依赖由谁补齐，以及最终状态为何成立。</p></div>
      <div class="observation-stats"><span><strong>{{ capabilities.filter((item) => item.ui_status === 'selected').length }}</strong>已选择</span><span><strong>{{ nodes.length }}</strong>Executor</span><span><strong>{{ artifacts.length }}</strong>Artifact</span></div>
    </div>

    <div class="capability-grid">
      <details v-for="capability in capabilities" :key="capability.id" class="capability-card" :class="`is-${capability.ui_status}`">
        <summary>
          <span class="capability-mark"><AppIcon :name="capability.ui_status === 'selected' ? 'check' : capability.ui_status === 'blocked' ? 'alert' : 'clock'" /></span>
          <span><strong>{{ capability.name }}</strong><code>{{ capability.id }}</code></span>
          <span class="capability-score"><small>Score</small>{{ score(capability.score) }}</span>
          <StatusPill :tone="capabilityTone[capability.ui_status]">{{ capabilityText[capability.ui_status] }}</StatusPill>
          <AppIcon name="chevron" :size="14" />
        </summary>
        <p class="decision-reason">{{ capability.reason }}</p>
        <div class="score-grid">
          <div v-for="dimension in SCORE_DIMENSIONS" :key="dimension[0]"><span>{{ dimension[1] }}</span><strong>{{ score(capability[dimension[0]]) }}</strong><i><b :style="{ width: `${Number(capability[dimension[0]] ?? 0) * 100}%` }"></b></i></div>
        </div>
        <div v-if="capability.required_artifacts.length" class="readiness-block">
          <strong>依赖产物 <em>{{ Math.round(Number(capability.artifact_readiness_score ?? 0) * 100) }}%</em></strong>
          <span v-for="artifact in capability.required_artifacts" :key="artifact" :class="{ missing: capability.missing_artifacts.includes(artifact) }"><AppIcon :name="capability.missing_artifacts.includes(artifact) ? 'clock' : 'check'" :size="12" />{{ artifact }}<small v-if="capability.producible_artifacts?.includes(artifact)">等待上游生成</small></span>
        </div>
        <div v-if="capability.missing_contract_fields.length" class="contract-block"><strong>前置合同缺失</strong><code v-for="field in capability.missing_contract_fields" :key="field">{{ field }}</code></div>
        <div v-if="Object.keys(capability.preconditions ?? {}).length" class="preconditions"><strong>数据前置</strong><span v-for="(ready, name) in capability.preconditions" :key="name"><AppIcon :name="ready ? 'check' : 'alert'" :size="11" />{{ name }}</span></div>
      </details>
    </div>

    <div v-if="nodes.length" class="runtime-dag">
      <div class="subheading"><span><AppIcon name="network" />Execution DAG</span><small>Artifact contract 自动依赖</small></div>
      <div class="dag-flow">
        <template v-for="(node, index) in nodes" :key="node.id">
          <details class="dag-node" :class="`is-${node.status}`">
            <summary><span><AppIcon :name="executionStatus(node.status).icon" /><strong>{{ node.executor }}</strong></span><StatusPill :tone="executionStatus(node.status).tone">{{ executionStatus(node.status).label || readinessText[node.status] }}</StatusPill></summary>
            <p>{{ node.reason }}</p>
            <div v-if="node.lifecycle.length > 1" class="lifecycle"><span v-for="(status, step) in node.lifecycle" :key="status">{{ step ? '→' : '' }} {{ readinessText[status] ?? executionStatus(status).label }}</span></div>
            <dl><div><dt>requires</dt><dd><code v-for="item in node.requires_artifacts ?? []" :key="item">{{ item }}</code><span v-if="!node.requires_artifacts?.length">无</span></dd></div><div><dt>produces</dt><dd><code v-for="item in node.produces_artifacts ?? []" :key="item">{{ item }}</code><span v-if="!node.produces_artifacts?.length">无</span></dd></div></dl>
            <div v-if="node.waiting.length" class="waiting"><strong>等待</strong><span v-for="item in node.waiting" :key="item.artifact">{{ item.producer }} 生成 {{ item.artifact }}</span></div>
            <div v-if="node.result?.missing_requirements?.length" class="contract-block"><strong>前置合同缺失</strong><code v-for="field in node.result.missing_requirements" :key="field">{{ field }}</code></div>
            <div v-if="executorHighlights(node.result).length" class="result-highlights"><span v-for="item in executorHighlights(node.result)" :key="item[0]"><small>{{ item[0] }}</small><strong>{{ metric(item[1], item[2]) }}</strong></span></div>
          </details>
          <AppIcon v-if="index < nodes.length - 1" name="arrow" class="dag-arrow" />
        </template>
      </div>
    </div>

    <div class="runtime-details">
      <details v-if="loading.selected_skill">
        <summary><span><AppIcon name="spark" />本次加载 Skill</span><strong>{{ loading.selected_skill }}</strong><AppIcon name="chevron" /></summary>
        <dl><div><dt>Capabilities</dt><dd>{{ loading.loaded_capabilities?.join(' · ') || '无' }}</dd></div><div><dt>Workflow</dt><dd>{{ loading.loaded_workflows?.join(' · ') || '无' }}</dd></div><div><dt>References</dt><dd>{{ loading.loaded_references?.join(' · ') || '无' }}</dd></div></dl>
      </details>
      <details v-if="artifacts.length">
        <summary><span><AppIcon name="database" />Artifact 链</span><strong>{{ artifacts.length }} 项</strong><AppIcon name="chevron" /></summary>
        <div class="artifact-list"><details v-for="artifact in artifacts" :key="artifact.artifact_id"><summary><code>{{ artifact.artifact_type }}</code><span>{{ artifact.producer_label }}</span><small>{{ artifact.short_hash }}</small></summary><dl><div><dt>run</dt><dd>{{ artifact.run_id }}</dd></div><div><dt>source execution</dt><dd>{{ artifact.source_execution_id || '—' }}</dd></div><div><dt>artifact id</dt><dd>{{ artifact.artifact_id }}</dd></div><div><dt>hash</dt><dd>{{ artifact.content_hash || '—' }}</dd></div><div><dt>path</dt><dd>{{ artifact.path }}</dd></div></dl></details></div>
      </details>
    </div>
  </section>
</template>

<style scoped>
.observability-panel { overflow: hidden; }
.section-heading p { margin: 5px 0 0; color: #64748b; font-size: 11px; }
.observation-stats { display: flex; gap: 8px; }.observation-stats span { min-width: 68px; padding: 8px; border: 1px solid #dbeafe; border-radius: 9px; color: #64748b; background: #fff; font-size: 8px; text-align: center; }.observation-stats strong { display: block; color: #1d4ed8; font-size: 17px; }
.capability-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px; padding: 15px 20px; border-top: 1px solid #edf2f7; }
.capability-card { border: 1px solid #dce5f0; border-radius: 10px; background: #fff; }.capability-card.is-selected { border-color: #86cbae; box-shadow: inset 3px 0 #10b981; }.capability-card.is-deferred,.capability-card.is-blocked { border-color: #f1c46f; box-shadow: inset 3px 0 #f59e0b; }.capability-card.is-skipped { opacity: .76; }
.capability-card > summary { display: grid; grid-template-columns: 28px minmax(0,1fr) 58px auto 14px; gap: 8px; align-items: center; padding: 11px; list-style: none; cursor: pointer; }.capability-card summary::-webkit-details-marker,.dag-node summary::-webkit-details-marker,.runtime-details summary::-webkit-details-marker,.artifact-list summary::-webkit-details-marker { display:none; }
.capability-mark { display:grid;place-items:center;width:27px;height:27px;border-radius:8px;color:#2563eb;background:#eff6ff}.capability-card summary strong,.capability-card summary code { display:block }.capability-card summary strong { color:#1e293b;font-size:11px }.capability-card summary code { margin-top:2px;color:#94a3b8;font-size:8px }.capability-score { color:#1e40af;font:700 12px monospace;text-align:right}.capability-score small { display:block;color:#94a3b8;font:7px sans-serif }
.decision-reason { margin:0 12px 10px 47px;color:#475569;font-size:9px;line-height:1.55}.score-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin:0 11px 10px;padding:9px;border-radius:8px;background:#f8fafc}.score-grid div { display:grid;grid-template-columns:1fr auto;gap:4px;color:#64748b;font-size:8px}.score-grid strong { color:#334155;font:700 8px monospace}.score-grid i { grid-column:1/-1;height:3px;overflow:hidden;border-radius:4px;background:#e2e8f0}.score-grid b { display:block;height:100%;background:#3b82f6}
.readiness-block,.preconditions { display:flex;flex-wrap:wrap;gap:5px;margin:0 11px 10px}.readiness-block > strong,.preconditions > strong { width:100%;color:#334155;font-size:8px}.readiness-block em { color:#2563eb;font-style:normal}.readiness-block > span,.preconditions > span { display:inline-flex;align-items:center;gap:3px;padding:3px 5px;border-radius:5px;color:#047857;background:#ecfdf5;font:7px monospace}.readiness-block > span.missing { color:#b45309;background:#fffbeb}.readiness-block small { color:inherit;font:6px sans-serif}.contract-block { display:flex;align-items:center;flex-wrap:wrap;gap:5px;margin:0 11px 10px;padding:7px;border:1px solid #fed7aa;border-radius:7px;background:#fff7ed}.contract-block strong { color:#9a3412;font-size:8px}.contract-block code { color:#c2410c;font-size:7px}
.runtime-dag { padding:4px 20px 17px;border-top:1px solid #edf2f7}.subheading { display:flex;justify-content:space-between;align-items:center;padding:13px 0 9px}.subheading span { display:flex;align-items:center;gap:6px;color:#1e293b;font-weight:700;font-size:12px}.subheading small { color:#94a3b8;font-size:8px}.dag-flow { display:flex;align-items:stretch;gap:7px;overflow-x:auto;padding-bottom:4px}.dag-node { flex:1 0 185px;max-width:270px;border:1px solid #dce5f0;border-radius:9px;background:#fbfdff}.dag-node.is-success { border-color:#86cbae}.dag-node.is-partial,.dag-node.is-deferred,.dag-node.is-blocked { border-color:#f1c46f}.dag-node.is-failed { border-color:#fecaca}.dag-node > summary { display:flex;align-items:center;justify-content:space-between;gap:6px;padding:9px;list-style:none;cursor:pointer}.dag-node > summary > span { display:flex;align-items:center;gap:5px;text-transform:capitalize}.dag-node > p { margin:0;padding:0 9px 8px;color:#64748b;font-size:8px;line-height:1.45}.dag-arrow { flex:0 0 auto;align-self:center;color:#94a3b8}.dag-node dl { margin:0 8px 8px;padding:7px;border-radius:6px;background:#f1f5f9;font-size:7px}.dag-node dl div { margin:3px 0}.dag-node dt { color:#94a3b8}.dag-node dd { display:flex;flex-wrap:wrap;gap:3px;margin:2px 0;color:#475569}.dag-node dd code { padding:2px 3px;border-radius:3px;background:#fff}.lifecycle,.waiting { display:flex;flex-wrap:wrap;gap:4px;margin:0 8px 8px;color:#b45309;font-size:7px}.waiting { padding:6px;border-radius:6px;background:#fffbeb}.waiting strong { width:100%}.result-highlights { display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin:0 8px 8px}.result-highlights span { padding:6px;border:1px solid #e2e8f0;border-radius:6px}.result-highlights small,.result-highlights strong { display:block}.result-highlights small { color:#94a3b8;font-size:7px}.result-highlights strong { margin-top:2px;color:#1e3a5f;font:700 10px monospace}
.runtime-details { display:grid;grid-template-columns:1fr 1fr;gap:9px;padding:14px 20px;border-top:1px solid #edf2f7;background:#f8fafc}.runtime-details > details { border:1px solid #dce5f0;border-radius:9px;background:#fff}.runtime-details > details > summary { display:flex;align-items:center;gap:7px;padding:10px;list-style:none;cursor:pointer}.runtime-details > details > summary span { display:flex;align-items:center;gap:5px;color:#334155;font-size:10px}.runtime-details > details > summary strong { margin-left:auto;color:#2563eb;font-size:9px}.runtime-details > details > dl { margin:0 10px 10px;padding:8px;border-radius:7px;background:#f8fafc;font-size:8px}.runtime-details dl div { display:grid;grid-template-columns:86px 1fr;gap:7px;margin:4px 0}.runtime-details dt { color:#94a3b8}.runtime-details dd { margin:0;color:#334155;overflow-wrap:anywhere}.artifact-list { max-height:240px;padding:0 8px 8px;overflow:auto}.artifact-list > details { border-top:1px solid #edf2f7}.artifact-list > details > summary { display:grid;grid-template-columns:1fr 1fr auto;gap:5px;padding:7px 2px;list-style:none;cursor:pointer;font-size:7px}.artifact-list summary span { color:#475569}.artifact-list summary small { color:#94a3b8;font-family:monospace}.artifact-list dl { margin:0 0 7px;padding:7px;border-radius:6px;background:#f8fafc;font-size:7px}
@media(max-width:800px){.capability-grid{grid-template-columns:1fr}.runtime-details{grid-template-columns:1fr}.observation-stats{display:none}}
</style>
