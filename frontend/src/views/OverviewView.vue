<script setup>
import { computed } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import IndustrialTwinPanel from '../components/IndustrialTwinPanel.vue'
import { formatNumber, requirementCoverage } from '../data/projectData'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'
import { buildSceneState } from '../composables/useSceneBinding'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['navigate', 'notify'])

const { latestRun, pipelineError: loadError } = useLatestPipelineRun()
const sceneState = computed(() => buildSceneState(props.project, latestRun.value))
const result = computed(() => latestRun.value?.results ?? {})
const standard = computed(() => result.value.standardization ?? {})
const cleaning = computed(() => result.value.cleaning ?? {})
const modeling = computed(() => result.value.modeling ?? {})
const optimization = computed(() => result.value.optimization ?? {})
const review = computed(() => result.value.review ?? {})
const testMetrics = computed(() => modeling.value.metrics?.test ?? {})
const candidateBars = computed(() => (optimization.value.iterations ?? []).filter((item) => item.status === 'completed').map((item) => ({ ...item, height: Math.max(4, Math.min(100, (Number(item.r2) + 0.05) * 95)) })))
const bestR2 = computed(() => Number(testMetrics.value.r2 ?? 0))
const selectedRate = computed(() => ((Number(cleaning.value.modeling_row_count ?? 0) / Math.max(Number(cleaning.value.cleaned_row_count ?? 0), 1)) * 100).toFixed(1))
const fieldCount = computed(() => standard.value.mapping?.mappings?.length ?? 0)
const updatedTime = computed(() => latestRun.value?.updated_at ? new Date(latestRun.value.updated_at).toLocaleTimeString('zh-CN', { hour12: false }) : '等待运行')
const activity = computed(() => (latestRun.value?.stages ?? []).slice().reverse().slice(0, 4).map((stage) => ({
  time: stage.finished_at ? new Date(stage.finished_at).toLocaleTimeString('zh-CN', { hour12: false }) : updatedTime.value,
  title: `${stage.label}${stage.status === 'completed' ? '完成' : '未完成'}`,
  detail: stage.message,
  tone: stage.status === 'completed' ? 'success' : stage.status === 'failed' ? 'warning' : 'info',
})))
const pathByStage = { standardization: '/standard-check/', cleaning: '/standard-check/', selection: '/data-selection/', modeling: '/identification-modeling/', optimization: '/closed-loop-optimization/', review: '/report-export/', report: '/report-export/' }
const dashboardWorkflow = computed(() => (latestRun.value?.stages ?? []).map((stage, index) => ({
  index: String(index + 1).padStart(2, '0'),
  label: stage.label,
  path: pathByStage[stage.key],
  status: stage.status === 'completed' ? 'done' : stage.status === 'failed' ? 'warning' : stage.status === 'running' ? 'active' : 'pending',
  meta: stage.message,
})))

function runFullLoop() {
  emit('notify', { tone: 'info', title: '请在 Agent 中枢选择数据', message: '上传CSV后会从字段标准化开始执行完整闭环。' })
  emit('navigate', '/agent-review/')
}

</script>

