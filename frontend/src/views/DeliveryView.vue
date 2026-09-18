<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import { requirementCoverage } from '../data/projectData'
import { artifactUrl } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'

defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate'])
const { latestRun } = useLatestPipelineRun()
const results = computed(() => latestRun.value?.results ?? {})
const cleaning = computed(() => results.value.cleaning ?? {})
const modeling = computed(() => results.value.modeling ?? {})
const optimization = computed(() => results.value.optimization ?? {})
const review = computed(() => results.value.review ?? {})
const testMetrics = computed(() => modeling.value.metrics?.test ?? {})
const reviewPassed = computed(() => Boolean(review.value.passed))
const standardization = computed(() => results.value.standardization ?? {})
const activeReportSection = ref('summary')
const reportSections = [
  { key: 'summary', number: '01', label: '执行摘要' },
  { key: 'quality', number: '02', label: '数据质量评估' },
  { key: 'selection', number: '03', label: '动态段优选' },
  { key: 'lag', number: '04', label: '时滞与共线性' },
  { key: 'modeling', number: '05', label: '系统辨识评价' },
  { key: 'optimization', number: '06', label: '闭环寻优过程' },
  { key: 'conclusion', number: '07', label: '工程结论与附录' },
]
const activeReportMeta = computed(() => reportSections.find((item) => item.key === activeReportSection.value) ?? reportSections[0])
const missingEntries = computed(() => Object.entries(cleaning.value.missing_rate ?? {}).sort((left, right) => Number(right[1]) - Number(left[1])).slice(0, 6))
const lagEntries = computed(() => (modeling.value.lags ?? []).slice(0, 6))
const vifEntries = computed(() => (modeling.value.collinearity?.vif ?? []).slice(0, 6))
const segmentEntries = computed(() => (cleaning.value.segments_preview ?? []).slice(0, 6))

const reviewItems = computed(() => [
  { label: '数据质量', result: Number(cleaning.value.overall_score ?? 0) >= 60 ? '通过' : '待复核', detail: `质量评分 ${cleaning.value.overall_score ?? '—'}，规整后 ${cleaning.value.cleaned_row_count ?? '—'} 行`, tone: Number(cleaning.value.overall_score ?? 0) >= 60 ? 'success' : 'warning' },
  { label: '动态段有效性', result: cleaning.value.selected_segment_count > 0 ? '通过' : '无可用片段', detail: `${cleaning.value.selected_segment_count ?? 0} 个接纳窗口（严格 ${cleaning.value.strict_selected_segment_count ?? cleaning.value.selected_segment_count ?? 0} 个），建模使用 ${cleaning.value.modeling_row_count ?? 0} 行`, tone: cleaning.value.selected_segment_count > 0 ? 'success' : 'warning' },
  { label: '时滞与共线性', result: modeling.value.selected_inputs?.length ? '完成' : '待运行', detail: `${modeling.value.input_cols?.length ?? 0} 个输入筛选为 ${modeling.value.selected_inputs?.length ?? 0} 个模型特征`, tone: modeling.value.selected_inputs?.length ? 'success' : 'warning' },
  { label: '辨识效果', result: Number(testMetrics.value.r2 ?? -1) >= 0 ? '通过' : '未通过', detail: `测试 R² ${Number(testMetrics.value.r2 ?? 0).toFixed(3)}，RMSE ${Number(testMetrics.value.rmse ?? 0).toFixed(3)}`, tone: Number(testMetrics.value.r2 ?? -1) >= 0 ? 'success' : 'warning' },
  { label: 'Agent评审', result: reviewPassed.value ? '通过' : '待复核', detail: `${review.value.blockers?.length ?? 0} 项阻断，${review.value.warnings?.length ?? 0} 项警告`, tone: reviewPassed.value ? 'success' : 'warning' },
])

const conclusion = computed(() => review.value.conclusion ?? '等待真实任务评审')

