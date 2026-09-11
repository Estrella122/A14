// TODO(mock): 本文件集中管理后端暂未提供的数据。接口返回真实数据后，组件会优先使用真实结果。
export const mockAgentTrace = {
  source: 'mock',
  total_duration_ms: 4280,
  nodes: [
    { id: 'instruction', name: '用户指令', kind: 'input', duration_ms: 12, status: 'success', input: { message: '提取高炉高信噪比动态数据并预测铁水硅含量' }, output: { accepted: true } },
    { id: 'intent', name: '意图解析', kind: 'reason', duration_ms: 286, status: 'success', input: { language: 'zh-CN', scene: '钢铁高炉' }, output: { intent: 'hot_metal_quality_prediction', confidence: 0.96, constraints: ['因果化验对齐', '高信噪比', '共线性处理'] } },
    { id: 'tools', name: '工具选择', kind: 'tool', duration_ms: 174, status: 'success', input: { capability_count: 9 }, output: { tools: ['cleaning_agent', 'dynamic_segmenter', 'lag_analyzer', 'arx_identifier', 'optimizer'] } },
    { id: 'parameters', name: '参数生成', kind: 'parameter', duration_ms: 238, status: 'success', input: { objective: 'R²↑, RMSE↓, coverage↑' }, output: { resample_rule: '1h', top_k: 8, max_lag: 24, lab_alignment: 'causal_asof_backward' } },
    { id: 'execution', name: '算法调用', kind: 'execution', duration_ms: 2140, status: 'success', input: { rows: 703, variables: 31 }, output: { target: 'hot_metal_si', leakage_guard: true } },
    { id: 'evaluation', name: '结果评估', kind: 'evaluation', duration_ms: 492, status: 'success', input: { metrics: ['R²', 'RMSE', 'coverage'] }, output: { evidence_source: 'real_dataset', gate: 'pending_run' } },
    { id: 'decision', name: '下一步决策', kind: 'decision', duration_ms: 321, status: 'success', input: { best_round: 6, no_improvement_rounds: 2 }, output: { action: 'stop_and_deliver', reason: '连续两轮改善低于阈值' } },
    { id: 'output', name: '最终输出', kind: 'output', duration_ms: 617, status: 'success', input: { evidence_items: 24 }, output: { artifacts: ['modeling_dataset.csv', 'analysis_report.md', 'optimization_report.json'] } },
  ],
  toolchain: ['数据清洗', '动态筛选', '时滞解耦', '系统辨识', '指标评估'],
}

export const pipelineNodeTypes = [
  { type: 'source', label: '数据源', icon: 'database', description: 'CSV 上传 / 仿真生成', color: '#0ea5e9', defaults: { source: 'CSV上传', file: 'historian.csv' } },
  { type: 'cleaning', label: '数据清洗', icon: 'clean', description: '缺失与异常处理', color: '#14b8a6', defaults: { resample: '5s', method: 'Hampel', sigma: 3 } },
  { type: 'selection', label: '动态段筛选', icon: 'segments', description: '高信噪比片段', color: '#22c55e', defaults: { threshold: 80, topK: 8, window: 30 } },
  { type: 'lag', label: '时滞补偿', icon: 'clock', description: '互相关时滞估计', color: '#8b5cf6', defaults: { maxLag: 60, method: 'cross-correlation' } },
  { type: 'collinearity', label: '共线性剔除', icon: 'network', description: 'VIF 与相关系数', color: '#a855f7', defaults: { vif: 10, correlation: 0.95 } },
  { type: 'identification', label: '系统辨识', icon: 'model', description: 'ARX / OE / 状态空间', color: '#2563eb', defaults: { algorithm: 'ARX', na: 2, nb: 2, nk: 1 } },
  { type: 'evaluation', label: '模型评估', icon: 'check', description: 'R²、RMSE、AIC', color: '#f59e0b', defaults: { validation: 25, metric: 'R²' } },
  { type: 'optimization', label: '闭环寻优', icon: 'loop', description: '指标反馈自动调参', color: '#f97316', defaults: { rounds: 8, objective: 'R²最大' } },
  { type: 'report', label: '报告生成', icon: 'report', description: '图文报告与数据集', color: '#64748b', defaults: { format: 'PDF + CSV', includeTrace: true } },
]

export const defaultPipelineGraph = {
  name: 'Agent 标准闭环流水线',
  nodes: pipelineNodeTypes.map((item, index) => ({ id: `node-${index + 1}`, type: item.type, x: 54 + (index % 3) * 255, y: 48 + Math.floor(index / 3) * 160, config: { ...item.defaults } })),
  edges: pipelineNodeTypes.slice(0, -1).map((_, index) => ({ id: `edge-${index + 1}`, from: `node-${index + 1}`, to: `node-${index + 2}` })),
}

