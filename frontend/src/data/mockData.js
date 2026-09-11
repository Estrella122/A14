// TODO(mock): 本文件集中管理后端暂未提供的数据。接口返回真实数据后，组件会优先使用真实结果。
const baseMockAgentTrace = {
  source: 'mock',
  total_duration_ms: 4280,
  nodes: [
    { id: 'instruction', name: '用户指令', kind: 'input', duration_ms: 12, status: 'success', input: { message: '提取高信噪比动态数据并闭环寻找最佳模型' }, output: { accepted: true } },
    { id: 'intent', name: '意图解析', kind: 'reason', duration_ms: 286, status: 'success', input: { language: 'zh-CN', scene: '钢铁高炉' }, output: { intent: 'hot_metal_quality_prediction', confidence: 0.96, constraints: ['高信噪比', '因果对齐', '共线性处理'] } },
    { id: 'tools', name: '工具选择', kind: 'tool', duration_ms: 174, status: 'success', input: { capability_count: 9 }, output: { tools: ['cleaning_agent', 'dynamic_segmenter', 'lag_analyzer', 'arx_identifier', 'optimizer'] } },
    { id: 'parameters', name: '参数生成', kind: 'parameter', duration_ms: 238, status: 'success', input: { objective: 'R²↑, RMSE↓, coverage↑' }, output: { resample_rule: '5s', top_k: 8, max_lag: 60, outlier_sigma: 3 } },
    { id: 'execution', name: '算法调用', kind: 'execution', duration_ms: 2140, status: 'success', input: { rows: 29602, variables: 28 }, output: { selected_segments: 11, modeling_rows: 12120, features: 7 } },
    { id: 'evaluation', name: '结果评估', kind: 'evaluation', duration_ms: 492, status: 'success', input: { metrics: ['R²', 'RMSE', 'coverage'] }, output: { r2: 0.913, rmse: 5.14, coverage: 0.82, gate: 'passed' } },
    { id: 'decision', name: '下一步决策', kind: 'decision', duration_ms: 321, status: 'success', input: { best_round: 6, no_improvement_rounds: 2 }, output: { action: 'stop_and_deliver', reason: '连续两轮改善低于阈值' } },
    { id: 'output', name: '最终输出', kind: 'output', duration_ms: 617, status: 'success', input: { evidence_items: 24 }, output: { artifacts: ['modeling_dataset.csv', 'analysis_report.md', 'optimization_report.json'] } },
  ],
  toolchain: ['数据清洗', '动态筛选', '时滞解耦', '系统辨识', '指标评估'],
}

const traceProfiles = {
  blast_furnace: { scene: '钢铁高炉', intent: 'hot_metal_quality_prediction', instruction: '提取高炉高信噪比动态数据并闭环寻找最佳铁水硅模型' },
  debutanizer_column: { scene: '炼油脱丁烷塔', intent: 'bottom_c4_soft_sensor', instruction: '提取脱丁烷塔高信噪比动态数据并闭环寻找最佳塔底 C4 模型' },
  industrial_dryer: { scene: '工业回转干燥器', intent: 'product_moisture_identification', instruction: '提取干燥器高信噪比动态数据并闭环寻找最佳产品含水率模型' },
}

// TODO(mock): 无真实 run_id 时按当前场景生成同结构演示轨迹；接入 trace API 后优先展示真实节点输入输出。
export const mockAgentTraceByScenario = Object.fromEntries(Object.entries(traceProfiles).map(([scenarioId, profile]) => [scenarioId, {
  ...baseMockAgentTrace,
  nodes: baseMockAgentTrace.nodes.map((node) => {
    if (node.id === 'instruction') return { ...node, input: { message: profile.instruction } }
    if (node.id === 'intent') return { ...node, input: { ...node.input, scene: profile.scene }, output: { ...node.output, intent: profile.intent } }
    return { ...node }
  }),
}]))

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

const prediction = (phase = 0, bias = 0, center = 885, slope = 1.28, amplitude = 8) => Array.from({ length: 36 }, (_, index) => Number((center + index * slope + Math.sin(index / 4 + phase) * amplitude + bias).toFixed(3)))
const residuals = (spread = 5) => Array.from({ length: 40 }, (_, index) => Number((Math.sin(index * 1.7) * spread + Math.cos(index * .42) * spread * .45).toFixed(2)))
const experimentProfiles = {
  blast_furnace: { prefix: 'BF', datasets: ['高炉传感器与化验数据-v4', '高炉传感器与化验数据-v3', '高炉扰动验证集-v2'], center: .57, slope: .001, amplitude: .035, scale: .018, note: '增加高炉负荷变化片段' },
  debutanizer_column: { prefix: 'DEB', datasets: ['脱丁烷塔历史数据-v4', '脱丁烷塔历史数据-v3', '回流阶跃验证集-v2'], center: 1.12, slope: -.002, amplitude: .06, scale: .035, note: '增加回流量阶跃片段' },
  industrial_dryer: { prefix: 'DRY', datasets: ['工业干燥器多变量数据-v4', '工业干燥器多变量数据-v3', '热风阶跃验证集-v2'], center: 8.8, slope: -.015, amplitude: .28, scale: .16, note: '增加热风温度激励片段' },
}

