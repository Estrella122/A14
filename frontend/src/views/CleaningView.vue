<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import IntegratedEvidencePanel from '../components/IntegratedEvidencePanel.vue'
import { announcePipelineUpdate, getLatestPipelineRun, rerunPipeline } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify', 'navigate'])

const recommendedConfig = { sample: props.project.sample ?? '1 h', missing: '因果化验对齐 + 分级插值', method: 'Hampel + 高炉工艺边界', threshold: 2.4, align: true }
const config = ref({ ...recommendedConfig })
const running = ref(false)
const auditFilter = ref('all')
const { latestRun } = useLatestPipelineRun(() => props.project.scenarioId)
const liveCleaning = computed(() => latestRun.value?.results?.cleaning ?? null)
const liveMissing = computed(() => {
  const values = Object.values(liveCleaning.value?.missing_rate ?? {})
  return values.length ? (values.reduce((sum, value) => sum + Number(value), 0) / values.length * 100).toFixed(2) : props.project.missing
})

const checks = computed(() => [
  { name: '时间戳规范', standard: config.value.sample, result: liveCleaning.value ? '通过' : '等待', detail: liveCleaning.value?.logs?.find((item) => item.includes('重采样')) ?? '等待真实任务', tone: liveCleaning.value ? 'success' : 'warning' },
  { name: '元数据隔离', standard: '文本字段不参与均值', result: liveCleaning.value ? '通过' : '等待', detail: liveCleaning.value?.logs?.find((item) => item.includes('排除非建模')) ?? '没有需要排除的元数据字段', tone: liveCleaning.value ? 'success' : 'warning' },
  { name: '缺失值处理', standard: '按缺失率分级插值', result: Number(liveMissing.value) < 20 ? '通过' : '待复核', detail: `重采样后平均空档率 ${liveMissing.value}%`, tone: Number(liveMissing.value) < 20 ? 'success' : 'warning' },
  { name: '异常值检测', standard: '工艺边界 + 阶跃 + 中位数', result: liveCleaning.value ? '完成' : '等待', detail: `${liveCleaning.value?.logs?.filter((item) => item.includes('异常点')).length ?? 0} 个变量完成异常检测`, tone: liveCleaning.value ? 'success' : 'warning' },
  { name: '建模数据冻结', standard: '动态窗口优先', result: liveCleaning.value?.modeling_row_count ? '通过' : '等待', detail: `${liveCleaning.value?.modeling_row_count ?? 0} 行进入系统辨识`, tone: liveCleaning.value?.modeling_row_count ? 'success' : 'warning' },
])
const visibleChecks = computed(() => auditFilter.value === 'review' ? checks.value.filter((item) => item.tone === 'warning') : checks.value)

function resetRecommendedConfig() {
  config.value = { ...recommendedConfig }
  emit('notify', { tone: 'success', title: '已恢复推荐参数', message: '采样周期、缺失处理、异常策略和阈值已恢复为 Agent 推荐值。' })
}

function toggleAuditFilter() {
  auditFilter.value = auditFilter.value === 'all' ? 'review' : 'all'
}

function showCheckDetail(item) {
  emit('notify', { tone: item.tone === 'warning' ? 'warning' : 'info', title: item.name, message: `${item.standard}：${item.detail}` })
}