const prediction = (phase = 0, bias = 0) => Array.from({ length: 36 }, (_, index) => Number((0.48 + Math.sin(index / 4 + phase) * 0.045 + bias).toFixed(3)))
const residuals = (spread = .04) => Array.from({ length: 40 }, (_, index) => Number((Math.sin(index * 1.7) * spread + Math.cos(index * .42) * spread * .45).toFixed(3)))
export const mockExperiments = [
  { id: 'BF-RUN-006', time: '2026-09-11 09:42', dataset: '高炉真实数据-720h', preprocessing: '1h / 因果化验对齐', algorithm: 'ARX', order: '2-2-1', r2: .712, aic: -318.4, duration: 38.8, status: 'completed', tag: '最佳结果', note: '仅供离线界面降级展示', actual: prediction(0), predicted: prediction(.12, -.006), residuals: residuals(.025) },
  { id: 'BF-RUN-005', time: '2026-09-11 09:26', dataset: '高炉真实数据-720h', preprocessing: '1h / Top8动态段', algorithm: 'ARX', order: '3-2-1', r2: .684, aic: -302.1, duration: 41.3, status: 'completed', tag: '候选', note: '', actual: prediction(0), predicted: prediction(.25, -.009), residuals: residuals(.032) },
  { id: 'BF-RUN-004', time: '2026-09-11 09:08', dataset: '高炉真实数据-720h', preprocessing: '1h / VIF消减', algorithm: 'OE', order: '2-3-1', r2: .653, aic: -289.3, duration: 44.7, status: 'completed', tag: '尝试2', note: '离线降级示例，不作为真实运行结论', actual: prediction(0), predicted: prediction(.48, -.012), residuals: residuals(.037) },
  { id: 'BF-RUN-003', time: '2026-09-11 08:45', dataset: '高炉真实数据-720h', preprocessing: '1h / 物理边界', algorithm: 'ARX', order: '2-2-2', r2: .621, aic: -276.6, duration: 37.4, status: 'completed', tag: '尝试1', note: '', actual: prediction(0), predicted: prediction(.34, -.014), residuals: residuals(.041) },
  { id: 'BF-RUN-002', time: '2026-09-11 08:20', dataset: '高炉真实数据-720h', preprocessing: '1h / 全量变量', algorithm: '状态空间', order: '4阶', r2: .587, aic: -251.1, duration: 51.2, status: 'completed', tag: '基线', note: '', actual: prediction(0), predicted: prediction(.58, -.018), residuals: residuals(.048) },
  { id: 'BF-RUN-001', time: '2026-09-11 08:02', dataset: '高炉真实数据-720h', preprocessing: '1h / 原始基线', algorithm: 'ARX', order: '1-1-1', r2: .544, aic: -230.8, duration: 29.9, status: 'completed', tag: '原始基线', note: '', actual: prediction(0), predicted: prediction(.9, -.022), residuals: residuals(.056) },
]

export const mockTwin = {
  metrics: [
    { id: 'blast', label: '鼓风流量', value: 3514, unit: 'm³/min', status: 'normal', x: 17, y: 68, trend: [3488, 3514, 3509, 3505, 3498, 3522] },
    { id: 'topPressure', label: '炉顶压力', value: 1.30, unit: 'kgf/cm²', status: 'normal', x: 67, y: 20, trend: [1.30, 1.30, 1.31, 1.30, 1.29, 1.30] },
    { id: 'hotBlast', label: '热风温度', value: 1118, unit: '℃', status: 'normal', x: 26, y: 52, trend: [1117, 1131, 1112, 1108, 1122, 1118] },
    { id: 'co2', label: '炉顶煤气 CO₂', value: 22.97, unit: '%', status: 'normal', x: 78, y: 36, trend: [22.62, 22.97, 23.31, 23.38, 23.10, 22.97] },
    { id: 'si', label: '铁水硅含量', value: 0.50, unit: '%', status: 'warning', x: 72, y: 82, trend: [.50, .50, .62, .62, .60, .55] },
  ],
}

export const mockTransferFunction = { numerator: [.12], denominator: [1, .8, .12], sampleTime: 1, label: '高炉Si归一化示例 G(s) = 0.12 / (s² + 0.8s + 0.12)' }

export const mockQualityDimensions = [
  { key: 'completeness', label: '完整性', score: 96, method: '1 - 缺失单元格数 / 总单元格数', value: '缺失率 4.0%', suggestion: '保持当前缺失修复策略。' },
  { key: 'consistency', label: '一致性', score: 94, method: '采样间隔落在中位周期 ±5% 的比例', value: '时间戳均匀率 94%', suggestion: '对少量时间漂移点执行重采样。' },
  { key: 'snr', label: '信噪比', score: 88, method: '有效动态能量与高频残差能量之比归一化', value: '估计 SNR 21.7 dB', suggestion: '保留现有滤波强度，避免抹平阶跃。' },
  { key: 'dynamic', label: '动态性', score: 76, method: '非稳态高价值窗口占全部窗口的比例', value: '非稳态占比 24.8%', suggestion: '建议增加阶跃激励以提升动态性得分。' },
  { key: 'collinearity', label: '共线健康度', score: 82, method: '按最大 VIF 与高相关变量对数量综合折算', value: '最大 VIF 7.4', suggestion: '复核两组高相关燃烧变量。' },
  { key: 'anomaly', label: '异常健康度', score: 91, method: '1 - 工艺越界与统计异常点占比', value: '异常率 2.7%', suggestion: '隔离压力尖峰后再进入辨识。' },
]
