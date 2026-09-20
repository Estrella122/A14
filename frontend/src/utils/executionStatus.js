export const EXECUTION_STATUS = {
  needs_review: { label: '搜索已结束，需复核', tone: 'warning', icon: 'alert' },
  cancelled: { label: '已取消', tone: 'neutral', icon: 'clock' },
  timed_out: { label: '执行超时', tone: 'warning', icon: 'alert' },
  pending_candidate_search: { label: '准备完成，等待候选拟合', tone: 'neutral', icon: 'clock' },
  fitted_no_winner: { label: '已拟合，无合格赢家', tone: 'warning', icon: 'alert' },
  not_fitted: { label: '尚无有效拟合模型', tone: 'neutral', icon: 'clock' },
  executed: { label: '已执行', tone: 'success', icon: 'check' },
  evidence_only: { label: '仅读取证据', tone: 'brand', icon: 'database' },
  selected: { label: '已选择', tone: 'success', icon: 'check' },
  deferred: { label: '等待上游依赖', tone: 'warning', icon: 'clock' },
  executable: { label: '可执行', tone: 'brand', icon: 'arrow' },
  success: { label: '成功', tone: 'success', icon: 'check' },
  partial: { label: '已完成，但存在约束未满足', tone: 'warning', icon: 'alert' },
  blocked: { label: '等待前置条件', tone: 'warning', icon: 'clock' },
  failed: { label: '执行失败', tone: 'danger', icon: 'alert' },
  skipped: { label: '本轮未调用', tone: 'neutral', icon: 'clock' },
  unavailable: { label: '本轮暂无证据', tone: 'neutral', icon: 'clock' },
  completed: { label: '成功', tone: 'success', icon: 'check' },
  running: { label: '执行中', tone: 'brand', icon: 'loop' },
  pending: { label: '等待执行', tone: 'neutral', icon: 'clock' },
}

export function executionStatus(status) {
  return EXECUTION_STATUS[status] ?? { label: status || '未执行', tone: 'neutral', icon: 'clock' }
}

export function pipelineStatus(run) {
  const outcome = run?.results?.optimization?.optimization_outcome
  const labels = { no_feasible_candidate: '搜索结束，无合格候选', insufficient_input: '拟合或评价条件不足', failed: '程序或服务异常', cancelled: '已取消', timed_out: '执行超时', unknown: '历史记录不完整' }
  return labels[outcome] || executionStatus(run?.status).label
}
