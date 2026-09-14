<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildSceneState } from '../composables/useSceneBinding'
import { resolveScene3DView } from '../data/scene3dRegistry'

const SceneModel3D = defineAsyncComponent(() => import('../components/SceneModel3D.vue'))

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['navigate'])
const sceneModel = ref(null)
// The project selector controls which equipment the digital-twin page opens.
// Data evidence remains visible and can be inspected explicitly when its
// detected scene differs from the selected project.
const preferredModelScope = ref('project')
const { latestRun } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(props.project, latestRun.value))
const modeling = computed(() => latestRun.value?.results?.modeling ?? {})
const cleaning = computed(() => latestRun.value?.results?.cleaning ?? {})
const sceneView = computed(() => resolveScene3DView(sceneState.value, preferredModelScope.value))
const sceneContent = computed(() => sceneView.value.descriptor)
const modelSceneState = computed(() => sceneView.value.sceneState)
const canSwitchModelScope = computed(() => Boolean(sceneState.value.data_scene.id && sceneState.value.project_scene.id && sceneState.value.data_scene.id !== sceneState.value.project_scene.id))
const modelScopeLabel = computed(() => sceneView.value.scope === 'project'
  ? sceneState.value.data_scene.id && !sceneView.value.dataHasAsset ? '项目模型 · 数据模型未安装' : '正在查看项目模型'
  : '正在查看数据模型')
const sceneNodesById = computed(() => Object.fromEntries(sceneContent.value.semantic_nodes.map((node) => [node.id, node])))
const processFlow = computed(() => sceneContent.value.flows.map(([from, to]) => ({
  label: `${sceneNodesById.value[from]?.label || from} → ${sceneNodesById.value[to]?.label || to}`,
  field: sceneNodesById.value[to]?.fields?.[0] || 'PROCESS NODE',
})))
const testMetrics = computed(() => modeling.value.metrics?.test ?? {})
const evidenceRows = computed(() => [
  { label: '当前数据场景', value: sceneState.value.data_scene.display_name, detail: sceneState.value.data_scene_status_label },
  { label: '模型输入', value: modeling.value.selected_inputs?.length ?? '—', detail: modeling.value.config?.family ?? '等待辨识' },
  { label: '独立测试 R²', value: testMetrics.value.r2 == null ? '—' : Number(testMetrics.value.r2).toFixed(3), detail: '不使用演示指标' },
  { label: '动态数据段', value: cleaning.value.selected_segment_count ?? '—', detail: `${cleaning.value.modeling_row_count ?? '—'} 行建模数据` },
])

function toggleModelScope() {
  preferredModelScope.value = sceneView.value.scope === 'data' ? 'project' : 'data'
}

watch(() => props.project.scenarioId, (next, previous) => {
  if (previous && next !== previous) preferredModelScope.value = 'project'
})
watch(() => sceneState.value.data_scene.id, (next, previous) => {
  if (previous && next !== previous) preferredModelScope.value = 'auto'
})
</script>

<template>
  <div class="view-stack twin-view">
    <PageHeader
      :eyebrow="sceneContent.eyebrow"
      :title="sceneContent.title"
      :description="sceneContent.description"
    >
      <template #actions>
        <StatusPill :tone="sceneView.usedProjectFallback ? 'warning' : latestRun ? 'success' : 'neutral'" dot>{{ modelScopeLabel }}</StatusPill>
        <button v-if="canSwitchModelScope" class="btn btn-secondary" type="button" @click="toggleModelScope">
          <AppIcon name="cube" />{{ sceneView.scope === 'data' ? '查看项目模型' : '查看数据模型' }}
        </button>
        <button class="btn btn-secondary" type="button" @click="emit('navigate', '/overview/')"><AppIcon name="dashboard" />返回驾驶舱</button>
      </template>
    </PageHeader>

    <div class="twin-layout">
      <SceneModel3D ref="sceneModel" :scene-state="modelSceneState" :latest-run="latestRun" />
      <aside class="twin-side">
        <section class="twin-context">
          <span class="section-kicker">Scene context</span>
          <h2>{{ sceneState.project_scene.display_name }}</h2>
          <p>项目预设场景，不会被上传数据覆盖。</p>
          <dl>
            <div><dt>当前数据场景</dt><dd>{{ sceneState.data_scene.display_name }}<code>{{ sceneState.data_scene.status_label }}</code></dd></div>
            <div><dt>场景绑定</dt><dd>{{ sceneState.is_mismatch ? '已分离' : '一致' }}<code>{{ sceneState.data_scene.source }}</code></dd></div>
            <div><dt>项目采样设定</dt><dd>{{ project.sample }}<code>max lag {{ project.maxLag }}</code></dd></div>
          </dl>
        </section>
        <section class="zone-list">
          <div class="section-title"><span>设备分区</span><small>由上至下</small></div>
          <ol><li v-for="(node, index) in sceneContent.semantic_nodes" :key="node.id"><button type="button" @click="sceneModel?.focusNode(node.id)"><span>{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ node.label }}</strong><small>{{ node.mesh_name }}</small></button></li></ol>
        </section>
      </aside>
    </div>

    <section class="evidence-strip" aria-label="当前任务证据">
      <article v-for="item in evidenceRows" :key="item.label"><span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.detail }}</small></article>
    </section>

    <section class="process-story">
      <div class="story-copy"><span class="section-kicker">Process narrative</span><h2>从工艺结构到数据证据</h2><p>三维模型只用于解释设备拓扑和变量关系；所有数值仍来自当前 CSV 流水线，不以动画或示意模型替代真实运行结果。</p></div>
      <ol class="story-flow"><li v-for="(step, index) in processFlow" :key="step.label"><span>{{ index + 1 }}</span><div><strong>{{ step.label }}</strong><small>{{ step.field }}</small></div><AppIcon v-if="index < processFlow.length - 1" name="arrow" :size="16" /></li></ol>
    </section>
  </div>
