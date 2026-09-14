export const EXECUTION_STATUS = {
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