<template>
  <div class="view-stack overview-view">
    <PageHeader
      eyebrow="A14 · 流程工业建模智能体"
      :title="project.name"
      description="以辨识效果为反馈信号，自动完成工业时序数据规整、动态优选、解耦辨识与预处理策略闭环寻优。"
    >
      <template #actions>
        <button class="btn btn-secondary" type="button" @click="emit('navigate', '/agent-review/')">
          <AppIcon name="spark" />打开 Agent 中枢
        </button>
        <button class="btn btn-primary" type="button" @click="runFullLoop">
          <AppIcon name="play" />运行完整闭环
        </button>
      </template>
    </PageHeader>

    <section class="hero-panel" aria-labelledby="hero-title">
      <div class="hero-copy">
        <div class="hero-meta">
          <StatusPill tone="success" dot>算法服务在线</StatusPill>
          <StatusPill tone="brand">{{ latestRun ? '实时任务' : project.badge }}</StatusPill>
          <span>{{ latestRun?.run_id ?? project.code }}</span>
        </div>
        <h2 id="hero-title">让高价值动态样本，从海量稳态数据中自动浮现</h2>
        <p v-if="latestRun">Agent 已对 {{ latestRun.original_name }} 完成 {{ latestRun.stages.length }} 个真实阶段，识别场景为 {{ sceneState.data_scene.display_name }}，全部结果来自任务 {{ latestRun.run_id }}。</p>
        <p v-else>{{ loadError || '正在读取最近一次真实任务…' }}</p>
        <div class="hero-value-row">
          <div><span>必需字段覆盖率</span><strong>{{ ((standard.mapping?.required_coverage ?? 0) * 100).toFixed(0) }}%</strong></div>
          <div><span>建模数据保留率</span><strong>{{ selectedRate }}%</strong></div>
          <div><span>寻优综合得分</span><strong>{{ optimization.best_score ?? '—' }}</strong></div>
        </div>
      </div>
      <div class="hero-orbit" aria-label="Agent 闭环运行状态">
        <div class="orbit-ring orbit-ring-outer"></div>
        <div class="orbit-ring orbit-ring-inner"></div>
        <div class="orbit-node orbit-node-a">清洗</div>
        <div class="orbit-node orbit-node-b">辨识</div>
        <div class="orbit-node orbit-node-c">反馈</div>
        <div class="orbit-core">
          <AppIcon name="spark" :size="26" />
          <strong>Agent</strong>
          <span>第 {{ optimization.best_round ?? '—' }} / {{ optimization.iterations?.length ?? '—' }} 轮</span>
        </div>
      </div>
    </section>

    <IndustrialTwinPanel :project="project" :latest-run="latestRun" :scene-state="sceneState" />

    <section class="metric-grid four-col" aria-label="核心项目指标">
      <article class="metric-card accent-cyan">
        <span class="metric-label">规整数据规模</span>
        <div class="metric-value">{{ formatNumber(cleaning.cleaned_row_count ?? 0) }} <small>行</small></div>
        <p>{{ fieldCount }} 个原始字段 · {{ modeling.selected_inputs?.length ?? 0 }} 个模型输入</p>
        <span class="metric-trend positive">任务 {{ latestRun?.status === 'completed' ? '已完成' : '等待运行' }}</span>
      </article>
      <article class="metric-card accent-violet">
        <span class="metric-label">优选动态数据</span>
        <div class="metric-value">{{ cleaning.selected_segment_count ?? 0 }} <small>段</small></div>
        <p>建模保留 {{ formatNumber(cleaning.modeling_row_count ?? 0) }} 行</p>
        <span class="metric-trend positive">质量评分 {{ cleaning.overall_score ?? '—' }}</span>
      </article>
      <article class="metric-card accent-blue">
        <span class="metric-label">当前最佳 R²</span>
        <div class="metric-value">{{ bestR2.toFixed(3) }}</div>
        <p>RMSE {{ Number(testMetrics.rmse ?? 0).toFixed(3) }}</p>
        <span class="metric-trend positive">最优候选第 {{ optimization.best_round ?? '—' }} 轮</span>
      </article>
      <article class="metric-card accent-amber">
        <span class="metric-label">交付状态</span>
        <div class="metric-value metric-value-text">{{ review.passed ? '通过' : '待复核' }}</div>
        <p>{{ review.conclusion ?? '尚无评审结果' }}</p>
        <span class="metric-trend" :class="review.passed ? 'positive' : 'warning'">{{ review.blockers?.length ?? 0 }} 项阻断 · {{ review.warnings?.length ?? 0 }} 项警告</span>
      </article>
    </section>

    <section class="panel workflow-panel">
      <div class="section-heading">
        <div>
          <span class="section-kicker">端到端工作流</span>
          <h2>从用户指令到高质量数据交付</h2>
        </div>
        <div class="section-heading-meta"><span class="live-dot"></span>最近更新 {{ updatedTime }}</div>
      </div>
      <div class="workflow-rail">
        <button
          v-for="step in dashboardWorkflow"
          :key="step.index"
          class="workflow-step"
          :class="`is-${step.status}`"
          type="button"
          @click="emit('navigate', step.path)"
        >
          <span class="workflow-index">
            <AppIcon v-if="step.status === 'done'" name="check" :size="16" />
            <span v-else>{{ step.index }}</span>
          </span>
          <span class="workflow-copy"><strong>{{ step.label }}</strong><small>{{ step.meta }}</small></span>
          <AppIcon name="chevron" :size="16" class="workflow-chevron" />
        </button>
      </div>
    </section>

    <div class="content-grid content-grid-7-5">
      <section class="panel model-compare-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">真实候选对比</span><h2>闭环寻优三轮模型表现</h2></div>
          <StatusPill tone="success">最佳策略已锁定</StatusPill>
        </div>
        <div class="chart-legend"><span><i class="legend-dot raw"></i>测试 R²</span><span><i class="legend-dot score"></i>综合得分</span></div>
        <div class="bar-comparison" role="img" aria-label="闭环寻优候选模型R²对比">
          <div class="chart-y-labels"><span>1.0</span><span>0.8</span><span>0.6</span><span>0.4</span><span>0.2</span></div>
          <div class="chart-grid-lines"></div>
          <div v-for="item in candidateBars" :key="item.round" class="bar-group" :class="{ 'is-best': item.round === optimization.best_round }">
            <div v-if="item.round === optimization.best_round" class="best-flag">BEST</div>
            <div class="bar-value">{{ Number(item.r2).toFixed(3) }}</div>
            <div class="bar" :class="item.round === optimization.best_round ? 'best-bar' : item.round === 1 ? 'raw-bar' : 'clean-bar'" :style="{ height: `${item.height}%` }"></div>
            <span>第 {{ item.round }} 轮</span>
          </div>
        </div>
        <div class="model-metric-strip">
          <div><span>最佳 R²</span><strong>{{ bestR2.toFixed(3) }}</strong></div>
          <div><span>RMSE</span><strong>{{ Number(testMetrics.rmse ?? 0).toFixed(3) }}</strong></div>
          <div><span>MAE</span><strong>{{ Number(testMetrics.mae ?? 0).toFixed(3) }}</strong></div>
          <div><span>最优参数</span><strong>Top {{ optimization.best_parameters?.top_k ?? '—' }} · Lag {{ optimization.best_parameters?.max_lag ?? '—' }}</strong></div>
        </div>
      </section>

      <section class="panel activity-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">实时运行轨迹</span><h2>Agent 执行事件</h2></div>
          <button class="text-button" type="button" @click="emit('navigate', '/agent-review/')">查看全部 <AppIcon name="arrow" :size="15" /></button>
        </div>
        <ol class="activity-list">
          <li v-for="item in activity" :key="item.time + item.title">
            <span class="activity-marker" :class="`is-${item.tone}`"></span>
            <div><time>{{ item.time }}</time><strong>{{ item.title }}</strong><p>{{ item.detail }}</p></div>
          </li>
        </ol>
      </section>
    </div>

    <section class="panel coverage-panel">
      <div class="section-heading compact">
        <div><span class="section-kicker">任务能力覆盖</span><h2>赛题核心能力 7 / 7 已形成演示闭环</h2></div>
        <StatusPill tone="brand">A14 要求覆盖 100%</StatusPill>
      </div>
      <div class="coverage-grid">
        <article v-for="item in requirementCoverage" :key="item.label" class="coverage-item">
          <span class="coverage-icon"><AppIcon :name="item.icon" /></span>
          <div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div>
          <span class="coverage-check"><AppIcon name="check" :size="14" /></span>
        </article>
      </div>
    </section>
  </div>
</template>
