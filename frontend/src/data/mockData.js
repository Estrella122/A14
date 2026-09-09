// TODO(mock): 本文件集中管理后端暂未提供的数据。接口返回真实数据后，组件会优先使用真实结果。
export const mockAgentTrace = {
  source: 'mock',
  total_duration_ms: 4280,
  nodes: [
    { id: 'instruction', name: '用户指令', kind: 'input', duration_ms: 12, status: 'success', input: { message: '提取高信噪比动态数据并闭环寻找最佳模型' }, output: { accepted: true } },
    { id: 'intent', name: '意图解析', kind: 'reason', duration_ms: 286, status: 'success', input: { language: 'zh-CN', scene: '加热炉' }, output: { intent: 'closed_loop_identification', confidence: 0.96, constraints: ['高信噪比', '共线性处理'] } },
    { id: 'tools', name: '工具选择', kind: 'tool', duration_ms: 174, status: 'success', input: { capability_count: 9 }, output: { tools: ['cleaning_agent', 'dynamic_segmenter', 'lag_analyzer', 'arx_identifier', 'optimizer'] } },
    { id: 'parameters', name: '参数生成', kind: 'parameter', duration_ms: 238, status: 'success', input: { objective: 'R²↑, RMSE↓, coverage↑' }, output: { resample_rule: '5s', top_k: 8, max_lag: 60, outlier_sigma: 3 } },
    { id: 'execution', name: '算法调用', kind: 'execution', duration_ms: 2140, status: 'success', input: { rows: 48000, variables: 36 }, output: { selected_segments: 11, modeling_rows: 12120, features: 7 } },
    { id: 'evaluation', name: '结果评估', kind: 'evaluation', duration_ms: 492, status: 'success', input: { metrics: ['R²', 'RMSE', 'coverage'] }, output: { r2: 0.913, rmse: 5.14, coverage: 0.82, gate: 'passed' } },
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

const prediction = (phase = 0, bias = 0) => Array.from({ length: 36 }, (_, index) => Number((885 + index * 1.28 + Math.sin(index / 4 + phase) * 8 + bias).toFixed(2)))
const residuals = (spread = 5) => Array.from({ length: 40 }, (_, index) => Number((Math.sin(index * 1.7) * spread + Math.cos(index * .42) * spread * .45).toFixed(2)))
export const mockExperiments = [
  { id: 'RUN-0907-1421', time: '2026-09-07 14:21', dataset: '2#炉历史数据-v4', preprocessing: '5s / Hampel 3σ', algorithm: 'ARX', order: '2-2-1', r2: .928, aic: 182.4, duration: 42.8, status: 'completed', tag: '最佳结果', note: '增加高负荷阶跃片段', actual: prediction(0), predicted: prediction(.12, -.8), residuals: residuals(3.2) },
  { id: 'RUN-0907-1350', time: '2026-09-07 13:50', dataset: '2#炉历史数据-v4', preprocessing: '5s / Hampel 3σ', algorithm: 'ARX', order: '3-2-1', r2: .913, aic: 191.7, duration: 46.1, status: 'completed', tag: '候选', note: '', actual: prediction(0), predicted: prediction(.25, -1.4), residuals: residuals(4.1) },
  { id: 'RUN-0906-1728', time: '2026-09-06 17:28', dataset: '2#炉历史数据-v3', preprocessing: '10s / IQR', algorithm: 'OE', order: '2-3-1', r2: .887, aic: 209.3, duration: 38.7, status: 'completed', tag: '尝试2', note: '对比 OE 模型', actual: prediction(0), predicted: prediction(.48, -2.1), residuals: residuals(5.3) },
  { id: 'RUN-0906-1605', time: '2026-09-06 16:05', dataset: '2#炉历史数据-v3', preprocessing: '10s / Hampel 2.5σ', algorithm: 'ARX', order: '2-2-2', r2: .901, aic: 198.6, duration: 40.4, status: 'completed', tag: '尝试1', note: '', actual: prediction(0), predicted: prediction(.34, -1.8), residuals: residuals(4.7) },
  { id: 'RUN-0905-1043', time: '2026-09-05 10:43', dataset: '仿真阶跃集-v2', preprocessing: '5s / 物理边界', algorithm: '状态空间', order: '4阶', r2: .865, aic: 224.1, duration: 55.2, status: 'completed', tag: '基线', note: '仿真数据验证', actual: prediction(0), predicted: prediction(.58, -2.8), residuals: residuals(6.1) },
  { id: 'RUN-0904-0912', time: '2026-09-04 09:12', dataset: '2#炉历史数据-v2', preprocessing: '30s / 线性插值', algorithm: 'ARX', order: '1-1-1', r2: .804, aic: 246.8, duration: 26.9, status: 'completed', tag: '原始基线', note: '未做动态优选', actual: prediction(0), predicted: prediction(.9, -4.5), residuals: residuals(7.8) },
]

export const mockTwin = {
  metrics: [
    { id: 'gas', label: '煤气流量', value: 18620, unit: 'Nm³/h', status: 'normal', x: 13, y: 58, trend: [18120, 18280, 18410, 18360, 18520, 18620] },
    { id: 'pressure', label: '炉膛压力', value: -18, unit: 'Pa', status: 'warning', x: 48, y: 43, trend: [-24, -21, -19, -17, -14, -18] },
    { id: 'temp', label: '炉温', value: 1248, unit: '℃', status: 'normal', x: 54, y: 27, trend: [1236, 1240, 1245, 1244, 1247, 1248] },
    { id: 'slabIn', label: '入炉钢坯', value: 842, unit: '℃', status: 'normal', x: 22, y: 76, trend: [836, 838, 839, 841, 843, 842] },
    { id: 'slabOut', label: '出炉温度', value: 1186, unit: '℃', status: 'normal', x: 83, y: 76, trend: [1172, 1177, 1180, 1183, 1184, 1186] },
  ],
}

export const mockTransferFunction = { numerator: [1], denominator: [1, .5, 1], sampleTime: .1, label: 'G(s) = 1 / (s² + 0.5s + 1)' }

export const mockQualityDimensions = [
  { key: 'completeness', label: '完整性', score: 96, method: '1 - 缺失单元格数 / 总单元格数', value: '缺失率 4.0%', suggestion: '保持当前缺失修复策略。' },
  { key: 'consistency', label: '一致性', score: 94, method: '采样间隔落在中位周期 ±5% 的比例', value: '时间戳均匀率 94%', suggestion: '对少量时间漂移点执行重采样。' },
  { key: 'snr', label: '信噪比', score: 88, method: '有效动态能量与高频残差能量之比归一化', value: '估计 SNR 21.7 dB', suggestion: '保留现有滤波强度，避免抹平阶跃。' },
  { key: 'dynamic', label: '动态性', score: 76, method: '非稳态高价值窗口占全部窗口的比例', value: '非稳态占比 24.8%', suggestion: '建议增加阶跃激励以提升动态性得分。' },
  { key: 'collinearity', label: '共线健康度', score: 82, method: '按最大 VIF 与高相关变量对数量综合折算', value: '最大 VIF 7.4', suggestion: '复核两组高相关燃烧变量。' },
  { key: 'anomaly', label: '异常健康度', score: 91, method: '1 - 工艺越界与统计异常点占比', value: '异常率 2.7%', suggestion: '隔离压力尖峰后再进入辨识。' },
]
