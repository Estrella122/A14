export const pipelineNodeTypes = [
  { type: 'source', label: '数据源', icon: 'database', description: '当前真实 CSV 任务', color: '#0ea5e9', defaults: { source: '当前CSV任务' } },
  { type: 'cleaning', label: '数据清洗', icon: 'clean', description: '缺失与异常处理', color: '#14b8a6', defaults: { resample: '10s', method: 'causal', sigma: 3 } },
  { type: 'selection', label: '动态段筛选', icon: 'segments', description: '高信噪比片段', color: '#22c55e', defaults: { threshold: 80, topK: 8, window: 30 } },
  { type: 'lag', label: '时滞补偿', icon: 'clock', description: '互相关时滞估计', color: '#8b5cf6', defaults: { maxLag: 60, method: 'cross-correlation' } },
  { type: 'collinearity', label: '共线性剔除', icon: 'network', description: 'VIF 与相关系数', color: '#a855f7', defaults: { vif: 10, correlation: 0.95 } },
  { type: 'identification', label: '系统辨识', icon: 'model', description: 'AR/ARX 结构辨识', color: '#2563eb', defaults: { algorithm: 'ARX', na: 2, nb: 2, nk: 1 } },
  { type: 'evaluation', label: '模型评估', icon: 'check', description: '独立测试与工程评审', color: '#f59e0b', defaults: { validation: 20, metric: 'R² / RMSE / MAE' } },
  { type: 'optimization', label: '闭环寻优', icon: 'loop', description: '验证集反馈自动调参', color: '#f97316', defaults: { rounds: 8, objective: '综合得分' } },
  { type: 'report', label: '报告生成', icon: 'report', description: '可审计报告与数据产物', color: '#64748b', defaults: { format: 'Markdown + CSV + JSON', includeTrace: true } },
]

export const defaultPipelineGraph = {
  name: 'Agent 标准闭环流水线',
  nodes: pipelineNodeTypes.map((item, index) => ({ id: `node-${index + 1}`, type: item.type, x: 54 + (index % 3) * 255, y: 48 + Math.floor(index / 3) * 160, config: { ...item.defaults } })),
  edges: pipelineNodeTypes.slice(0, -1).map((_, index) => ({ id: `edge-${index + 1}`, from: `node-${index + 1}`, to: `node-${index + 2}` })),
}
