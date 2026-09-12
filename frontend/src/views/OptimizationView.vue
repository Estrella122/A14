<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import {
  acceptOptimizationStudy,
  createOptimizationStudy,
  downloadOptimizationStudy,
  listOptimizationStudies,
  runOptimizationStep,
} from '../api/optimization'
import { announcePipelineUpdate, artifactUrl, rerunPipeline } from '../api/pipeline'
import { useLatestPipelineRun } from '../composables/useLatestPipelineRun'

const props = defineProps({
  project: { type: Object, required: true },
  config: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['notify', 'strategy-accepted'])
const { latestRun } = useLatestPipelineRun()
const pipelineOptimization = computed(() => latestRun.value?.results?.optimization ?? null)

const defaultCandidate = {
  dynamic_threshold: 0.24,
  outlier_sigma: 3.8,
  collinearity_threshold: 0.94,
  lag_max_seconds: 60,
  min_segment_minutes: 4,
}

const configuredWeights = {
  fit: Number(props.config.objectiveWeights?.fit ?? 0.70),
  coverage: Number(props.config.objectiveWeights?.coverage ?? 0.20),
  cost: Number(props.config.objectiveWeights?.cost ?? 0.10),
}
const configuredConstraints = {
  target_fit: Number(props.config.constraints?.target_fit ?? 0.75),
  min_coverage: Number(props.config.constraints?.min_coverage ?? 0.70),
  max_rmse: Number(props.config.constraints?.max_rmse ?? 6.0),
  min_valid_segments: Number(props.config.constraints?.min_valid_segments ?? 5),
}

const params = ref({ ...defaultCandidate, ...(props.config.initialCandidate ?? {}) })
const searchSettings = ref({
  runMode: 'auto_converge',
  maxRounds: 12,
  minRounds: 8,
  patience: 3,
  minImprovement: 0.2,
  fixedRounds: 8,
  randomSeed: Number(props.config.randomSeed ?? 20260731),
})
const study = ref(null)
const studyHistory = ref([])
const loading = ref(true)
const creating = ref(false)
const running = ref(false)
const paused = ref(false)
const pauseRequested = ref(false)
const accepting = ref(false)
const exporting = ref('')
const errorMessage = ref('')
const connectionError = ref('')
const comparisonMode = ref(false)
const technicalView = ref(false)
const chartMode = ref('score')
const historyOpen = ref(false)
let requestController = new AbortController()

function pipelineRunToStudy(snapshot) {
  const optimization = snapshot?.results?.optimization
  if (!optimization?.iterations?.length) return null
  const cleaning = snapshot.results?.cleaning ?? {}
  const modeling = snapshot.results?.modeling ?? {}
  const review = snapshot.results?.review ?? {}
  const optimizationStopping = optimization.stopping ?? {}
  const trainMetrics = modeling.metrics?.train ?? {}
  const selectedInputs = modeling.selected_inputs ?? modeling.input_cols ?? []
  const modelLagRows = modeling.lags ?? []
  const observedLag = modelLagRows.length
    ? Math.max(...modelLagRows.map(row => Number(row.delay_samples) || 0))
    : null
  const observedLagBoundaryHit = modelLagRows.some(row => row.boundary_hit)
  let previous = null
  const iterations = optimization.iterations.filter((item) => item.status === 'completed').map((item) => {
    const r2 = Number(item.r2 ?? 0)
    const rmse = Number(item.rmse ?? 0)
    const coverage = Number(item.coverage ?? 0)
    const score = Number(item.score ?? 0)
    const isBest = item.round === optimization.best_round
    const checks = {
      fit: { actual: r2, target: configuredConstraints.target_fit, passed: r2 >= configuredConstraints.target_fit },
      coverage: { actual: coverage, target: configuredConstraints.min_coverage, passed: coverage >= configuredConstraints.min_coverage },
      rmse: { actual: rmse, target: configuredConstraints.max_rmse, passed: rmse <= configuredConstraints.max_rmse },
      segments: { actual: Number(cleaning.selected_segment_count ?? 0), target: configuredConstraints.min_valid_segments, passed: Number(cleaning.selected_segment_count ?? 0) >= configuredConstraints.min_valid_segments },
    }
    const failures = Object.entries(checks).filter(([, check]) => !check.passed).map(([key]) => ({ fit: '拟合度未达阈值', coverage: '覆盖率未达阈值', rmse: 'RMSE超过阈值', segments: '有效片段不足' }[key]))
    const row = {
      id: `${snapshot.run_id}-${item.round}`,
      round: item.round,
      params: {
        top_k: Number(item.top_k ?? optimization.best_parameters?.top_k ?? 5),
        dynamic_threshold: Number(cleaning.config?.dynamic_threshold ?? 0.35),
        outlier_sigma: Number(cleaning.config?.outlier_sigma ?? 3),
        collinearity_threshold: 0.95,
        lag_max_seconds: Number(item.effective_max_lag ?? item.max_lag ?? optimization.best_parameters?.max_lag ?? 60),
        min_segment_minutes: Number(
          snapshot.results?.standardization?.scenario?.selection_window_samples
          ?? cleaning.config?.min_segment_minutes
          ?? 4,
        ),
      },
      metrics: { fit: r2, r2, rmse, coverage, cost: 0, overall_score: score },
      diagnostics: {
        optimal_lag_seconds: isBest && observedLag != null
          ? observedLag
          : Number(item.effective_max_lag ?? item.max_lag ?? 0),
        validation_samples: Math.max(0, Math.round(Number(item.row_count ?? 0) * 0.2)),
        generalization_gap: Number(trainMetrics.r2 ?? r2) - r2,
        lag_boundary_hit: isBest ? observedLagBoundaryHit : false,
        clipped_points: Number(cleaning.outlier_count ?? 0),
        injected_outliers: 0,
        valid_segments: Number(cleaning.selected_segment_count ?? 0),
        feature_count: selectedInputs.length,
        effective_signature: `RUN-${snapshot.run_id}-R${item.round}`,
      },
      constraint_checks: checks,
      constraint_failures: failures,
      decision: isBest ? (failures.length ? '最高分待复核' : 'Agent 推荐') : '候选保留',
      decision_code: isBest ? 'new_best' : 'not_improved',
      decision_reason: isBest ? (failures.length ? `真实 CSV 候选中综合得分最高，但仍有 ${failures.length} 项硬约束未通过` : '真实 CSV 候选中综合得分最高且通过硬约束') : '真实计算完成，但综合得分未超过当前最优轮次',
      change_summary: item.label ?? `候选策略 ${item.round}`,
      search_reason: item.round === 1 ? '建立真实数据基线' : '依据上一轮辨识结果调整动态段数量与时滞上限',
      delta_vs_previous: previous ? { overall_score: score - previous.score, fit: r2 - previous.r2 } : {},
      candidate_source: item.round === 1 ? 'initial_baseline' : item.round <= 6 ? 'space_filling' : 'feedback_search',
      is_best: isBest,
    }
    previous = { score, r2 }
    return row
  })
  const best = iterations.find((item) => item.is_best) ?? iterations[0]
  return {
    contract_version: 'clso.pipeline.v1',
    id: snapshot.run_id,
    pipeline_run_id: snapshot.run_id,
    project_code: props.project.code,
    project_name: props.project.name,
    dataset_mode: 'uploaded_csv',
    dataset_source: `总控上传 CSV · ${snapshot.original_name}`,
    status: review.passed ? 'completed' : 'completed',
    total_rounds: Number(optimizationStopping.max_rounds ?? iterations.length),
    current_round: iterations.length,
    round_progress: 100,
    run_mode: 'agent_managed',
    stopping: {
      min_rounds: Number(optimizationStopping.min_rounds ?? 8),
      max_rounds: Number(optimizationStopping.max_rounds ?? iterations.length),
      patience: Number(optimizationStopping.patience ?? 3),
      min_score_improvement: Number(optimizationStopping.min_score_improvement ?? 0.2),
    },
    no_improvement_rounds: Number(optimizationStopping.no_improvement_rounds ?? 0),
    stop_reason: optimizationStopping.stop_reason ?? `总控已完成 ${iterations.length} 个真实数据候选评价，并选择第 ${optimization.best_round} 轮`,
    early_stopped: Boolean(optimizationStopping.early_stopped),
    objective_weights: { fit: 0.68, coverage: 0.15, cost: 0.17 },
    constraints: configuredConstraints,
    random_seed: 0,
    algorithm_version: 'REAL-CSV-CLSO-1.0',
    strategy_version: `OPT-${snapshot.run_id}-R${String(optimization.best_round).padStart(2, '0')}`,
    evaluation_profile: {
      dataset_snapshot: snapshot.run_id,
      validation_method: '真实 CSV · 分段时序留出 · ARX 候选复训',
      trust_label: '真实数据离线验证级',
      production_ready: false,
      production_gate: '仍需使用独立工况和现场多批次数据复验，方可进入生产审批。',
    },
    best_iteration: best,
    iterations,
  }
}

const iterations = computed(() => study.value?.iterations ?? [])
const usesSampleUnits = computed(() => Boolean(study.value?.pipeline_run_id))
const lagDisplayUnit = computed(() => usesSampleUnits.value ? '采样点' : 's')
const segmentDisplayUnit = computed(() => usesSampleUnits.value ? '采样点' : 'min')
const isCompleted = computed(() => ['completed', 'accepted'].includes(study.value?.status))
const isTerminal = computed(() => ['completed', 'accepted', 'failed'].includes(study.value?.status))
const isAccepted = computed(() => study.value?.status === 'accepted')
const isLegacy = computed(() => Boolean(study.value?.is_legacy))
const executionBusy = computed(() => creating.value || running.value)
const operationBusy = computed(() => loading.value || creating.value || running.value || accepting.value)
const settingsLocked = computed(() => operationBusy.value || Boolean(study.value && !isTerminal.value))
const normalizedRandomSeed = computed(() => {
  const value = Math.trunc(Number(searchSettings.value.randomSeed))
  return Number.isFinite(value) ? Math.min(2_147_483_647, Math.max(0, value)) : 20260731
})
const visibleIterations = computed(() => {
  if (!comparisonMode.value) return iterations.value
  return [...iterations.value]
    .sort((left, right) => {
      const leftValid = left.constraint_failures?.length ? 0 : 1
      const rightValid = right.constraint_failures?.length ? 0 : 1
      return rightValid - leftValid || right.metrics.overall_score - left.metrics.overall_score
    })
    .slice(0, 3)
    .sort((left, right) => left.round - right.round)
})
const bestIteration = computed(() => study.value?.best_iteration ?? null)
const totalRounds = computed(() => study.value?.total_rounds ?? (
  searchSettings.value.runMode === 'fixed' ? searchSettings.value.fixedRounds : searchSettings.value.maxRounds
))
const currentRound = computed(() => study.value?.current_round ?? 0)
const roundProgress = computed(() => isTerminal.value ? 100 : study.value?.round_progress ?? (
  totalRounds.value ? Math.round(currentRound.value / totalRounds.value * 100) : 0
))
const baselineIteration = computed(() => iterations.value[0] ?? null)
const baselineFit = computed(() => baselineIteration.value?.metrics.fit ?? null)
const fitImprovement = computed(() => {
  if (baselineFit.value === null || !bestIteration.value) return null
  return bestIteration.value.metrics.fit - baselineFit.value
})
const scoreImprovement = computed(() => {
  if (!baselineIteration.value || !bestIteration.value) return null
  return bestIteration.value.metrics.overall_score - baselineIteration.value.metrics.overall_score
})
const coverageImprovement = computed(() => {
  if (!baselineIteration.value || !bestIteration.value) return null
  return bestIteration.value.metrics.coverage - baselineIteration.value.metrics.coverage
})
const strategyVersion = computed(() => study.value?.strategy_version ?? '尚未生成')
const algorithmVersion = computed(() => study.value?.algorithm_version ?? 'CLSO-2.0')
const stopping = computed(() => study.value?.stopping ?? {
  min_rounds: searchSettings.value.minRounds,
  max_rounds: totalRounds.value,
  patience: searchSettings.value.patience,
  min_score_improvement: searchSettings.value.minImprovement,
})
const evaluationProfile = computed(() => study.value?.evaluation_profile ?? {
  dataset_snapshot: '任务创建后生成输入快照指纹',
  validation_method: '分段时序留出 · 18 步自由运行',
  trust_label: '仿真验证级',
  production_ready: false,
  production_gate: '接入现场 CSV 并通过多时段、多批次复验后，才可进入生产审批。',
})
const objectiveWeights = computed(() => study.value?.objective_weights ?? configuredWeights)
const constraintsConfig = computed(() => study.value?.constraints ?? configuredConstraints)
const passedConstraintCount = computed(() => Object.values(bestIteration.value?.constraint_checks ?? {}).filter((item) => item.passed).length)
const canAccept = computed(() => Boolean(
  bestIteration.value
  && isCompleted.value
  && !study.value?.pipeline_run_id
  && !isAccepted.value
  && !isLegacy.value
  && !bestIteration.value.constraint_failures?.length
))
const highestRejected = computed(() => {
  if (!bestIteration.value) return null
  return [...iterations.value]
    .filter((row) => row.constraint_failures?.length && row.metrics.overall_score > bestIteration.value.metrics.overall_score)
    .sort((left, right) => right.metrics.overall_score - left.metrics.overall_score)[0] ?? null
})
const sourceStatus = computed(() => {
  if (loading.value) return { tone: 'loading', label: '正在连接后端', detail: '正在读取闭环寻优任务与数据快照' }
  if (connectionError.value) return { tone: 'offline', label: '后端连接异常', detail: connectionError.value }
  if (study.value?.pipeline_run_id) return { tone: 'live', label: '总控 Agent 已调用闭环寻优', detail: study.value.dataset_source }
  if (study.value) return { tone: 'live', label: '仿真基准计算', detail: study.value.dataset_source }
  return { tone: 'ready', label: '后端已就绪', detail: '尚未创建寻优任务，启动后生成可追溯数据快照' }
})
const constraintGateRows = computed(() => {
  const checks = bestIteration.value?.constraint_checks ?? {}
  const definitions = {
    fit: { label: '多步 Fit', operator: '\u2265', digits: 4, percent: false },
    coverage: { label: '动态覆盖率', operator: '\u2265', digits: 1, percent: true },
    rmse: { label: '验证 RMSE', operator: '\u2264', digits: 3, percent: false },
    segments: { label: '有效片段', operator: '\u2265', digits: 0, percent: false },
  }
  return Object.entries(definitions).map(([key, definition]) => {
    const check = checks[key] ?? {}
    const factor = definition.percent ? 100 : 1
    return {
      key,
      ...definition,
      passed: Boolean(check.passed),
      actual: Number(check.actual) * factor,
      target: Number(check.target) * factor,
    }
  })
})

const startButtonLabel = computed(() => {
  if (creating.value) return '正在创建任务…'
  if (running.value && pauseRequested.value) return '正在安全暂停…'
  if (running.value) return `真实计算 · 第 ${Math.min(currentRound.value + 1, totalRounds.value)} 轮`
  if (study.value?.pipeline_run_id) return '由总控重新执行闭环寻优'
  if (paused.value) return '继续剩余轮次'
  if (study.value && !isTerminal.value) return '继续未完成的寻优'
  if (study.value) return '启动新一轮寻优'
  return '启动闭环寻优'
})
const stopHeadline = computed(() => {
  if (running.value && pauseRequested.value) return '正在安全暂停'
  if (running.value) return '正在搜索'
  if (paused.value) return '已安全暂停'
  if (isAccepted.value) return '演示策略已固化'
  if (study.value?.early_stopped) return '已自动收敛'
  if (study.value?.status === 'completed') return '已达到最大轮次'
  if (study.value?.status === 'failed') return '执行失败'
  if (study.value) return '等待继续'
  return '等待启动'
})
const statusCopy = computed(() => {
  if (running.value && pauseRequested.value) return '正在完成当前轮并保存结果，随后暂停；已完成轮次不会丢失。'
  if (running.value) return `后端正在执行第 ${Math.min(currentRound.value + 1, totalRounds.value)} 轮预处理与多步 ARX 验证…`
  if (paused.value) return `任务已暂停在第 ${currentRound.value} 轮，点击“继续剩余轮次”即可从下一轮恢复。`
  if (study.value?.status === 'accepted') return '最优演示策略已固化，可导出标准 JSON 合并包。'
  if (study.value?.status === 'completed') return study.value.stop_reason || '本次搜索已结束。'
  if (study.value?.status === 'failed') return study.value.error_message || '任务执行失败。'
  if (study.value) return '任务可恢复，点击继续后从下一轮执行。'
  return '默认自动收敛：至少 8 轮，最多 12 轮。'
})

const chartOptions = [
  { key: 'score', label: '综合分', metric: 'overall_score', target: null },
  { key: 'fit', label: 'Fit', metric: 'fit', targetKey: 'target_fit' },
  { key: 'coverage', label: '覆盖率', metric: 'coverage', targetKey: 'min_coverage' },
]
const activeChartOption = computed(() => chartOptions.find((item) => item.key === chartMode.value) ?? chartOptions[0])
const chartTarget = computed(() => {
  const option = activeChartOption.value
  return option.targetKey ? Number(study.value?.constraints?.[option.targetKey] ?? (option.key === 'fit' ? 0.75 : 0.70)) : null
})
const chartValue = (row) => Number(row?.metrics?.[activeChartOption.value.metric] ?? 0)
const chartDomain = computed(() => {
  const values = iterations.value.map(chartValue).filter(Number.isFinite)
  if (chartTarget.value !== null) values.push(chartTarget.value)
  if (!values.length) return activeChartOption.value.key === 'score' ? [0, 100] : [0, 1]
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  const minimumPadding = activeChartOption.value.key === 'score' ? 1.5 : 0.015
  const padding = Math.max(minimumPadding, (rawMax - rawMin) * 0.22)
  const isFit = activeChartOption.value.key === 'fit'
  const lowerBound = isFit ? Math.min(0, rawMin - padding) : 0
  const upperBound = activeChartOption.value.key === 'score' ? 100 : isFit ? Math.max(1, rawMax + padding) : 1
  let minimum = Math.max(lowerBound, rawMin - padding)
  let maximum = Math.min(upperBound, rawMax + padding)
  if (maximum - minimum < minimumPadding * 2) {
    minimum = Math.max(lowerBound, minimum - minimumPadding)
    maximum = Math.min(upperBound, maximum + minimumPadding)
  }
  return [minimum, maximum]
})
const chartX = (round) => 60 + (round - 1) * 750 / Math.max(1, totalRounds.value - 1)
const chartY = (value) => {
  const [minimum, maximum] = chartDomain.value
  const coordinate = 275 - (Number(value) - minimum) / Math.max(0.0001, maximum - minimum) * 240
  return Math.max(35, Math.min(275, coordinate))
}
const chartPoints = computed(() => iterations.value.map((row) => ({
  ...row,
  value: chartValue(row),
  x: chartX(row.round),
  y: chartY(chartValue(row)),
})))
const bestSeriesPoints = computed(() => {
  let runningBest = null
  return iterations.value.map((row) => {
    const rowValid = !row.constraint_failures?.length
    const bestValid = runningBest ? !runningBest.constraint_failures?.length : false
    if (!runningBest || (rowValid && !bestValid) || (rowValid === bestValid && row.metrics.overall_score > runningBest.metrics.overall_score)) {
      runningBest = row
    }
    return { x: chartX(row.round), y: chartY(chartValue(runningBest)) }
  })
})
const seriesPath = computed(() => chartPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' '))
const bestSeriesPath = computed(() => bestSeriesPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' '))
const seriesArea = computed(() => {
  if (!chartPoints.value.length) return ''
  const first = chartPoints.value[0]
  const last = chartPoints.value.at(-1)
  return `${seriesPath.value} L${last.x.toFixed(1)} 275 L${first.x.toFixed(1)} 275Z`
})
const chartTicks = computed(() => {
  const [minimum, maximum] = chartDomain.value
  return Array.from({ length: 5 }, (_, index) => ({
    y: 35 + index * 60,
    value: maximum - (maximum - minimum) * index / 4,
  }))
})
const goalY = computed(() => chartTarget.value === null ? null : chartY(chartTarget.value))

