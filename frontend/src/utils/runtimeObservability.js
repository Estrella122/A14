const CAPABILITY_LABELS = {
  DATA_PROFILING: '数据画像',
  DATA_QUALITY_ANALYSIS: '数据质量分析',
  TREND_ANALYSIS: '趋势分析',
  TIME_SERIES_ANALYSIS: '时序分析',
  ANOMALY_DETECTION: '异常检测',
  CORRELATION_ANALYSIS: '相关性分析',
  PROCESS_STABILITY: '过程稳定性',
  ENERGY_ANALYSIS: '能耗分析',
  EQUIPMENT_HEALTH: '设备健康',
  QUALITY_ANALYSIS: '质量分析',
  OPERATING_STATE: '运行工况',
  BOTTLENECK_ANALYSIS: '瓶颈分析',
  MISSING_DATA_ANALYSIS: '缺失数据分析',
  ROOT_CAUSE_CANDIDATES: '根因候选',
  SEGMENTATION: '动态分段',
  MODELING: '系统建模',
  OPTIMIZATION: '闭环优化',
}

export const SCORE_DIMENSIONS = [
  ['semantic_intent_score', 'Semantic Intent'],
  ['context_fit_score', 'Context Fit'],
  ['data_precondition_score', 'Data Preconditions'],
  ['scene_fit_score', 'Scene Fit'],
  ['dependency_readiness_score', 'Dependency Readiness'],
  ['lexical_recall_score', 'Lexical Recall'],
]

export function capabilityLabel(id) {
  return CAPABILITY_LABELS[id] ?? String(id || '').replaceAll('_', ' ')
}

export function capabilityStatus(candidate) {
  if (candidate?.selected) return 'selected'
  // Candidates that were not selected did not fail this turn. Missing optional
  // evidence is useful context, but should not render as an execution error.
  if (candidate?.status === 'blocked') return 'skipped'
  if (candidate?.status === 'deferred' && candidate?.producible_artifacts?.length) return 'deferred'
  return 'skipped'
}

export function buildRuntimeObservability(source = {}) {
  const answerStatus = {
    llm: source.llm,
    answer_mode: source.answer_mode,
    knowledge: source.answer_context?.retrieval_observability,
    context: source.answer_context?.context_observability,
    capability_availability: source.capability_availability,
  }
  if (source.runtime_observability) return { ...source.runtime_observability, ...answerStatus }
  const plan = source.skill_plan ?? source.plan ?? {}
  const analysis = plan.analysis ?? {}
  return {
    ...answerStatus,
    capabilities: analysis.capability_resolution?.candidates ?? [],
    execution_dag: analysis.execution_plan?.core ?? { steps: [], target_groups: [] },
    skill_loading: analysis.skill_runtime ?? {},
    executor_results: source.core_skill_execution_results ?? [],
    artifacts: source.artifact_registry ?? [],
  }
}

export function capabilityCards(runtime = {}) {
  return (runtime.capabilities ?? []).map((candidate) => ({
    ...candidate,
    id: candidate.candidate,
    name: candidate.display_name ?? capabilityLabel(candidate.candidate),
    ui_status: capabilityStatus(candidate),
    score: Number(candidate.final_score ?? 0),
    required_artifacts: candidate.required_artifacts ?? Object.keys(candidate.artifact_readiness ?? {}),
    missing_artifacts: candidate.missing_artifacts ?? [],
    missing_contract_fields: candidate.missing_contract_fields ?? [],
  }))
}

export function dagNodes(runtime = {}) {
  const results = Object.fromEntries((runtime.executor_results ?? []).map((result) => [result.executor ?? result.skill_id, result]))
  const steps = runtime.execution_dag?.steps ?? []
  const producers = {}
  steps.forEach((step) => (step.produces_artifacts ?? []).forEach((artifact) => { producers[artifact] = step.executor ?? step.id }))
  return steps.map((step) => {
    const result = results[step.executor ?? step.id]
    const missing = step.missing_artifacts ?? []
    const waiting = missing.map((artifact) => ({ artifact, producer: producers[artifact] })).filter((item) => item.producer)
    return {
      ...step,
      initial_status: step.readiness_status ?? 'executable',
      status: result?.status ?? step.readiness_status ?? 'executable',
      reason: result?.reason ?? step.readiness_reason ?? '',
      result,
      waiting,
      lifecycle: [step.readiness_status, result?.status].filter((value, index, all) => value && all.indexOf(value) === index),
    }
  })
}

export function artifactChain(runtime = {}) {
  return (runtime.artifacts ?? []).map((artifact) => ({
    ...artifact,
    producer_label: artifact.producer ? `${artifact.producer} Executor` : '未记录',
    short_hash: artifact.content_hash ? `${artifact.content_hash.slice(0, 12)}…` : '—',
  }))
}

export function executorHighlights(result) {
  if (!result) return []
  const metrics = result.metrics ?? {}
  if ((result.executor ?? result.skill_id) === 'optimization') {
    return [
      ['候选数', metrics.candidate_count],
      ['Validation R²', metrics.validation_scores?.r2],
      ['Test R²', metrics.test_score?.r2],
      ['训练覆盖率', metrics.validation_scores?.coverage, 'percent'],
      ['最低覆盖率', metrics.constraints?.min_coverage, 'percent'],
    ].filter((item) => item[1] !== undefined && item[1] !== null)
  }
  if ((result.executor ?? result.skill_id) === 'segmentation') {
    const evidence = result.evidence?.[0] ?? {}
    return [
      ['候选窗口', metrics.candidate_count], ['接纳动态段', metrics.selected_count],
      ['建模数据行', metrics.selected_row_count], ['Validation 读取', evidence.validation_rows_read],
      ['Test 读取', evidence.test_rows_read],
    ].filter((item) => item[1] !== undefined && item[1] !== null)
  }
  return []
}