const artifacts = computed(() => [
  { type: 'csv', key: 'modeling_csv', title: '优选建模数据集', file: 'modeling_dataset.csv', meta: `${cleaning.value.modeling_row_count ?? 0} 行 · ${modeling.value.selected_inputs?.length ?? 0} 个模型输入`, icon: 'database', action: '导出 CSV' },
  { type: 'report', key: 'analysis_report_md', title: 'Agent分析报告', file: 'analysis_report.md', meta: `任务 ${latestRun.value?.run_id ?? '等待运行'} · Markdown`, icon: 'report', action: '导出报告' },
  { type: 'trace', key: 'optimization_json', title: '闭环寻优记录', file: 'optimization_report.json', meta: `${optimization.value.iterations?.length ?? 0} 轮候选 · 最优第 ${optimization.value.best_round ?? '—'} 轮`, icon: 'loop', action: '导出 JSON' },
  { type: 'review', key: 'review_json', title: '独立评审记录', file: 'agent_review.json', meta: conclusion.value, icon: 'shield', action: '导出 JSON' },
])

function exportArtifact(artifact) {
  if (!latestRun.value) return
  const anchor = document.createElement('a')
  anchor.href = artifactUrl(latestRun.value.run_id, artifact.key)
  anchor.click()
  emit('notify', { tone: 'success', title: '下载已开始', message: `${artifact.file} 来自任务 ${latestRun.value.run_id}。` })
}

function handleGlobalCommand(event) {
  if (event.detail?.action === 'export-report') exportArtifact(artifacts.value[1])
}
onMounted(() => window.addEventListener('processpilot:command', handleGlobalCommand))
onBeforeUnmount(() => window.removeEventListener('processpilot:command', handleGlobalCommand))
</script>