function formatMetric(value, digits = 3, empty = '—') {
  if (value === null || value === undefined || value === '') return empty
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : empty
}

function formatSigned(value, digits = 2, suffix = '') {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  const numeric = Number(value)
  return `${numeric >= 0 ? '+' : ''}${numeric.toFixed(digits)}${suffix}`
}

function formatChartValue(value) {
  if (activeChartOption.value.key === 'score') return formatMetric(value, 2)
  if (activeChartOption.value.key === 'coverage') return `${formatMetric(Number(value) * 100, 1)}%`
  return formatMetric(value, 4)
}

function resultTone(row) {
  if (row.is_best) return 'success'
  if (row.constraint_failures?.length) return 'warning'
  if (row.decision_code === 'equivalent') return 'neutral'
  return 'brand'
}

function pointClass(point) {
  return {
    'best-point': point.is_best,
    'infeasible-point': point.constraint_failures?.length,
    'equivalent-point': point.decision_code === 'equivalent',
  }
}

function phaseLabel(row) {
  return {
    initial_baseline: '首轮基线',
    space_filling: '空间覆盖',
    feedback_search: '反馈精搜',
  }[row.candidate_source] || '历史轮次'
}

function deltaText(row) {
  const delta = row.delta_vs_previous ?? {}
  if (row.round === 1 || delta.overall_score === undefined) return '建立可比基线'
  return `综合分 ${formatSigned(delta.overall_score, 2)} · Fit ${formatSigned(delta.fit, 4)}`
}

