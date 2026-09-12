const STATUS_LABELS = {
  confirmed: '已确认',
  uncertain: '候选场景',
  ambiguous: '场景不明确',
  unknown: '未知场景',
}

function isNonEmpty(value) {
  return value !== null && value !== undefined && String(value).trim() !== ''
}

export function sceneStateFromProject(project) {
  const id = project?.scenarioId ?? null
  return {
    id,
    display_name: project?.scene || project?.shortName || project?.name || id || '项目场景',
  }
}

export function sceneFromRun(run) {
  const standardization = run?.results?.standardization ?? {}
  const rootTrace = run?.runtime_trace ?? {}
  const standardTrace = standardization.runtime_trace ?? {}
  const rawCandidateEntries = [
    ['final_scene', rootTrace.final_scene ?? standardTrace.final_scene],
    ['selected_scene', rootTrace.selected_scene ?? standardTrace.selected_scene],
    ['agent_scene', rootTrace.agent_scene ?? standardTrace.agent_scene],
    ['detected_scene', rootTrace.detected_scene ?? standardTrace.detected_scene ?? run?.detected_scene],
    ['scene_id', rootTrace.scene_id ?? standardTrace.scene_id],
    ['standardization',
    standardization?.scenario?.scenario_id,
    ],
    ['standardization',
    standardization?.scenario?.scene_id,
    ],
    ['standardization',
    standardization?.scenario,
    ],
  ]
  const candidateEntries = rawCandidateEntries
    .map(([, item]) => {
      if (typeof item === 'string') return item
      if (typeof item === 'object' && item?.scenario_id) return item.scenario_id
      if (typeof item === 'object' && item?.id) return item.id
      return ''
    })
    .map((id, index) => ({ id, source: rawCandidateEntries[index][0] }))
    .filter(({ id }) => isNonEmpty(id) && id !== 'auto')
  const standardScene = standardization?.scenario ?? {}
  const candidate = candidateEntries[0] ?? { id: null, source: 'unresolved' }
  const sceneId = candidate.id
  const displayName = standardScene.scenario_name
    || standardScene.name
    || standardScene.display_name
    || sceneId
    || '等待场景识别'

  return {
    id: sceneId,
    display_name: displayName,
    status: rootTrace.scene_status ?? rootTrace.status ?? standardTrace.scene_status ?? standardTrace.status ?? standardScene.status ?? run?.results?.scene_status ?? 'unknown',
    confidence: [rootTrace.scene_confidence, rootTrace.confidence, standardTrace.scene_confidence, standardTrace.confidence, standardScene.confidence]
      .map(Number).find(Number.isFinite) ?? null,
    source: candidate.source,
  }
}

export function buildSceneState(project, run) {
  const projectScene = sceneStateFromProject(project)
  const dataScene = sceneFromRun(run)
  const mismatch = projectScene.id && dataScene.id && dataScene.id !== projectScene.id

  return {
    project_scene: {
      id: projectScene.id,
      display_name: projectScene.display_name,
    },
    data_scene: {
      id: dataScene.id,
      display_name: dataScene.display_name,
      status: dataScene.status,
      confidence: dataScene.confidence,
      source: dataScene.source,
      status_label: STATUS_LABELS[dataScene.status] || (isNonEmpty(dataScene.status) ? dataScene.status : '待识别'),
    },
    is_mismatch: mismatch,
    data_scene_source: dataScene.source,
    data_scene_status_label: STATUS_LABELS[dataScene.status] || (isNonEmpty(dataScene.status) ? dataScene.status : '待识别'),
    mismatch_text: mismatch
      ? `本次数据按【${dataScene.display_name}】处理；项目预设仍为【${projectScene.display_name}】。两者独立，不影响本次分析。`
      : '',
  }
}

export function sceneMismatchLabel(state) {
  if (!state?.is_mismatch) return '场景一致'
  if ((state.data_scene?.status ?? '') === 'uncertain') return `${state.project_scene?.display_name ?? '项目场景'} ≠ 候选场景 ${state.data_scene?.display_name ?? ''}`
  return state.mismatch_text
}