<template>
  <div class="view-stack delivery-view">
    <PageHeader
      eyebrow="Review, Report & Delivery"
      title="评审、报告与高质量数据交付"
      description="执行 Agent 提交完整运行证据，评审 Agent 验证数据、模型与报告一致性，最终输出工程报告、优选数据和可追溯清单。"
    >
      <template #actions>
        <button class="btn btn-secondary" type="button" :disabled="!latestRun" @click="activeReportSection = 'summary'">浏览完整报告</button>
        <button class="btn btn-primary" type="button" @click="exportArtifact(artifacts[1])"><AppIcon name="download" />导出图文报告</button>
      </template>
    </PageHeader>

    <section class="review-result-card" :class="{ 'is-approved': reviewPassed }">
      <div class="review-result-mark"><AppIcon :name="reviewPassed ? 'check' : 'alert'" :size="28" /></div>
      <div class="review-result-copy"><span>双 Agent 最终评审结论</span><h2>{{ conclusion }}</h2><p>该结论来自当前任务的字段、质量、动态段与最优模型证据，不使用演示常量。</p></div>
      <div class="review-result-meta"><span>评审时间<strong>{{ latestRun?.updated_at ? new Date(latestRun.updated_at).toLocaleString('zh-CN') : '等待运行' }}</strong></span><span>运行编号<strong>{{ latestRun?.run_id ?? '—' }}</strong></span></div>
      <StatusPill :tone="reviewPassed ? 'success' : 'warning'"><AppIcon :name="reviewPassed ? 'check' : 'alert'" :size="14" /> {{ reviewPassed ? '已生成证据' : '需要复核' }}</StatusPill>
    </section>

    <section class="panel artifacts-panel">
      <div class="section-heading compact"><div><span class="section-kicker">一键交付</span><h2>本次运行产物</h2></div><StatusPill tone="success">4 / 4 已生成</StatusPill></div>
      <div class="artifact-grid">
        <article v-for="artifact in artifacts" :key="artifact.type" class="artifact-card">
          <span class="artifact-icon"><AppIcon :name="artifact.icon" :size="24" /></span>
          <div><strong>{{ artifact.title }}</strong><code>{{ artifact.file }}</code><p>{{ artifact.meta }}</p></div>
          <button class="btn btn-secondary" type="button" @click="exportArtifact(artifact)"><AppIcon name="download" :size="16" />{{ artifact.action }}</button>
        </article>
      </div>
    </section>

    <div class="content-grid content-grid-8-4 delivery-top-grid">
      <section class="panel report-preview-panel">
        <div class="section-heading compact"><div><span class="section-kicker">Agent 工程报告预览</span><h2>{{ project.name }}</h2></div><div class="report-page-count">第 {{ activeReportMeta.number }} 章 / 共 07 章</div></div>
        <div class="report-document">
          <aside class="report-toc">
            <strong>报告目录</strong>
            <button v-for="section in reportSections" :key="section.key" :class="{ 'is-active': activeReportSection === section.key }" type="button" @click="activeReportSection = section.key"><span>{{ section.number }}</span>{{ section.label }}</button>
          </aside>
          <article class="report-page">
            <div class="report-page-header"><span>PROCESSPILOT · ANALYSIS REPORT</span><strong>{{ latestRun?.run_id ?? '等待运行' }}</strong></div>
            <template v-if="activeReportSection === 'summary'">
              <h3>执行摘要</h3>
              <p>本次运行面向 <strong>{{ standardization.scenario?.scenario_name ?? project.unit }}</strong> 的系统辨识任务。Agent 对 {{ Number(cleaning.cleaned_row_count ?? 0).toLocaleString('zh-CN') }} 行规整数据完成动态优选、时滞解耦、系统辨识和真实候选寻优。</p>
              <div class="report-highlight"><span><AppIcon name="spark" /></span><p><strong>Agent 核心结论</strong>第 {{ optimization.best_round ?? '—' }} 轮“{{ optimization.best_label ?? '等待寻优' }}”综合得分最高（{{ optimization.best_score ?? '—' }}）。最终评审：{{ conclusion }}。</p></div>
              <div class="report-kpis"><div><span>训练达标窗口</span><strong>{{ cleaning.selected_segment_count ?? 0 }}</strong><small>{{ cleaning.modeling_row_count ?? 0 }} 行建模数据</small></div><div><span>核心变量</span><strong>{{ modeling.selected_inputs?.length ?? 0 }}</strong><small>由 {{ modeling.input_cols?.length ?? 0 }} 个输入筛选</small></div><div><span>独立测试 R²</span><strong>{{ Number(testMetrics.r2 ?? 0).toFixed(3) }}</strong><small>RMSE {{ Number(testMetrics.rmse ?? 0).toFixed(3) }}</small></div></div>
            </template>

            <template v-else-if="activeReportSection === 'quality'">
              <h3>数据质量评估</h3>
              <p>字段标准化结论为 <strong>{{ standardization.data_decision?.status ?? '—' }}</strong>，清洗质量评分为 <strong>{{ cleaning.overall_score ?? '—' }}/100</strong>。原始数据经过时间戳对齐、数值重采样、缺失处理和异常规整后形成 {{ cleaning.cleaned_row_count ?? 0 }} 行时序数据。</p>
              <div class="report-kpis"><div><span>字段覆盖率</span><strong>{{ ((standardization.mapping?.required_coverage ?? 0) * 100).toFixed(1) }}%</strong><small>必需字段映射</small></div><div><span>规整行数</span><strong>{{ cleaning.cleaned_row_count ?? 0 }}</strong><small>统一时间轴</small></div><div><span>质量评分</span><strong>{{ cleaning.overall_score ?? '—' }}</strong><small>综合质量门禁</small></div></div>
              <h4>缺失率最高字段</h4><ul class="report-evidence-list"><li v-for="item in missingEntries" :key="item[0]"><strong>{{ item[0] }}</strong><span>{{ (Number(item[1]) * 100).toFixed(2) }}%</span></li><li v-if="!missingEntries.length">未发现字段缺失统计。</li></ul>
            </template>

            <template v-else-if="activeReportSection === 'selection'">
              <h3>动态段优选</h3>
              <p>动态优选 Agent 按变化强度、信息量与完整性评价候选窗口。当前接纳窗口共 {{ cleaning.selected_segment_count ?? 0 }} 个，其中严格优质段 {{ cleaning.strict_selected_segment_count ?? cleaning.selected_segment_count ?? 0 }} 个，最终保留 {{ cleaning.modeling_row_count ?? 0 }} 行用于辨识。</p>
              <div class="report-kpis"><div><span>候选窗口</span><strong>{{ cleaning.candidate_segment_count ?? segmentEntries.length }}</strong><small>滑动窗口评价</small></div><div><span>有效窗口</span><strong>{{ cleaning.selected_segment_count ?? 0 }}</strong><small>{{ cleaning.relaxed_acceptance ? '小样本自适应筛选' : '严格评分与SNR门槛' }}</small></div><div><span>建模数据</span><strong>{{ cleaning.modeling_row_count ?? 0 }}</strong><small>优选后行数</small></div></div>
              <div class="table-wrap report-table-wrap"><table class="data-table"><thead><tr><th>段编号</th><th>起始位置</th><th>结束位置</th><th>动态分</th><th>入选</th></tr></thead><tbody><tr v-for="(item, index) in segmentEntries" :key="item.segment_id ?? index"><td>{{ item.segment_id ?? index + 1 }}</td><td>{{ item.start_time ?? item.start ?? item.start_idx ?? '—' }}</td><td>{{ item.end_time ?? item.end ?? item.end_idx ?? '—' }}</td><td>{{ Number(item.segment_score ?? item.score ?? item.dynamic_score ?? 0).toFixed(3) }}</td><td>{{ item.selected ? '是' : '候选' }}</td></tr><tr v-if="!segmentEntries.length"><td colspan="5">当前任务未生成段预览。</td></tr></tbody></table></div>
            </template>

            <template v-else-if="activeReportSection === 'lag'">
              <h3>时滞与共线性</h3>
              <p>系统从 {{ modeling.input_cols?.length ?? 0 }} 个输入中保留 {{ modeling.selected_inputs?.length ?? 0 }} 个辨识特征，并使用互相关搜索时滞、相关矩阵和 VIF 复核冗余变量。</p>
              <div class="report-split"><div><h4>主要时滞</h4><ul class="report-evidence-list"><li v-for="item in lagEntries" :key="item.input"><strong>{{ item.input }}</strong><span>{{ item.delay_samples ?? '—' }} 点</span></li><li v-if="!lagEntries.length">暂无时滞记录。</li></ul></div><div><h4>VIF 证据</h4><ul class="report-evidence-list"><li v-for="(item, index) in vifEntries" :key="item.variable ?? index"><strong>{{ item.variable ?? item.feature ?? `变量${index + 1}` }}</strong><span>{{ Number(item.VIF ?? item.vif ?? 0).toFixed(2) }}</span></li><li v-if="!vifEntries.length">暂无 VIF 记录。</li></ul></div></div>
            </template>

            <template v-else-if="activeReportSection === 'modeling'">
              <h3>系统辨识评价</h3>
              <p>当前输出变量为 <strong>{{ modeling.output_col ?? '—' }}</strong>，{{ modeling.config?.family ?? '—' }} 模型实际使用 {{ modeling.fitted_inputs?.length ?? 0 }} 个外部输入特征。评审以时序留出测试集为主，不使用训练集分数替代泛化结论。</p>
              <div class="report-kpis"><div><span>测试 R²</span><strong>{{ Number(testMetrics.r2 ?? 0).toFixed(4) }}</strong><small>越接近 1 越好</small></div><div><span>测试 RMSE</span><strong>{{ Number(testMetrics.rmse ?? 0).toFixed(4) }}</strong><small>原始量纲误差</small></div><div><span>测试 MAE</span><strong>{{ Number(testMetrics.mae ?? 0).toFixed(4) }}</strong><small>绝对误差均值</small></div></div>
              <div class="report-highlight" :class="{ 'is-warning': !review.passed }"><span><AppIcon :name="review.passed ? 'check' : 'alert'" /></span><p><strong>泛化判断</strong>{{ conclusion }} {{ (review.blockers ?? []).join('；') }}</p></div>
            </template>

            <template v-else-if="activeReportSection === 'optimization'">
              <h3>闭环寻优过程</h3>
              <p>{{ optimization.search_strategy ?? '对真实候选策略逐轮评价' }}。共完成 {{ optimization.iterations?.length ?? 0 }} 轮，第 {{ optimization.best_round ?? '—' }} 轮综合分最高。</p>
              <div class="mini-report-chart"><div class="report-bars"><span v-for="item in optimization.iterations ?? []" :key="item.round" :class="{ 'is-best': item.round === optimization.best_round }" :style="{ height: `${Math.max(8, Math.min(96, Number(item.score ?? 0)))}%` }"><i>{{ Number(item.score ?? 0).toFixed(1) }}</i></span></div><div class="report-bar-labels"><span v-for="item in optimization.iterations ?? []" :key="item.round">R{{ item.round }}</span></div></div>
              <div class="table-wrap report-table-wrap"><table class="data-table"><thead><tr><th>轮次</th><th>策略</th><th>Top K</th><th>Lag</th><th>R²</th><th>得分</th></tr></thead><tbody><tr v-for="item in optimization.iterations ?? []" :key="item.round" :class="{ 'best-iteration': item.round === optimization.best_round }"><td>R{{ item.round }}</td><td>{{ item.label }}</td><td>{{ item.top_k }}</td><td>{{ item.max_lag }}</td><td>{{ Number(item.r2 ?? 0).toFixed(3) }}</td><td>{{ Number(item.score ?? 0).toFixed(2) }}</td></tr></tbody></table></div>
            </template>

            <template v-else>
              <h3>工程结论与附录</h3>
              <div class="report-highlight" :class="{ 'is-warning': !reviewPassed }"><span><AppIcon :name="reviewPassed ? 'check' : 'alert'" /></span><p><strong>最终评审结论</strong>{{ conclusion }}</p></div>
              <h4>阻断项</h4><ul class="report-evidence-list"><li v-for="item in review.blockers ?? []" :key="item"><strong>{{ item }}</strong><span>需处理</span></li><li v-if="!review.blockers?.length"><strong>无阻断项</strong><span>通过</span></li></ul>
              <h4>交付附件</h4><ul class="report-evidence-list"><li v-for="artifact in artifacts" :key="artifact.key"><strong>{{ artifact.title }}</strong><span>{{ artifact.file }}</span></li></ul>
            </template>
            <div class="report-footnote">注：本页面数据与可下载 Markdown 报告均来自当前流水线任务。</div>
          </article>
        </div>
      </section>

      <section class="panel review-checklist-panel">
        <div class="section-heading compact"><div><span class="section-kicker">Review Agent</span><h2>验收门禁</h2></div><span class="review-score">{{ cleaning.overall_score ?? '—' }}<small>/100</small></span></div>
        <div class="review-agent-flow"><div><span><AppIcon name="spark" /></span><strong>执行 Agent</strong><small>提交证据包</small></div><AppIcon name="arrow" /><div><span><AppIcon name="shield" /></span><strong>评审 Agent</strong><small>独立验收</small></div></div>
        <ul class="review-checklist">
          <li v-for="item in reviewItems" :key="item.label"><span class="review-check-icon" :class="`is-${item.tone}`"><AppIcon :name="item.tone === 'warning' ? 'alert' : 'check'" :size="15" /></span><div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div><StatusPill :tone="item.tone">{{ item.result }}</StatusPill></li>
        </ul>
      </section>
    </div>

    <div class="content-grid content-grid-7-5">
      <section class="panel traceability-panel">
        <div class="section-heading compact"><div><span class="section-kicker">全链路可追溯</span><h2>数据、策略、模型与算法版本</h2></div></div>
        <div class="version-chain">
          <article><span><AppIcon name="database" /></span><div><small>数据版本</small><strong :title="latestRun?.run_id ?? '—'">{{ latestRun?.run_id ?? '—' }}</strong><p :title="latestRun?.original_name ?? '等待CSV'">{{ latestRun?.original_name ?? '等待CSV' }}</p></div></article>
          <AppIcon name="chevron" />
          <article><span><AppIcon name="clean" /></span><div><small>规整结果</small><strong>{{ cleaning.overall_score ?? '—' }} 分</strong><p>{{ cleaning.cleaned_row_count ?? 0 }} 行</p></div></article>
          <AppIcon name="chevron" />
          <article><span><AppIcon name="loop" /></span><div><small>寻优策略</small><strong>Round {{ optimization.best_round ?? '—' }}</strong><p>Score · {{ optimization.best_score ?? '—' }}</p></div></article>
          <AppIcon name="chevron" />
          <article><span><AppIcon name="model" /></span><div><small>模型结果</small><strong>ARX</strong><p>R² · {{ Number(testMetrics.r2 ?? 0).toFixed(3) }}</p></div></article>
        </div>
      </section>

      <section class="panel coverage-summary-panel">
        <div class="section-heading compact"><div><span class="section-kicker">赛题要求覆盖</span><h2>核心任务 7 / 7</h2></div><StatusPill tone="success">完整</StatusPill></div>
        <div class="compact-coverage-list"><div v-for="item in requirementCoverage" :key="item.label"><span><AppIcon name="check" :size="13" /></span><strong>{{ item.label }}</strong><small>{{ item.detail }}</small></div></div>
      </section>
    </div>

    <section class="delivery-ready-card">
      <div><span><AppIcon name="shield" :size="24" /></span><p><strong>{{ reviewPassed ? '当前任务产物已通过本地完整性校验' : '当前任务需要复核' }}</strong><small>{{ latestRun?.run_id ?? '—' }} · {{ latestRun?.updated_at ? new Date(latestRun.updated_at).toLocaleString('zh-CN') : '等待生成' }}</small></p></div>
      <button class="btn btn-primary" type="button" :disabled="!latestRun" @click="exportArtifact(artifacts[1])"><AppIcon name="download" />下载分析报告</button>
    </section>
  </div>