function deltaTone(row) {
  const delta = Number(row.delta_vs_previous?.overall_score ?? 0)
  if (row.round === 1 || Math.abs(delta) < 0.0001) return ''
  return delta > 0 ? 'positive' : 'negative'
}

function constraintText(row) {
  return row.constraint_failures?.length ? row.constraint_failures.join('、') : '4 项硬约束全部通过'
}

function clearErrors() {
  errorMessage.value = ''
  connectionError.value = ''
}

function notifyError(error, title = '闭环寻优请求失败') {
  if (error?.name === 'AbortError') return
  const message = error?.message || '请求未完成'
  const isConnectionFailure = !error?.status && (
    error instanceof TypeError
    || /fetch|network|连接|Failed to fetch/i.test(message)
  )
  if (isConnectionFailure) connectionError.value = message
  else errorMessage.value = message
  emit('notify', { tone: 'warning', title, message })
}

function applyStudy(nextStudy) {
  study.value = nextStudy ?? null
  paused.value = false
  comparisonMode.value = false
  if (study.value?.best_iteration) params.value = { ...study.value.best_iteration.params }
  if (study.value && !study.value.is_legacy) {
    searchSettings.value.runMode = study.value.run_mode || 'auto_converge'
    searchSettings.value.maxRounds = study.value.total_rounds || 12
    searchSettings.value.fixedRounds = study.value.total_rounds || 8
    searchSettings.value.minRounds = study.value.stopping?.min_rounds || 8
    searchSettings.value.patience = study.value.stopping?.patience || 3
    searchSettings.value.minImprovement = study.value.stopping?.min_score_improvement || 0.2
    searchSettings.value.randomSeed = study.value.random_seed ?? 20260731
  }
}

function historyStatusLabel(item) {
  return {
    ready: '待运行',
    running: '可继续',
    completed: item.early_stopped ? '已收敛' : '已完成',
    accepted: '已固化',
    failed: '失败',
  }[item.status] || item.status
}

function formatHistoryTime(value) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

async function loadLatestStrategy({ announce = false, selectLatest = true } = {}) {
  const pipelineStudy = pipelineRunToStudy(latestRun.value)
  if (pipelineStudy) {
    applyStudy(pipelineStudy)
    loading.value = false
    if (announce) emit('notify', { tone: 'success', title: '已载入总控寻优结果', message: `任务 ${pipelineStudy.pipeline_run_id} 的 ${pipelineStudy.current_round} 轮真实候选已写入闭环页面。` })
    return
  }
  loading.value = true
  clearErrors()
  try {
    const response = await listOptimizationStudies(props.project.code, { signal: requestController.signal })
    studyHistory.value = response.results ?? []
    const currentPipelineStudy = pipelineRunToStudy(latestRun.value)
    if (currentPipelineStudy) applyStudy(currentPipelineStudy)
    else if (selectLatest || !study.value) applyStudy(studyHistory.value[0] ?? null)
    if (announce) {
      emit('notify', study.value
        ? { tone: 'success', title: '运行历史已刷新', message: `共 ${studyHistory.value.length} 条；当前为 ${algorithmVersion.value} · 已执行 ${currentRound.value} / 最多 ${totalRounds.value} 轮。` }
        : { tone: 'info', title: '暂无历史任务', message: '当前参数将作为首轮候选。' })
    }
  } catch (error) {
    notifyError(error, '后端连接失败')
  } finally {
    loading.value = false
  }
}