</template>

<style scoped>
.twin-view { --twin-ink:#16202b; --twin-muted:#667482; }
.twin-layout { display:grid;grid-template-columns:minmax(0,1fr) 282px;gap:14px;align-items:stretch;animation:reveal .62s cubic-bezier(.16,1,.3,1) both }.twin-side{display:grid;gap:12px}.twin-context,.zone-list{padding:20px;border:1px solid var(--line);border-radius:12px;background:#fff}.twin-context h2{margin-top:9px;color:var(--twin-ink);font-size:21px;letter-spacing:-.025em}.twin-context>p{margin-top:5px;color:var(--twin-muted);font-size:10px}.twin-context dl{display:grid;gap:0;margin-top:20px}.twin-context dl>div{padding:12px 0;border-top:1px solid #edf1f5}.twin-context dt{color:#84909c;font-size:9px}.twin-context dd{display:flex;justify-content:space-between;gap:8px;margin-top:5px;color:#263544;font-size:11px;font-weight:650}.twin-context code{color:#788896;font-size:8px;font-weight:500}.section-title{display:flex;justify-content:space-between;align-items:center}.section-title span{color:#263544;font-size:11px;font-weight:700}.section-title small{color:#93a0ac;font-size:8px}.zone-list ol{display:grid;gap:5px;margin:14px 0 0;padding:0;list-style:none}.zone-list li{border-bottom:1px solid #f0f3f6}.zone-list li:last-child{border-bottom:0}.zone-list button{display:grid;grid-template-columns:30px 1fr;gap:2px 8px;align-items:center;width:100%;padding:9px 0;color:#536373;text-align:left;border:0;background:transparent;cursor:pointer}.zone-list button:hover,.zone-list button:focus-visible{color:#225f8f}.zone-list button span{grid-row:1/3;color:#a0acb7;font:8px monospace}.zone-list button strong{font-size:10px;font-weight:600}.zone-list button small{overflow:hidden;color:#9aa8b4;font:7px monospace;text-overflow:ellipsis;white-space:nowrap}
.evidence-strip{display:grid;grid-template-columns:1.4fr repeat(3,1fr);overflow:hidden;border:1px solid var(--line);border-radius:12px;background:#fff;animation:reveal .62s .08s cubic-bezier(.16,1,.3,1) both}.evidence-strip article{display:grid;gap:5px;min-width:0;padding:17px 19px;border-right:1px solid var(--line-soft)}.evidence-strip article:last-child{border-right:0}.evidence-strip span{color:#7e8b98;font-size:9px}.evidence-strip strong{overflow:hidden;color:#1d2b38;font-size:17px;letter-spacing:-.02em;text-overflow:ellipsis;white-space:nowrap;font-variant-numeric:tabular-nums}.evidence-strip small{color:#98a3ad;font-size:8px}
.process-story{display:grid;grid-template-columns:minmax(260px,.7fr) minmax(0,1.3fr);gap:42px;align-items:center;padding:28px 30px 31px;border:1px solid var(--line);border-radius:12px;background:#fff;animation:reveal .62s .16s cubic-bezier(.16,1,.3,1) both}.story-copy h2{margin-top:8px;color:#16202b;font-size:22px;letter-spacing:-.03em}.story-copy p{max-width:54ch;margin-top:8px;color:#667482;font-size:10px;line-height:1.7}.story-flow{display:grid;grid-template-columns:repeat(4,1fr);margin:0;padding:0;list-style:none}.story-flow li{position:relative;display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:center;min-width:0;padding-right:18px}.story-flow li>span{display:grid;place-items:center;width:24px;height:24px;color:#315f87;font:700 8px monospace;border:1px solid #cbdce9;border-radius:6px;background:#f2f7fa}.story-flow strong,.story-flow small{display:block}.story-flow strong{overflow:hidden;color:#31404e;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.story-flow small{margin-top:3px;color:#a0aab4;font:7px monospace}.story-flow .app-icon{position:absolute;right:3px;color:#b5c0ca}
@keyframes reveal{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:1040px){.twin-layout{grid-template-columns:1fr}.twin-side{grid-template-columns:1fr 1fr}.evidence-strip{grid-template-columns:repeat(2,1fr)}.evidence-strip article:nth-child(2){border-right:0}.evidence-strip article:nth-child(-n+2){border-bottom:1px solid var(--line-soft)}.process-story{grid-template-columns:1fr}}
@media(max-width:680px){.twin-side{grid-template-columns:1fr}.evidence-strip{grid-template-columns:1fr}.evidence-strip article{border-right:0;border-bottom:1px solid var(--line-soft)}.story-flow{grid-template-columns:1fr 1fr;gap:18px}.process-story{padding:22px}.page-heading-actions .status-pill{display:none}}
@media(prefers-reduced-motion:reduce){.twin-layout,.evidence-strip,.process-story{animation:none}}
</style>