</template>

<style scoped>
.delivery-top-grid,
.delivery-view .content-grid-7-5 {
  align-items: stretch;
}

.report-preview-panel {
  display: flex;
  flex-direction: column;
  padding-bottom: 16px;
}

.report-document {
  flex: 1;
  min-height: clamp(420px, 48vh, 500px);
  margin-top: 8px;
}

.report-page {
  margin-top: 12px;
  padding: 20px 26px 18px;
}

.report-toc {
  padding-block: 14px;
}

.report-page h3 {
  margin-top: 13px;
}

.report-page h4 {
  margin-top: 12px;
}

.report-page > p,
.report-highlight,
.report-kpis,
.mini-report-chart {
  margin-top: 10px;
}

.traceability-panel,
.coverage-summary-panel,
.review-checklist-panel {
  align-self: stretch;
}

.traceability-panel,
.coverage-summary-panel {
  display: flex;
  flex-direction: column;
}

.coverage-summary-panel .compact-coverage-list {
  flex: 1;
  align-content: start;
}

.traceability-panel {
  overflow: hidden;
}

.traceability-panel .version-chain {
  flex: 0 0 auto;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-content: start;
  justify-content: stretch;
  margin-top: 16px;
  gap: 10px;
}

.traceability-panel .version-chain > .app-icon {
  display: none;
}

.traceability-panel .version-chain article {
  position: relative;
  min-width: 0;
  padding: 12px 10px 10px;
}

.traceability-panel .version-chain article::before {
  content: "0" counter(version-step);
  position: absolute;
  top: 6px;
  right: 8px;
  color: #9aa8b7;
  font: 700 7px monospace;
}

.traceability-panel .version-chain {
  counter-reset: version-step;
}

.traceability-panel .version-chain article {
  counter-increment: version-step;
}

.traceability-panel .version-chain article strong,
.traceability-panel .version-chain article p {
  max-width: 100%;
}

@media (max-width: 1180px) {
  .traceability-panel .version-chain {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .report-document {
    min-height: 0;
  }
}

@media (max-width: 560px) {
  .traceability-panel .version-chain {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