async function toggleHistory() {
  if (operationBusy.value) return
  if (historyOpen.value) {
    historyOpen.value = false
    return
  }
  await loadLatestStrategy({ announce: false, selectLatest: false })
  historyOpen.value = true
}

function selectHistoryStudy(item) {
  if (operationBusy.value) return
  applyStudy(item)
  historyOpen.value = false
  emit('notify', {
    tone: 'info',
    title: `已载入第 ${item.id} 号寻优任务`,
    message: `${historyStatusLabel(item)} · ${item.current_round} / ${item.total_rounds} 轮 · Seed ${item.random_seed}。`,
  })
}

function studyPayload(initialCandidate = params.value) {
  const autoMode = searchSettings.value.runMode === 'auto_converge'
  const rounds = autoMode ? searchSettings.value.maxRounds : searchSettings.value.fixedRounds
  return {
    project_code: props.project.code,
    project_name: props.project.name,
    dataset_mode: props.config.datasetMode || 'synthetic_benchmark',
    total_rounds: rounds,
    run_mode: searchSettings.value.runMode,
    stopping: {
      min_rounds: autoMode ? Math.min(searchSettings.value.minRounds, rounds) : 2,
      patience: searchSettings.value.patience,
      min_score_improvement: searchSettings.value.minImprovement,
    },
    random_seed: normalizedRandomSeed.value,
    initial_candidate: { ...initialCandidate },
    objective_weights: { ...configuredWeights },
    constraints: { ...configuredConstraints },
  }
}

async function runRemainingSteps() {
  running.value = true
  paused.value = false
  pauseRequested.value = false
  clearErrors()
  let requestCount = 0
  try {
    while (
      study.value
      && !['completed', 'accepted', 'failed'].includes(study.value.status)
      && study.value.current_round < study.value.total_rounds
      && !pauseRequested.value
    ) {
      const previousRound = study.value.current_round
      const response = await runOptimizationStep(study.value.id, { signal: requestController.signal })
      study.value = response.data
      requestCount += 1
      if (!isTerminal.value && study.value.current_round <= previousRound) {
        throw new Error(`后端轮次未推进（仍为第 ${study.value.current_round} 轮），已停止自动请求以避免空转`)
      }
      if (requestCount > totalRounds.value + 1) {
        throw new Error('寻优请求次数超过轮次上限，已安全停止')
      }
      if (!isTerminal.value) await new Promise((resolve) => window.setTimeout(resolve, 220))
    }
    if (study.value?.status === 'failed') throw new Error(study.value.error_message || '寻优任务执行失败')
    if (study.value?.best_iteration) params.value = { ...study.value.best_iteration.params }
    if (pauseRequested.value && !isTerminal.value) {
      paused.value = true
      emit('notify', {
        tone: 'info',
        title: '闭环寻优已安全暂停',
        message: `已保存前 ${currentRound.value} 轮结果，下次将从第 ${currentRound.value + 1} 轮继续。`,
      })
      return
    }
    emit('notify', {
      tone: 'success',
      title: study.value?.early_stopped ? '闭环寻优已自动收敛' : '闭环寻优已完成',
      message: `${study.value?.stop_reason || '本次搜索已结束'}。最优 Fit ${formatMetric(bestIteration.value?.metrics.fit, 4)}，综合分 ${formatMetric(bestIteration.value?.metrics.overall_score, 2)}。`,
    })
  } catch (error) {
    notifyError(error, '寻优执行中断')
  } finally {
    running.value = false
    pauseRequested.value = false
  }
}

async function runOptimization() {
  if (operationBusy.value) return
  if (study.value?.pipeline_run_id && latestRun.value) {
    clearErrors()
    running.value = true
    try {
      const snapshot = await rerunPipeline(latestRun.value.run_id, { maxLag: params.value.lag_max_seconds })
      announcePipelineUpdate(snapshot)
      applyStudy(pipelineRunToStudy(snapshot))
      emit('notify', { tone: 'success', title: '总控闭环寻优已完成', message: `新任务 ${snapshot.run_id} 已完成，闭环页面已同步全部候选轮次。` })
    } catch (error) {
      notifyError(error, '总控重新寻优失败')
    } finally {
      running.value = false
    }
    return
  }
  if (study.value && !isTerminal.value) {
    await runRemainingSteps()
    return
  }
  clearErrors()
  creating.value = true
  try {
    searchSettings.value.randomSeed = normalizedRandomSeed.value
    const response = await createOptimizationStudy(studyPayload(), { signal: requestController.signal })
    study.value = response.data
    emit('notify', {
      tone: 'info',
      title: '闭环寻优已启动',
      message: searchSettings.value.runMode === 'auto_converge'
        ? `至少 ${searchSettings.value.minRounds} 轮，最多 ${searchSettings.value.maxRounds} 轮，达到收敛条件将自动停止。`
        : `将完整执行 ${searchSettings.value.fixedRounds} 轮固定搜索。`,
    })
    creating.value = false
    await runRemainingSteps()
  } catch (error) {
    notifyError(error, '任务创建失败')
  } finally {
    creating.value = false
  }
}

function pauseOptimization() {
  if (!running.value || pauseRequested.value) return
  pauseRequested.value = true
}

async function startFreshV2() {
  if (operationBusy.value) return
  params.value = { ...defaultCandidate, ...(props.config.initialCandidate ?? {}) }
  searchSettings.value = { runMode: 'auto_converge', maxRounds: 12, minRounds: 8, patience: 3, minImprovement: 0.2, fixedRounds: 8, randomSeed: Number(props.config.randomSeed ?? 20260731) }
  study.value = null
  await runOptimization()
}

function resetInitialCandidate() {
  if (operationBusy.value) return
  params.value = { ...defaultCandidate, ...(props.config.initialCandidate ?? {}) }
  emit('notify', {
    tone: 'info',
    title: '首轮候选已恢复默认值',
    message: '滑块中的当前值会直接用于下一次新任务，无需额外保存。',
  })
}

async function continueExploration() {
  if (!bestIteration.value || operationBusy.value) return
  params.value = { ...bestIteration.value.params }
  if (study.value?.pipeline_run_id) {
    await runOptimization()
    return
  }
  study.value = null
  await runOptimization()
}

async function exportStudy(format = 'csv') {
  if (!study.value || exporting.value || operationBusy.value) return
  exporting.value = format
  errorMessage.value = ''
  try {
    if (study.value.pipeline_run_id) {
      const anchor = document.createElement('a')
      anchor.href = artifactUrl(study.value.pipeline_run_id, 'optimization_json')
      anchor.download = `${study.value.pipeline_run_id}_optimization.json`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      emit('notify', { tone: 'success', title: '真实寻优记录已导出', message: `${iterations.value.length} 轮总控候选及最优策略已写入 JSON。` })
      return
    }
    const { blob, disposition } = await downloadOptimizationStudy(study.value.id, format, { signal: requestController.signal })
    const matchedName = disposition.match(/filename="?([^";]+)"?/i)?.[1]
    const filename = matchedName || `${props.project.code}_optimization.${format}`
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
    emit('notify', format === 'json'
      ? { tone: 'success', title: '独立合并包已导出', message: `${strategyVersion.value} 的配置、每轮证据与采纳状态已写入 JSON。` }
      : { tone: 'success', title: '真实记录已导出', message: `${iterations.value.length} 轮参数、指标、约束与决策原因已写入 CSV。` })
  } catch (error) {
    notifyError(error, '导出失败')
  } finally {
    exporting.value = ''
  }
}