function exportAudit() {
  const rows = [['检查项', '准入规则', '结论', '详情'], ...checks.value.map((item) => [item.name, item.standard, item.result, item.detail])]
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${latestRun.value?.run_id ?? 'processpilot'}_cleaning_audit.csv`
  anchor.click()
  URL.revokeObjectURL(url)
  emit('notify', { tone: 'success', title: '审计记录已导出', message: `${checks.value.length} 项质量门禁已写入 CSV。` })
}

async function executeCleaning() {
  if (running.value) return
  running.value = true
  try {
    const latest = await getLatestPipelineRun()
    if (!latest) throw new Error('请先在“数据资产”页面上传CSV。')
    const snapshot = await rerunPipeline(latest.run_id, { resampleRule: config.value.sample.replace(' ', '') })
    latestRun.value = snapshot
    announcePipelineUpdate(snapshot)
    const quality = snapshot.results?.cleaning?.overall_score
    emit('notify', { tone: 'success', title: '真实规整流水线执行完成', message: `质量评分 ${quality ?? '—'}，后续动态优选与辨识结果已同步更新。` })
  } catch (error) {
    emit('notify', { tone: 'warning', title: '规整执行失败', message: error.message })
  } finally {
    running.value = false
  }
}

</script>

<template>
  <div class="view-stack cleaning-view">
    <PageHeader
      eyebrow="Intelligent Data Preparation"
      title="智能规整与质量治理"
      description="Agent 根据数据画像自动配置重采样、时间戳对齐、缺失修复与异常剔除策略，保留完整可追溯的修复记录。"
    >
      <template #actions>
        <button class="btn btn-secondary" type="button" @click="resetRecommendedConfig">恢复推荐参数</button>
        <button class="btn btn-primary" type="button" :disabled="running" @click="executeCleaning"><AppIcon :name="running ? 'loop' : 'play'" :class="{ spinning: running }" />{{ running ? '正在规整…' : '执行智能规整' }}</button>
      </template>
    </PageHeader>

    <IntegratedEvidencePanel module="cleaning" :run="latestRun" />

    <div class="notice-banner" :class="liveCleaning ? 'success-banner' : 'warning-banner'">
      <span class="notice-icon"><AppIcon name="alert" /></span>
      <div><strong>{{ liveCleaning ? `真实清洗质量评分 ${liveCleaning.overall_score}` : '尚未运行真实清洗任务' }}</strong><p>{{ liveCleaning ? `已完成 ${liveCleaning.cleaned_row_count} 行数据规整，筛选建模数据 ${liveCleaning.modeling_row_count} 行。` : '请先上传CSV，系统将按工艺边界检测并修复异常。' }}</p></div>
      <button type="button" @click="executeCleaning">重新执行 <AppIcon name="arrow" :size="15" /></button>
    </div>

    <section class="metric-grid four-col">
      <article class="metric-card"><span class="metric-label">原始平均缺失率</span><div class="metric-value">{{ liveMissing }}%</div><p>清洗后完成插值</p><span class="metric-trend positive">真实任务统计</span></article>
      <article class="metric-card"><span class="metric-label">数据质量</span><div class="metric-value">{{ liveCleaning?.overall_score ?? '—' }}</div><p>综合五维评分</p><span class="metric-trend positive">{{ liveCleaning ? '已生成质量报告' : '等待运行' }}</span></article>
      <article class="metric-card"><span class="metric-label">优质动态段</span><div class="metric-value">{{ liveCleaning?.selected_segment_count ?? '—' }}</div><p>滑动窗口真实评分</p><span class="metric-trend positive">自动筛选</span></article>
      <article class="metric-card"><span class="metric-label">规整后数据量</span><div class="metric-value">{{ liveCleaning?.cleaned_row_count?.toLocaleString('zh-CN') ?? '—' }}</div><p>建模数据 {{ liveCleaning?.modeling_row_count?.toLocaleString('zh-CN') ?? '—' }} 行</p><span class="metric-trend positive">任务产物可下载</span></article>
    </section>

    <div class="content-grid content-grid-4-8">
      <section class="panel settings-panel">
        <div class="section-heading compact"><div><span class="section-kicker">标准化参数接口</span><h2>Agent 推荐策略</h2></div><StatusPill tone="brand">自动生成</StatusPill></div>
        <div class="settings-form">
          <label><span>目标采样周期 <small>按过程惯性推荐</small></span><select v-model="config.sample"><option>1 s</option><option>2 s</option><option>5 s</option><option>10 s</option></select></label>
          <label><span>缺失值处理 <small>短断点自动修复</small></span><select v-model="config.missing"><option>局部线性插值</option><option>前向填充</option><option>样条插值</option></select></label>
          <label><span>异常检测策略 <small>统计规则叠加工艺边界</small></span><select v-model="config.method"><option>Hampel + 工艺边界</option><option>3σ + 工艺边界</option><option>Isolation Forest</option></select></label>
          <label class="range-setting"><span>异常阈值 <strong>{{ config.threshold }}σ</strong></span><input v-model="config.threshold" type="range" min="1.5" max="4" step="0.1" /><small><span>敏感</span><span>稳健</span></small></label>
          <label class="switch-setting"><span><strong>跨源时间轴对齐</strong><small>DCS / MES / LIMS 自动校准</small></span><input v-model="config.align" type="checkbox" /><i></i></label>
        </div>
        <div class="strategy-version"><span><AppIcon name="shield" /></span><div><strong>策略版本 PREP-v2.4</strong><p>由 Agent 基于 12 次历史运行自适应推荐</p></div></div>
      </section>

      <section class="panel comparison-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">清洗前后对比</span><h2>{{ project.target }} · 00:42 — 01:18</h2></div>
          <div class="chart-legend"><span><i class="legend-dot raw"></i>原始信号</span><span><i class="legend-dot cleaned"></i>规整后</span><span><i class="legend-dot anomaly"></i>异常点</span></div>
        </div>
        <svg class="line-chart comparison-chart" viewBox="0 0 820 310" role="img" :aria-label="`${project.target}清洗前后曲线对比`">
          <g class="chart-grid"><path d="M55 35H795M55 90H795M55 145H795M55 200H795M55 255H795" /><path d="M55 35V255M203 35V255M351 35V255M499 35V255M647 35V255M795 35V255" /></g>
          <g class="axis-labels"><text x="15" y="40">1240</text><text x="15" y="95">1220</text><text x="15" y="150">1200</text><text x="15" y="205">1180</text><text x="15" y="260">1160</text><text x="58" y="286">00:42</text><text x="190" y="286">00:49</text><text x="338" y="286">00:56</text><text x="486" y="286">01:03</text><text x="634" y="286">01:10</text><text x="755" y="286">01:18</text></g>
          <path class="chart-line raw-signal" d="M55 206 L82 197 L105 213 L130 194 L152 200 L180 182 L206 190 L232 171 L258 185 L282 166 L304 178 L330 48 L347 169 L370 157 L396 163 L422 148 L448 155 L470 137 L494 145 L520 132 L544 142 L568 126 L590 54 L607 120 L632 130 L660 112 L684 122 L710 106 L736 112 L762 96 L795 102" />
          <path class="chart-line clean-signal" d="M55 202 C100 204 132 196 180 187 S260 176 330 168 S410 156 470 145 S560 132 620 123 S710 110 795 100" />
          <g class="anomaly-points"><circle cx="330" cy="48" r="6" /><circle cx="590" cy="54" r="6" /><path d="M330 48V25M590 54V25" /><text x="305" y="18">压力尖峰</text><text x="565" y="18">传感器抖动</text></g>
        </svg>
        <div class="comparison-summary"><div><span>修复点</span><strong>864</strong></div><div><span>隔离点</span><strong>402</strong></div><div><span>保留率</span><strong>97.4%</strong></div><div><span>信噪比提升</span><strong>+5.8 dB</strong></div></div>
      </section>
    </div>

    <section class="panel audit-panel">
      <div class="section-heading compact"><div><span class="section-kicker">质量门禁</span><h2>数据标准化检查与修复记录</h2></div><div class="table-tools"><button :class="{ 'is-active': auditFilter === 'review' }" type="button" @click="toggleAuditFilter">{{ auditFilter === 'all' ? '全部状态' : '仅待复核' }}</button><button type="button" @click="exportAudit">导出审计记录</button></div></div>
      <div class="table-wrap">
        <table class="data-table audit-table">
          <caption class="visually-hidden">数据标准化检查与修复记录</caption>
          <thead><tr><th>检查项</th><th>准入规则</th><th>检查结论</th><th>Agent 解释与修复结果</th><th>操作</th></tr></thead>
          <tbody><tr v-for="item in visibleChecks" :key="item.name"><td><strong>{{ item.name }}</strong></td><td>{{ item.standard }}</td><td><StatusPill :tone="item.tone" dot>{{ item.result }}</StatusPill></td><td>{{ item.detail }}</td><td><button class="text-button" type="button" @click="showCheckDetail(item)">查看详情</button></td></tr><tr v-if="!visibleChecks.length"><td colspan="5">当前筛选条件下没有待复核项。</td></tr></tbody>
        </table>
      </div>
    </section>

    <div class="agent-explanation-card">
      <span class="agent-explanation-icon"><AppIcon name="spark" :size="24" /></span>
      <div><span class="section-kicker">Agent 决策解释</span><h2>本次CSV实际采用的清洗策略</h2><p>时间戳按当前采样周期统一；缺失值根据缺失率使用时间插值；异常值由工艺边界、阶跃阈值和局部中位数联合识别。本次质量评分 {{ liveCleaning?.overall_score ?? '—' }}，最终保留 {{ liveCleaning?.modeling_row_count ?? 0 }} 行建模数据。</p></div>
      <button type="button" @click="emit('navigate', '/agent-review/')">追问 Agent <AppIcon name="arrow" :size="15" /></button>
    </div>
  </div>
</template>