function createMockExperiments(profile) {
  const actual = prediction(0, 0, profile.center, profile.slope, profile.amplitude)
  const build = (suffix, time, dataset, preprocessing, algorithm, order, r2, aic, duration, tag, note, phase, bias, spread) => ({
    id: `${profile.prefix}-${suffix}`, time, dataset, preprocessing, algorithm, order, r2, aic, duration, status: 'completed', tag, note,
    actual, predicted: prediction(phase, bias, profile.center, profile.slope, profile.amplitude), residuals: residuals(spread),
  })
  return [
    build('0907-1421', '2026-09-07 14:21', profile.datasets[0], '5s / Hampel 3σ', 'ARX', '2-2-1', .928, 182.4, 42.8, '最佳结果', profile.note, .12, -profile.scale, profile.scale * 2.4),
    build('0907-1350', '2026-09-07 13:50', profile.datasets[0], '5s / Hampel 3σ', 'ARX', '3-2-1', .913, 191.7, 46.1, '候选', '', .25, -profile.scale * 1.6, profile.scale * 3),
    build('0906-1728', '2026-09-06 17:28', profile.datasets[1], '10s / IQR', 'OE', '2-3-1', .887, 209.3, 38.7, '尝试2', '对比 OE 模型', .48, -profile.scale * 2.2, profile.scale * 3.8),
    build('0906-1605', '2026-09-06 16:05', profile.datasets[1], '10s / Hampel 2.5σ', 'ARX', '2-2-2', .901, 198.6, 40.4, '尝试1', '', .34, -profile.scale * 1.9, profile.scale * 3.4),
    build('0905-1043', '2026-09-05 10:43', profile.datasets[2], '5s / 物理边界', '状态空间', '4阶', .865, 224.1, 55.2, '基线', '仿真数据验证', .58, -profile.scale * 2.8, profile.scale * 4.5),
    build('0904-0912', '2026-09-04 09:12', profile.datasets[1], '30s / 线性插值', 'ARX', '1-1-1', .804, 246.8, 26.9, '原始基线', '未做动态优选', .9, -profile.scale * 4.5, profile.scale * 5.8),
  ]
}

// TODO(mock): 后端无历史运行时按当前场景提供离线实验记录；真实接口数据会优先覆盖。
export const mockExperimentsByScenario = Object.fromEntries(Object.entries(experimentProfiles).map(([key, profile]) => [key, createMockExperiments(profile)]))

// TODO(mock): 三套场景测点目前用于数字孪生演示；后端提供实时 tag 快照后按 role 映射输入与质量输出。
export const mockTwinByScenario = {
  blast_furnace: {
    description: '炼铁高炉传感器、炉料与铁水质量状态',
    metrics: [
      { id: 'blast', role: 'input', label: '鼓风流量', value: 3980, unit: 'm³/min', status: 'normal', x: 18, y: 60, trend: [3890, 3918, 3945, 3928, 3962, 3980] },
      { id: 'topPressure', label: '炉顶压力', value: 1.84, unit: 'kgf/cm²', status: 'normal', x: 49, y: 17, trend: [1.78, 1.8, 1.83, 1.82, 1.85, 1.84] },
      { id: 'hotBlastTemp', label: '热风温度', value: 1092, unit: '℃', status: 'normal', x: 25, y: 38, trend: [1078, 1081, 1087, 1090, 1089, 1092] },
      { id: 'burdenRatio', label: '矿焦比', value: 3.27, unit: '', status: 'warning', x: 73, y: 38, trend: [3.18, 3.2, 3.23, 3.3, 3.31, 3.27] },
      { id: 'silicon', role: 'output', label: '铁水硅含量', value: 0.57, unit: '%', status: 'normal', x: 78, y: 78, trend: [.61, .6, .58, .59, .57, .57] },
    ],
  },
  debutanizer_column: {
    description: '脱丁烷塔塔板、回流与轻重组分分离状态',
    metrics: [
      { id: 'columnTopTemp', label: '塔顶温度', value: 64.2, unit: '℃', status: 'normal', x: 42, y: 18, trend: [63.8, 64, 64.1, 64.4, 64.3, 64.2] },
      { id: 'columnPressure', label: '塔顶压力', value: 618, unit: 'kPa', status: 'normal', x: 68, y: 20, trend: [612, 614, 616, 619, 617, 618] },
      { id: 'refluxFlow', role: 'input', label: '回流流量', value: 83.6, unit: 't/h', status: 'normal', x: 78, y: 43, trend: [81.9, 82.3, 82.8, 83.1, 83.8, 83.6] },
      { id: 'trayTemp', label: '第六塔板温度', value: 82.4, unit: '℃', status: 'normal', x: 42, y: 54, trend: [81.7, 81.9, 82.1, 82.2, 82.5, 82.4] },
      { id: 'bottomC4', role: 'output', label: '塔底 C4 含量', value: 1.16, unit: '%', status: 'warning', x: 70, y: 79, trend: [1.02, 1.08, 1.11, 1.19, 1.21, 1.16] },
    ],
  },
  industrial_dryer: {
    description: '回转滚筒、热风系统与产品含水率状态',
    metrics: [
      { id: 'wetFeed', label: '湿料进料量', value: 38.2, unit: 't/h', status: 'normal', x: 23, y: 27, trend: [37.1, 37.4, 37.9, 38, 38.4, 38.2] },
      { id: 'hotAirTemp', role: 'input', label: '入口热风温度', value: 181.4, unit: '℃', status: 'normal', x: 17, y: 60, trend: [176.8, 178.3, 179.6, 180.8, 182.1, 181.4] },
      { id: 'airFlow', label: '热风流量', value: 42180, unit: 'Nm³/h', status: 'normal', x: 36, y: 75, trend: [41420, 41680, 41910, 42160, 42310, 42180] },
      { id: 'exhaustHumidity', label: '尾气湿度', value: 60.8, unit: '%RH', status: 'normal', x: 78, y: 25, trend: [59.1, 59.7, 60.2, 60.6, 61, 60.8] },
      { id: 'productMoisture', role: 'output', label: '产品含水率', value: 8.7, unit: '%', status: 'warning', x: 80, y: 74, trend: [9.4, 9.2, 9, 8.8, 8.6, 8.7] },
    ],
  },
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