async function acceptStrategy() {
  if (!study.value || !canAccept.value || accepting.value) return
  accepting.value = true
  errorMessage.value = ''
  try {
    const response = await acceptOptimizationStudy(study.value.id, { signal: requestController.signal })
    study.value = response.data
    const acceptedPackage = study.value.accepted_strategy ?? {
      contract_version: 'clso.accepted-strategy.v1',
      study_id: study.value.id,
      project_code: study.value.project_code,
      strategy_version: strategyVersion.value,
      algorithm_version: algorithmVersion.value,
      dataset_snapshot: evaluationProfile.value.dataset_snapshot,
      accepted_iteration: study.value.best_iteration,
      accepted_at: study.value.accepted_at,
    }
    emit('strategy-accepted', acceptedPackage)
    emit('notify', { tone: 'success', title: '演示策略已固化', message: `${strategyVersion.value} 已写入后端；可直接导出 JSON 合并包交给总工程。` })
  } catch (error) {
    notifyError(error, '策略采纳失败')
  } finally {
    accepting.value = false
  }
}

watch(latestRun, (snapshot) => {
  const pipelineStudy = pipelineRunToStudy(snapshot)
  if (pipelineStudy && study.value?.pipeline_run_id !== pipelineStudy.pipeline_run_id) applyStudy(pipelineStudy)
}, { deep: true })

function handleGlobalCommand(event) {
  if (event.detail?.action !== 'run-optimization') return
  if (loading.value) window.setTimeout(runOptimization, 650)
  else runOptimization()
}

onMounted(() => { loadLatestStrategy(); window.addEventListener('processpilot:command', handleGlobalCommand) })
onBeforeUnmount(() => { requestController.abort(); window.removeEventListener('processpilot:command', handleGlobalCommand) })
</script>

