<script setup>
import { computed } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import SceneModel3D from '../components/SceneModel3D.vue'
import StatusPill from '../components/StatusPill.vue'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildSceneState } from '../composables/useSceneBinding'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['navigate'])
const { latestRun } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(props.project, latestRun.value))
const modeling = computed(() => latestRun.value?.results?.modeling ?? {})
const cleaning = computed(() => latestRun.value?.results?.cleaning ?? {})
const sceneContent = computed(() => ({
  blast_furnace: {
    eyebrow: 'IRONMAKING PROCESS', title: '高炉炼铁过程结构', description: '以鼓风、富氧和装料条件为输入，观察炉内热状态与铁水硅含量的动态响应。',
    zones: ['炉顶装料与煤气', '炉身还原区', '炉腹软熔带', '炉缸与出铁口'],
    flow: ['矿石与焦炭装入', '热风与煤粉送入', '还原熔融反应', '铁水质量化验'],
  },
  debutanizer_column: {
    eyebrow: 'REFINERY SEPARATION', title: '脱丁烷精馏过程结构', description: '展示进料、塔板分离、塔顶冷凝回流与塔底再沸之间的物料和能量联系。',
    zones: ['塔顶冷凝器', '回流罐与回流线', '精馏塔板区', '塔底再沸器'],
    flow: ['混合进料进入', '轻重组分分离', '塔顶冷凝回流', '塔底 C4 质量预测'],
  },
  industrial_dryer: {
    eyebrow: 'THERMAL DRYING', title: '连续热风干燥过程结构', description: '呈现湿料进给、热风换热、滚筒输送和产品含水率变化的多变量耦合关系。',
    zones: ['湿料进料斗', '空气加热器', '回转干燥筒', '产品出料端'],
    flow: ['湿料连续进入', '热风建立温差', '筒内传热传质', '含水率在线估计'],
  },
}[props.project.scenarioId] ?? {}))
const testMetrics = computed(() => modeling.value.metrics?.test ?? {})
const evidenceRows = computed(() => [
  { label: '当前数据场景', value: sceneState.value.data_scene.display_name, detail: sceneState.value.data_scene_status_label },
  { label: '模型输入', value: modeling.value.selected_inputs?.length ?? '—', detail: modeling.value.config?.family ?? '等待辨识' },
  { label: '独立测试 R²', value: testMetrics.value.r2 == null ? '—' : Number(testMetrics.value.r2).toFixed(3), detail: '不使用演示指标' },
  { label: '动态数据段', value: cleaning.value.selected_segment_count ?? '—', detail: `${cleaning.value.modeling_row_count ?? '—'} 行建模数据` },
])
</script>

<template>
  <div class="view-stack twin-view">
    <PageHeader
      :eyebrow="sceneContent.eyebrow"
      :title="sceneContent.title"
      :description="sceneContent.description"
    >
      <template #actions>
        <StatusPill :tone="latestRun ? 'success' : 'neutral'" dot>{{ latestRun ? '真实任务测点' : '结构示意模式' }}</StatusPill>
        <button class="btn btn-secondary" type="button" @click="emit('navigate', '/overview/')"><AppIcon name="dashboard" />返回驾驶舱</button>
      </template>
    </PageHeader>

    <div class="twin-layout">
      <SceneModel3D :project="project" :latest-run="latestRun" />
      <aside class="twin-side">
        <section class="twin-context">
          <span class="section-kicker">Scene context</span>
          <h2>{{ project.shortName }}</h2>
          <p>{{ project.scene }}</p>
          <dl>
            <div><dt>被控目标</dt><dd>{{ project.target }}<code>{{ project.targetTag }}</code></dd></div>
            <div><dt>主要输入</dt><dd>{{ project.mv }}<code>{{ project.mvTag }}</code></dd></div>
            <div><dt>采样周期</dt><dd>{{ project.sample }}<code>max lag {{ project.maxLag }}</code></dd></div>
          </dl>
        </section>
        <section class="zone-list">
          <div class="section-title"><span>设备分区</span><small>由上至下</small></div>
          <ol><li v-for="(zone, index) in sceneContent.zones" :key="zone"><span>{{ String(index + 1).padStart(2, '0') }}</span><strong>{{ zone }}</strong></li></ol>
        </section>
      </aside>
    </div>

    <section class="evidence-strip" aria-label="当前任务证据">
      <article v-for="item in evidenceRows" :key="item.label"><span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.detail }}</small></article>
    </section>

    <section class="process-story">
      <div class="story-copy"><span class="section-kicker">Process narrative</span><h2>从工艺结构到数据证据</h2><p>三维模型只用于解释设备拓扑和变量关系；所有数值仍来自当前 CSV 流水线，不以动画或示意模型替代真实运行结果。</p></div>
      <ol class="story-flow"><li v-for="(step, index) in sceneContent.flow" :key="step"><span>{{ index + 1 }}</span><div><strong>{{ step }}</strong><small>{{ index === sceneContent.flow.length - 1 ? project.targetTag : 'PROCESS NODE' }}</small></div><AppIcon v-if="index < sceneContent.flow.length - 1" name="arrow" :size="16" /></li></ol>
    </section>
  </div>
</template>

<style scoped>
.twin-view { --twin-ink:#16202b; --twin-muted:#667482; }
.twin-layout { display:grid;grid-template-columns:minmax(0,1fr) 282px;gap:14px;align-items:stretch;animation:reveal .62s cubic-bezier(.16,1,.3,1) both }.twin-side{display:grid;gap:12px}.twin-context,.zone-list{padding:20px;border:1px solid var(--line);border-radius:12px;background:#fff}.twin-context h2{margin-top:9px;color:var(--twin-ink);font-size:21px;letter-spacing:-.025em}.twin-context>p{margin-top:5px;color:var(--twin-muted);font-size:10px}.twin-context dl{display:grid;gap:0;margin-top:20px}.twin-context dl>div{padding:12px 0;border-top:1px solid #edf1f5}.twin-context dt{color:#84909c;font-size:9px}.twin-context dd{display:flex;justify-content:space-between;gap:8px;margin-top:5px;color:#263544;font-size:11px;font-weight:650}.twin-context code{color:#788896;font-size:8px;font-weight:500}.section-title{display:flex;justify-content:space-between;align-items:center}.section-title span{color:#263544;font-size:11px;font-weight:700}.section-title small{color:#93a0ac;font-size:8px}.zone-list ol{display:grid;gap:5px;margin:14px 0 0;padding:0;list-style:none}.zone-list li{display:grid;grid-template-columns:30px 1fr;gap:8px;align-items:center;padding:9px 0;color:#536373;border-bottom:1px solid #f0f3f6;font-size:10px}.zone-list li:last-child{border-bottom:0}.zone-list li span{color:#a0acb7;font:8px monospace}.zone-list li strong{font-weight:600}
.evidence-strip{display:grid;grid-template-columns:1.4fr repeat(3,1fr);overflow:hidden;border:1px solid var(--line);border-radius:12px;background:#fff;animation:reveal .62s .08s cubic-bezier(.16,1,.3,1) both}.evidence-strip article{display:grid;gap:5px;min-width:0;padding:17px 19px;border-right:1px solid var(--line-soft)}.evidence-strip article:last-child{border-right:0}.evidence-strip span{color:#7e8b98;font-size:9px}.evidence-strip strong{overflow:hidden;color:#1d2b38;font-size:17px;letter-spacing:-.02em;text-overflow:ellipsis;white-space:nowrap;font-variant-numeric:tabular-nums}.evidence-strip small{color:#98a3ad;font-size:8px}
.process-story{display:grid;grid-template-columns:minmax(260px,.7fr) minmax(0,1.3fr);gap:42px;align-items:center;padding:28px 30px 31px;border:1px solid var(--line);border-radius:12px;background:#fff;animation:reveal .62s .16s cubic-bezier(.16,1,.3,1) both}.story-copy h2{margin-top:8px;color:#16202b;font-size:22px;letter-spacing:-.03em}.story-copy p{max-width:54ch;margin-top:8px;color:#667482;font-size:10px;line-height:1.7}.story-flow{display:grid;grid-template-columns:repeat(4,1fr);margin:0;padding:0;list-style:none}.story-flow li{position:relative;display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:center;min-width:0;padding-right:18px}.story-flow li>span{display:grid;place-items:center;width:24px;height:24px;color:#315f87;font:700 8px monospace;border:1px solid #cbdce9;border-radius:6px;background:#f2f7fa}.story-flow strong,.story-flow small{display:block}.story-flow strong{overflow:hidden;color:#31404e;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.story-flow small{margin-top:3px;color:#a0aab4;font:7px monospace}.story-flow .app-icon{position:absolute;right:3px;color:#b5c0ca}
@keyframes reveal{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:1040px){.twin-layout{grid-template-columns:1fr}.twin-side{grid-template-columns:1fr 1fr}.evidence-strip{grid-template-columns:repeat(2,1fr)}.evidence-strip article:nth-child(2){border-right:0}.evidence-strip article:nth-child(-n+2){border-bottom:1px solid var(--line-soft)}.process-story{grid-template-columns:1fr}}
@media(max-width:680px){.twin-side{grid-template-columns:1fr}.evidence-strip{grid-template-columns:1fr}.evidence-strip article{border-right:0;border-bottom:1px solid var(--line-soft)}.story-flow{grid-template-columns:1fr 1fr;gap:18px}.process-story{padding:22px}.page-heading-actions .status-pill{display:none}}
@media(prefers-reduced-motion:reduce){.twin-layout,.evidence-strip,.process-story{animation:none}}
</style>