<template>
  <div class="view-stack optimization-view">
    <PageHeader
      eyebrow="Closed-loop Strategy Optimization"
      title="辨识反馈驱动的闭环寻优"
      description="总控 Agent 将上传 CSV 的辨识结果直接交给闭环寻优引擎，候选轮次、收敛证据和推荐策略统一在此留痕。"
    >
      <template #actions>
        <button v-if="!study?.pipeline_run_id" class="btn btn-secondary" type="button" :disabled="operationBusy" :aria-expanded="historyOpen" @click="toggleHistory">{{ historyOpen ? '收起运行历史' : '查看仿真历史' }}</button>
        <button v-if="running && !study?.pipeline_run_id" class="btn btn-secondary" type="button" :disabled="pauseRequested" @click="pauseOptimization"><AppIcon name="pause" />{{ pauseRequested ? '当前轮后暂停…' : '安全暂停' }}</button>
        <button class="btn btn-primary" type="button" :disabled="operationBusy" @click="runOptimization"><AppIcon :name="operationBusy ? 'loop' : 'play'" :class="{ spinning: operationBusy }" />{{ startButtonLabel }}</button>
      </template>
    </PageHeader>

    <section v-if="study?.pipeline_run_id" class="panel pipeline-optimization-summary">
      <div class="section-heading compact"><div><span class="section-kicker">总控 Agent → 闭环寻优 Agent</span><h2>任务 {{ study.pipeline_run_id }} 已写入统一寻优工作区</h2></div><StatusPill tone="success">真实 CSV · 第 {{ pipelineOptimization?.best_round }} 轮最优</StatusPill></div>
      <p>以下曲线、轮次对比、参数证据和最优策略全部来自本次总控运行，不再使用另一套独立展示数据。</p>
    </section>

    <section v-if="connectionError || errorMessage" class="panel optimization-error" role="alert">
      <span><AppIcon name="alert" /></span>
      <div><strong>{{ connectionError ? '后端连接异常' : '本次操作未完成' }}</strong><p>{{ connectionError || errorMessage }}{{ connectionError ? '。请确认闭环寻优后端仍在运行。' : '。任务状态与已完成轮次不会丢失。' }}</p></div>
      <button class="btn btn-secondary" type="button" :disabled="loading" @click="loadLatestStrategy({ announce: true })">重新连接</button>
    </section>

    <section v-if="isLegacy" class="optimization-legacy-banner" role="status">
      <AppIcon name="alert" />
      <div><strong>当前是 CLSO-1.0 历史记录</strong><p>旧任务使用一步预测与固定轮次，数值偏平不代表真正收敛。保留它是为了可追溯，不建议作为最终结果。</p></div>
      <button class="btn btn-primary" type="button" :disabled="operationBusy" @click="startFreshV2">用 CLSO-2.0 重新运行</button>
    </section>

    <section class="optimization-loop-card">
      <div class="loop-stage"><span><AppIcon name="spark" /></span><div><strong>自适应策略生成</strong><small>前 6 轮空间覆盖，随后反馈精搜</small></div></div>
      <AppIcon name="arrow" class="loop-arrow" />
      <div class="loop-stage"><span><AppIcon name="clean" /></span><div><strong>数据预处理</strong><small>Hampel 异常处理、动态筛选与降维</small></div></div>
      <AppIcon name="arrow" class="loop-arrow" />
      <div class="loop-stage"><span><AppIcon name="model" /></span><div><strong>ARX 训练验证</strong><small>{{ study?.pipeline_run_id ? '真实 CSV · 分段时序留出' : '分段留出 · 18 步自由运行' }}</small></div></div>
      <AppIcon name="arrow" class="loop-arrow" />
      <div class="loop-stage" :class="{ 'is-active': running || isCompleted }"><span><AppIcon name="loop" /></span><div><strong>指标反馈与早停</strong><small>Fit / 覆盖率 / 成本 / 硬约束</small></div></div>
      <div class="feedback-return"><span>Feedback</span><i></i></div>
    </section>

    <div class="optimization-source-strip" :class="`is-${sourceStatus.tone}`" role="status" aria-live="polite">
      <span><i></i>{{ sourceStatus.label }}</span>
      <strong>{{ sourceStatus.detail }}</strong>
      <code>{{ study?.pipeline_run_id ? `Run ${study.pipeline_run_id}` : `Seed ${study?.random_seed ?? normalizedRandomSeed}` }}</code>
      <small>{{ study?.pipeline_run_id ? '当前为上传 CSV 的真实离线计算结果' : study ? '当前是仿真验证，不冒充现场生产结论' : '任务创建后锁定输入快照与复现种子' }}</small>
    </div>

    <section v-if="historyOpen" class="panel optimization-history-panel" aria-label="闭环寻优运行历史">
      <div class="section-heading compact"><div><span class="section-kicker">可恢复、可追溯</span><h2>最近 {{ studyHistory.length }} 次运行</h2></div><button type="button" class="history-close" aria-label="关闭运行历史" @click="historyOpen = false">×</button></div>
      <div v-if="studyHistory.length" class="optimization-history-list">
        <button v-for="item in studyHistory" :key="item.id" type="button" :disabled="operationBusy" :class="{ 'is-active': study?.id === item.id }" :aria-pressed="study?.id === item.id" @click="selectHistoryStudy(item)">
          <span><strong>{{ item.strategy_version || `任务 #${item.id}` }}</strong><small>{{ formatHistoryTime(item.created_at) }} · Seed {{ item.random_seed }}</small></span>
          <span><b>{{ historyStatusLabel(item) }}</b><small>{{ item.current_round }} / {{ item.total_rounds }} 轮</small></span>
          <span><b>{{ item.best_iteration ? formatMetric(item.best_iteration.metrics.fit, 4) : '—' }}</b><small>最优 Fit</small></span>
        </button>
      </div>
      <p v-else class="history-empty">尚无运行记录。启动首轮寻优后，这里会保存可恢复的历史任务。</p>
    </section>

    <section v-if="!study?.pipeline_run_id" class="panel optimization-run-settings">
      <div class="section-heading compact"><div><span class="section-kicker">本次寻优设置</span><h2>轮数由收敛证据决定</h2></div><StatusPill :tone="searchSettings.runMode === 'auto_converge' ? 'success' : 'neutral'">{{ searchSettings.runMode === 'auto_converge' ? '自动收敛（推荐）' : '固定轮次' }}</StatusPill></div>
      <div class="run-mode-switch">
        <button type="button" :disabled="settingsLocked" :class="{ 'is-active': searchSettings.runMode === 'auto_converge' }" :aria-pressed="searchSettings.runMode === 'auto_converge'" @click="searchSettings.runMode = 'auto_converge'"><strong>自动收敛（推荐）</strong><small>满足硬约束后，连续无有效改善则提前停止</small></button>
        <button type="button" :disabled="settingsLocked" :class="{ 'is-active': searchSettings.runMode === 'fixed' }" :aria-pressed="searchSettings.runMode === 'fixed'" @click="searchSettings.runMode = 'fixed'"><strong>固定轮次</strong><small>始终运行到指定轮次，用于对照试验</small></button>
      </div>
      <div v-if="searchSettings.runMode === 'auto_converge'" class="stopping-setting-grid">
        <label class="setting-field"><span>最多轮次 <strong>{{ searchSettings.maxRounds }} 轮</strong></span><input v-model.number="searchSettings.maxRounds" :disabled="settingsLocked" type="range" min="8" max="16" step="1" /><small>搜索的安全上限</small></label>
        <label class="setting-field"><span>最少轮次 <strong>{{ Math.min(searchSettings.minRounds, searchSettings.maxRounds) }} 轮</strong></span><input v-model.number="searchSettings.minRounds" :disabled="settingsLocked" type="range" min="4" :max="searchSettings.maxRounds" step="1" /><small>未达此轮次不会早停</small></label>
        <label class="setting-field"><span>连续无改善 <strong>{{ searchSettings.patience }} 轮</strong></span><input v-model.number="searchSettings.patience" :disabled="settingsLocked" type="range" min="2" max="6" step="1" /><small>超过后判定局部收敛</small></label>
        <label class="setting-field"><span>最小有效改善 <strong>{{ Number(searchSettings.minImprovement).toFixed(1) }} 分</strong></span><input v-model.number="searchSettings.minImprovement" :disabled="settingsLocked" type="range" min="0.1" max="1" step="0.1" /><small>低于此值不重置早停计数</small></label>
      </div>
      <div v-else class="stopping-setting-grid">
        <label class="setting-field"><span>固定搜索轮次 <strong>{{ searchSettings.fixedRounds }} 轮</strong></span><input v-model.number="searchSettings.fixedRounds" :disabled="settingsLocked" type="range" min="2" max="16" step="1" /><small>即使已收敛也会完整执行</small></label>
      </div>
      <label class="setting-field seed-setting"><span>复现实验种子 <strong>{{ normalizedRandomSeed }}</strong></span><input v-model.number="searchSettings.randomSeed" :disabled="settingsLocked" type="number" min="0" max="2147483647" step="1" inputmode="numeric" /><small>相同项目、参数与 Seed 会得到相同轮次和结果；修改 Seed 可做稳健性对照。</small></label>
      <p class="setting-note"><AppIcon name="shield" :size="15" />默认会先用 6 轮覆盖五维搜索空间，至少执行 8 轮。只有最优候选通过全部硬约束、连续无有效改善且时滞未命中边界时，才会自动停止。</p>
    </section>

    <section class="metric-grid four-col">
      <article class="metric-card accent-blue"><span class="metric-label">当前最优拟合度</span><div class="metric-value">{{ formatMetric(bestIteration?.metrics.fit, 4) }}</div><p>首轮 {{ formatMetric(baselineFit, 4) }}</p><span class="metric-trend" :class="fitImprovement !== null && fitImprovement >= 0 ? 'positive' : 'neutral'">{{ fitImprovement === null ? '等待真实评价' : `Fit ${formatSigned(fitImprovement, 4)}` }}</span></article>
      <article class="metric-card"><span class="metric-label">综合目标得分</span><div class="metric-value">{{ formatMetric(bestIteration?.metrics.overall_score, 2) }}</div><p>Fit {{ formatMetric(objectiveWeights.fit * 100, 0) }}% · 覆盖度 {{ formatMetric(objectiveWeights.coverage * 100, 0) }}% · 成本 −{{ formatMetric(objectiveWeights.cost * 100, 0) }}%</p><span class="metric-trend positive">{{ bestIteration ? `覆盖 ${(bestIteration.metrics.coverage * 100).toFixed(1)}%` : '尚未计算' }}</span></article>
      <article class="metric-card"><span class="metric-label">真实搜索进度</span><div class="metric-value">{{ currentRound }} <small>/ 最多 {{ totalRounds }} 轮</small></div><p>{{ stopHeadline }}</p><span class="metric-trend neutral">无改善已累计 {{ study?.no_improvement_rounds || 0 }} 轮 · 阈值 {{ stopping.patience }} 轮</span></article>
      <article class="metric-card"><span class="metric-label">算法与策略版本</span><div class="metric-value metric-value-text">{{ algorithmVersion }}</div><p>{{ strategyVersion }}{{ bestIteration ? ` · R${String(bestIteration.round).padStart(2, '0')}` : '' }}</p><span class="metric-trend" :class="isAccepted ? 'positive' : 'neutral'">{{ isAccepted ? '演示策略已固化' : '可恢复 · 可追溯' }}</span></article>
    </section>

    <div class="content-grid content-grid-4-8">
      <section class="panel search-space-panel">
        <div class="section-heading compact"><div><span class="section-kicker">标准化参数接口</span><h2>{{ study?.pipeline_run_id ? '总控真实搜索参数' : '搜索空间与首轮候选' }}</h2></div><StatusPill tone="brand">{{ study?.pipeline_run_id ? '2D REAL' : '5D Search' }}</StatusPill></div>
        <div v-if="study?.pipeline_run_id" class="optimization-controls">
          <label><span>动态段数量 <strong>Top {{ params.top_k }}</strong></span><input :value="params.top_k" disabled type="range" min="2" max="20" step="1" /><small><span>Top 2</span><span>Top 20</span></small></label>
          <label><span>时滞搜索上限 <strong>{{ params.lag_max_seconds }} {{ lagDisplayUnit }}</strong></span><input :value="params.lag_max_seconds" disabled type="range" min="10" max="600" step="5" /><small><span>10 {{ lagDisplayUnit }}</span><span>600 {{ lagDisplayUnit }}</span></small></label>
        </div>
        <div v-else class="optimization-controls">
          <label><span>动态段阈值 <strong>{{ Number(params.dynamic_threshold).toFixed(2) }}</strong></span><input v-model.number="params.dynamic_threshold" :disabled="settingsLocked" type="range" min="0.2" max="0.7" step="0.01" /><small><span>0.20</span><span>0.70</span></small></label>
          <label><span>异常处理阈值 <strong>{{ Number(params.outlier_sigma).toFixed(1) }}σ</strong></span><input v-model.number="params.outlier_sigma" :disabled="settingsLocked" type="range" min="1.5" max="4" step="0.1" /><small><span>1.5σ</span><span>4.0σ</span></small></label>
          <label><span>共线降维阈值 <strong>{{ Number(params.collinearity_threshold).toFixed(2) }}</strong></span><input v-model.number="params.collinearity_threshold" :disabled="settingsLocked" type="range" min="0.6" max="0.95" step="0.01" /><small><span>0.60</span><span>0.95</span></small></label>
          <label><span>时滞搜索上限 <strong>{{ params.lag_max_seconds }} {{ lagDisplayUnit }}</strong></span><input v-model.number="params.lag_max_seconds" :disabled="settingsLocked" type="range" min="60" max="240" step="10" /><small><span>60 {{ lagDisplayUnit }}</span><span>240 {{ lagDisplayUnit }}</span></small></label>
          <label><span>最小数据段长度 <strong>{{ params.min_segment_minutes }} {{ segmentDisplayUnit }}</strong></span><input v-model.number="params.min_segment_minutes" :disabled="settingsLocked" type="range" min="4" max="20" step="1" /><small><span>4 {{ segmentDisplayUnit }}</span><span>20 {{ segmentDisplayUnit }}</span></small></label>
        </div>
        <div class="objective-card"><div><span>目标函数</span><code>J = {{ formatMetric(objectiveWeights.fit, 2) }}·Fit + {{ formatMetric(objectiveWeights.coverage, 2) }}·Coverage − {{ formatMetric(objectiveWeights.cost, 2) }}·Cost</code></div><p>硬约束：Fit ≥ {{ formatMetric(constraintsConfig.target_fit, 2) }} · 覆盖率 ≥ {{ formatMetric(constraintsConfig.min_coverage * 100, 0) }}% · RMSE ≤ {{ formatMetric(constraintsConfig.max_rmse, 1) }} · 有效片段 ≥ {{ constraintsConfig.min_valid_segments }}</p></div>
        <p class="candidate-draft-note">{{ study?.pipeline_run_id ? '前 6 轮覆盖 Top K 与时滞空间，后 2 轮依据最高分候选反馈精搜。' : '滑块值会直接作为下一次新任务的首轮候选。' }}</p>
        <button v-if="!study?.pipeline_run_id" class="btn btn-secondary btn-block" type="button" :disabled="settingsLocked" @click="resetInitialCandidate">恢复默认首轮候选</button>
      </section>

      <section class="panel convergence-panel">
        <div class="section-heading compact">
          <div><span class="section-kicker">本轮结果与历史最优</span><h2>{{ running ? '闭环策略正在计算' : iterations.length ? '迭代指标变化' : '等待首轮真实评价' }}</h2></div>
          <div class="chart-actions"><button v-for="option in chartOptions" :key="option.key" type="button" :class="{ 'is-active': chartMode === option.key }" :aria-pressed="chartMode === option.key" @click="chartMode = option.key">{{ option.label }}</button></div>
        </div>
        <svg class="line-chart convergence-chart" viewBox="0 0 840 330" role="img" :aria-label="`闭环寻优${activeChartOption.label}变化曲线`">
          <g class="chart-grid">
            <line v-for="tick in chartTicks" :key="`grid-${tick.y}`" x1="60" :y1="tick.y" x2="810" :y2="tick.y" class="chart-grid-line" />
            <line v-for="round in totalRounds" :key="`v-${round}`" :x1="chartX(round)" y1="35" :x2="chartX(round)" y2="275" class="chart-grid-line" />
          </g>
          <g class="chart-axis-labels"><text v-for="tick in chartTicks" :key="`axis-${tick.y}`" x="52" :y="tick.y + 3" text-anchor="end" class="chart-axis-label">{{ formatChartValue(tick.value) }}</text></g>
          <line v-if="goalY !== null" x1="60" :y1="goalY" x2="810" :y2="goalY" class="goal-line" /><text v-if="goalY !== null" x="686" :y="goalY - 9" class="goal-label">硬约束 {{ formatChartValue(chartTarget) }}</text>
          <defs><linearGradient id="optimizationSeriesFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2563eb" stop-opacity=".18" /><stop offset="100%" stop-color="#2563eb" stop-opacity="0" /></linearGradient></defs>
          <path v-if="seriesArea" class="convergence-area" :d="seriesArea" style="fill: url(#optimizationSeriesFill)" />
          <path v-if="seriesPath" class="chart-line convergence-line" :d="seriesPath" />
          <path v-if="bestSeriesPath" class="convergence-best-line" :d="bestSeriesPath" />
          <g v-for="point in chartPoints" :key="point.id" class="convergence-points">
            <circle :cx="point.x" :cy="point.y" :r="point.is_best ? 8 : 6" :class="pointClass(point)"><title>R{{ point.round }} · {{ formatChartValue(point.value) }} · {{ point.decision_reason }}</title></circle>
          </g>
          <g class="point-labels"><text v-for="point in chartPoints" :key="`label-${point.id}`" :x="point.x - 18" :y="point.y - 15" :class="{ 'best-label': point.is_best }">{{ formatChartValue(point.value) }}</text></g>
          <g class="chart-labels"><text v-for="round in totalRounds" :key="round" :x="chartX(round) - 10" y="305">R{{ round }}</text></g>
          <text v-if="!chartPoints.length" x="420" y="170" text-anchor="middle" class="empty-chart-label">启动任务后，每轮真实结果会在此生成</text>
        </svg>
        <div class="chart-legend"><span><i class="legend-dot target"></i>本轮结果</span><span><i class="legend-dot" style="background:#0f9f72"></i>推荐策略轨迹</span><span><i class="legend-dot" style="background:#dc4c43"></i>约束未通过</span></div>
        <div class="optimization-progress" role="progressbar" aria-label="闭环寻优执行进度" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="roundProgress" aria-live="polite"><div><span>已执行 {{ currentRound }} / 最多 {{ totalRounds }} 轮</span><strong>{{ roundProgress }}%</strong></div><i><b :style="{ width: `${roundProgress}%` }"></b></i><p><span class="live-dot" :class="{ muted: !running }"></span>{{ statusCopy }}</p></div>
        <div class="stop-reason-row"><AppIcon name="check" /><div><strong>{{ stopHeadline }}</strong><p>{{ statusCopy }}</p></div><small>最小有效改善 {{ Number(stopping.min_score_improvement).toFixed(1) }} 分</small></div>
      </section>
    </div>

    <section class="panel iteration-panel">
      <div class="section-heading compact"><div><span class="section-kicker">可解释、可追溯</span><h2>{{ technicalView ? '每轮技术参数与指标' : '每轮改了什么，为什么保留或淘汰' }}</h2></div><div class="table-tools"><button type="button" :disabled="!study || Boolean(exporting)" @click="exportStudy('csv')">{{ exporting === 'csv' ? '生成 CSV…' : '导出 CSV 记录' }}</button><button type="button" :disabled="!study || Boolean(exporting)" @click="exportStudy('json')">{{ exporting === 'json' ? '生成 JSON…' : '导出 JSON 合并包' }}</button><button type="button" :disabled="iterations.length < 2" :aria-pressed="comparisonMode" @click="comparisonMode = !comparisonMode">{{ comparisonMode ? '显示全部' : '比较前三名' }}</button><button type="button" :aria-pressed="technicalView" @click="technicalView = !technicalView">{{ technicalView ? '返回通俗视图' : '查看技术参数' }}</button></div></div>
      <div v-if="!technicalView" class="table-wrap">
        <table class="data-table iteration-plain-table">
          <caption class="visually-hidden">闭环寻优通俗迭代记录</caption>
          <thead><tr><th>轮次</th><th>搜索阶段与本轮改动</th><th>结果变化</th><th>硬约束</th><th>综合分</th><th>Agent 决策与原因</th></tr></thead>
          <tbody>
            <tr v-for="row in visibleIterations" :key="row.id" :class="{ 'best-iteration': row.is_best }">
              <td><span class="round-badge">{{ String(row.round).padStart(2, '0') }}</span></td>
              <td class="change-summary"><strong>{{ phaseLabel(row) }} · {{ row.change_summary }}</strong><p>{{ row.search_reason }}</p></td>
              <td><span class="delta-summary" :class="deltaTone(row)">{{ deltaText(row) }}</span></td>
              <td><span class="constraint-summary" :class="row.constraint_failures?.length ? 'is-failed' : 'is-passed'">{{ constraintText(row) }}</span></td>
              <td><strong>{{ formatMetric(row.metrics.overall_score, 2) }}</strong></td>
              <td class="decision-cell"><StatusPill :tone="resultTone(row)">{{ row.decision }}</StatusPill><small>{{ row.decision_reason }}</small></td>
            </tr>
            <tr v-if="!visibleIterations.length"><td colspan="6" class="table-empty-state">尚无寻优轮次。启动后，本轮改动、指标变化和淘汰原因会逐轮写入。</td></tr>
          </tbody>
        </table>
      </div>
      <div v-else class="table-wrap">
        <table class="data-table iteration-tech-table">
          <caption class="visually-hidden">闭环寻优技术参数记录</caption>
          <thead><tr><th>轮次</th><th>动态阈值</th><th>异常阈值</th><th>共线阈值</th><th>时滞上限</th><th>最优时滞</th><th>最小段长</th><th>Fit</th><th>覆盖率</th><th>RMSE</th><th>综合分</th><th>决策</th></tr></thead>
          <tbody>
            <tr v-for="row in visibleIterations" :key="row.id" :class="{ 'best-iteration': row.is_best }"><td><span class="round-badge">{{ String(row.round).padStart(2, '0') }}</span></td><td>{{ Number(row.params.dynamic_threshold).toFixed(2) }}</td><td>{{ Number(row.params.outlier_sigma).toFixed(1) }}σ</td><td>{{ Number(row.params.collinearity_threshold).toFixed(2) }}</td><td>{{ row.params.lag_max_seconds }} {{ lagDisplayUnit }}</td><td>{{ row.diagnostics.optimal_lag_seconds }} {{ lagDisplayUnit }}</td><td>{{ row.params.min_segment_minutes }} {{ segmentDisplayUnit }}</td><td><strong>{{ formatMetric(row.metrics.fit, 4) }}</strong></td><td>{{ (row.metrics.coverage * 100).toFixed(1) }}%</td><td>{{ formatMetric(row.metrics.rmse, 3) }}</td><td><strong>{{ formatMetric(row.metrics.overall_score, 2) }}</strong></td><td><StatusPill :tone="resultTone(row)">{{ row.decision }}</StatusPill></td></tr>
            <tr v-if="!visibleIterations.length"><td colspan="12" class="table-empty-state">尚无寻优轮次。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="bestIteration" class="panel strategy-explanation">
      <h3>为什么选它？</h3>
      <p>选择规则是“先通过全部硬约束，再在可行候选中比较综合分”，不会只挑表面分数最高的一轮。</p>
      <div class="explanation-grid">
        <article class="explanation-item"><strong>可行性优先</strong><span>{{ passedConstraintCount }} / 4 项硬约束通过</span><p>{{ bestIteration.decision_reason }}</p></article>
        <article class="explanation-item"><strong>相对首轮</strong><span>Fit {{ formatSigned(fitImprovement, 4) }} · 覆盖率 {{ formatSigned(coverageImprovement * 100, 1, '个百分点') }}</span><p>综合分 {{ formatSigned(scoreImprovement, 2) }}</p></article>
        <article class="explanation-item"><strong>高分不等于可采纳</strong><span v-if="highestRejected">第 {{ highestRejected.round }} 轮得分 {{ formatMetric(highestRejected.metrics.overall_score, 2) }} 但被淘汰</span><span v-else>当前没有更高分的违约候选</span><p>{{ highestRejected ? highestRejected.constraint_failures.join('、') : '所有决策均保留了明确约束证据。' }}</p></article>
      </div>
      <div class="constraint-gate-grid" role="list" aria-label="最优策略硬约束准入证据">
        <article v-for="gate in constraintGateRows" :key="gate.key" :class="{ 'is-passed': gate.passed, 'is-failed': !gate.passed }" role="listitem">
          <span><AppIcon :name="gate.passed ? 'check' : 'alert'" :size="15" /></span>
          <div><strong>{{ gate.label }}</strong><small>{{ gate.passed ? '准入通过' : '准入未通过' }}</small></div>
          <b>{{ formatMetric(gate.actual, gate.digits) }} {{ gate.operator }} {{ formatMetric(gate.target, gate.digits) }}{{ gate.percent ? '%' : '' }}</b>
        </article>
      </div>
    </section>

    <section class="panel optimization-trust-panel">
      <div class="trust-heading"><div><span class="section-kicker">结果可信度边界</span><h2>{{ evaluationProfile.trust_label }}</h2><p>当前结果足以支撑赛题演示、算法逻辑验收和可复现对比，但不等于现场生产策略已验证。</p></div><StatusPill tone="warning">{{ study?.pipeline_run_id ? '真实数据离线验证 · 非生产就绪' : '仿真验证 · 非生产就绪' }}</StatusPill></div>
      <div class="trust-grid">
        <article class="trust-item"><span>数据快照</span><strong>{{ study?.dataset_source || 'Benchmark v3' }}</strong><small>{{ evaluationProfile.dataset_snapshot }}</small></article>
        <article class="trust-item"><span>验证方式</span><strong>{{ study?.pipeline_run_id ? '真实候选复训' : '18 步自由运行' }}</strong><small>{{ evaluationProfile.validation_method }}</small></article>
        <article class="trust-item"><span>算法与复现</span><strong>{{ algorithmVersion }}</strong><small>{{ study?.pipeline_run_id ? `运行编号 ${study.pipeline_run_id}` : `Seed ${study?.random_seed ?? normalizedRandomSeed} · 相同输入得到相同结果` }}</small></article>
        <article class="trust-item"><span>最优轮泛化证据</span><strong>{{ bestIteration ? `${bestIteration.diagnostics.validation_samples} 个验证样本` : '等待评价' }}</strong><small>{{ bestIteration ? `训练/验证 Fit 差 ${formatSigned(bestIteration.diagnostics.generalization_gap, 4)}` : '启动后生成' }}</small></article>
        <article class="trust-item"><span>时滞边界检查</span><strong>{{ bestIteration ? `${bestIteration.diagnostics.optimal_lag_seconds} / ${bestIteration.params.lag_max_seconds} ${lagDisplayUnit}` : '等待评价' }}</strong><small>{{ bestIteration ? (bestIteration.diagnostics.lag_boundary_hit ? '命中搜索边界，不能据此提前收敛' : '未命中边界，时滞搜索空间充分') : '启动后生成' }}</small></article>
        <article class="trust-item"><span>异常处理证据</span><strong>{{ bestIteration ? `${bestIteration.diagnostics.clipped_points} 个替换点` : '等待评价' }}</strong><small>{{ bestIteration ? (study?.pipeline_run_id ? '来自总控数据清洗 Agent 的真实处理统计' : `基准注入 ${bestIteration.diagnostics.injected_outliers} 个软硬异常，用于检验 Hampel 阈值`) : '启动后生成' }}</small></article>
      </div>
      <p class="trust-warning"><AppIcon name="alert" :size="15" />{{ evaluationProfile.production_gate }}</p>
    </section>

    <section v-if="bestIteration" class="best-strategy-card">
      <div class="best-strategy-header"><span class="trophy-mark">{{ String(bestIteration.round).padStart(2, '0') }}</span><div><span class="section-kicker">{{ study?.pipeline_run_id ? '当前最优真实数据策略' : '当前最优仿真策略' }}</span><h2>第 {{ String(bestIteration.round).padStart(2, '0') }} 轮 · {{ strategyVersion }}</h2><p>只在完成真实评价的候选中按综合分选择；不会直接下发现场。</p></div><StatusPill :tone="isAccepted ? 'brand' : bestIteration.constraint_failures?.length ? 'warning' : 'success'"><AppIcon name="check" :size="14" />{{ study?.pipeline_run_id ? '总控推荐' : isAccepted ? '已固化' : bestIteration.constraint_failures?.length ? '不可采纳' : 'Agent 推荐' }}</StatusPill></div>
      <div class="strategy-params"><div><span>动态阈值</span><strong>{{ Number(bestIteration.params.dynamic_threshold).toFixed(2) }}</strong></div><div><span>异常阈值</span><strong>{{ Number(bestIteration.params.outlier_sigma).toFixed(1) }}σ</strong></div><div><span>共线阈值</span><strong>{{ Number(bestIteration.params.collinearity_threshold).toFixed(2) }}</strong></div><div><span>最优时滞</span><strong>{{ bestIteration.diagnostics.optimal_lag_seconds }} {{ lagDisplayUnit }}</strong></div><div><span>最小段长</span><strong>{{ bestIteration.params.min_segment_minutes }} {{ segmentDisplayUnit }}</strong></div></div>
      <div class="strategy-evidence"><span>Fit <strong>{{ formatMetric(bestIteration.metrics.fit, 4) }}</strong></span><span>验证 R² <strong>{{ formatMetric(bestIteration.metrics.r2, 4) }}</strong></span><span>RMSE <strong>{{ formatMetric(bestIteration.metrics.rmse, 3) }}</strong></span><span>有效片段 <strong>{{ bestIteration.diagnostics.valid_segments }}</strong></span><span>特征数 <strong>{{ bestIteration.diagnostics.feature_count }}</strong></span><span>有效签名 <strong>{{ bestIteration.diagnostics.effective_signature }}</strong></span></div>
      <div class="strategy-actions"><button class="btn btn-secondary" type="button" :disabled="operationBusy" @click="continueExploration">{{ study?.pipeline_run_id ? '由总控基于此结果重新寻优' : '以它为起点继续探索' }}</button><button v-if="!study?.pipeline_run_id" class="btn btn-primary" type="button" :disabled="!canAccept || operationBusy" @click="acceptStrategy">{{ isAccepted ? '演示策略已固化' : isLegacy ? '请先运行 CLSO-2.0' : bestIteration.constraint_failures?.length ? '硬约束未通过' : accepting ? '正在固化…' : '接受为演示策略' }} <AppIcon name="arrow" /></button></div>
    </section>

    <section v-else class="best-strategy-card empty-best-strategy">
      <span><AppIcon name="loop" :size="28" /></span><div><strong>最优策略将在真实计算后生成</strong><p>后端会保存每轮候选、多步模型评价、约束结果、等效签名和决策依据。</p></div>
    </section>
  </div>
</template>
