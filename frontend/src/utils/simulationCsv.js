const blastFurnaceHeaders = ['dt', 'Fb', 'Ph', 'Pc', 'Tc', 'Fo', 'dP', 'dPu', 'dPl', 'Pt', 'Th', 'CO2', 'H2', 'Tt1', 'Tt2', 'Tt3', 'Tt4', 'R', 'Si']

function seededRandom(seed) {
  let value = seed >>> 0
  return () => {
    value = (1664525 * value + 1013904223) >>> 0
    return value / 4294967296
  }
}

function noise(random, scale) {
  return (random() + random() + random() + random() - 2) * scale
}

function round(value, digits = 3) {
  return Number(value.toFixed(digits))
}

function formatHourTimestamp(index) {
  const date = new Date(Date.UTC(2013, 0, 1, index))
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:00:00`
}

function csvCell(value) {
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

// 仅用于明确标识的可控仿真压力测试；高炉主流程使用项目内置的 Mendeley 真实数据切片。
export function buildBlastFurnaceSimulationCsv(config = {}) {
  const steady = Math.min(75, Math.max(20, Number(config.steady) || 45))
  const step = Math.min(35, Math.max(5, Number(config.step) || 18))
  const noiseSigma = Math.min(6, Math.max(1, Number(config.noise) || 3))
  const anomalyCount = Math.min(30, Math.max(0, Math.round(Number(config.anomalies) || 0)))
  const rowCount = 2_160
  const steadyRows = Math.round(rowCount * steady / 100)
  const seed = steady * 100_000 + step * 1_000 + noiseSigma * 100 + anomalyCount
  const random = seededRandom(seed)
  const anomalyIndexes = new Map()

  for (let i = 0; i < anomalyCount; i += 1) {
    const index = Math.floor((i + 1) * rowCount / (anomalyCount + 1))
    anomalyIndexes.set(index, i % 4)
  }

  let silicon = .49
  const rows = []
  const stepPattern = [0, 1, -.7, .45, -.3]

  for (let i = 0; i < rowCount; i += 1) {
    const dynamicIndex = Math.max(0, i - steadyRows)
    const phase = i < steadyRows ? 0 : Math.floor(dynamicIndex / Math.max(48, Math.floor((rowCount - steadyRows) / stepPattern.length))) % stepPattern.length
    const stepFactor = stepPattern[phase]
    const slow = Math.sin(i / 110)
    const noiseFactor = noiseSigma / 3
    let blast = 3500 * (1 + stepFactor * step / 100) + slow * 90 + noise(random, 22 * noiseFactor)
    let oxygen = 19000 * (1 + stepFactor * step / 125) + Math.sin(i / 83) * 900 + noise(random, 380 * noiseFactor)
    const oreCoke = 3.92 - stepFactor * .08 + Math.sin(i / 170) * .07 + noise(random, .012 * noiseFactor)
    const hotBlast = 1120 + stepFactor * 24 + Math.sin(i / 64) * 13 + noise(random, 2.2 * noiseFactor)
    const hotPressure = 2.84 + (blast - 3500) / 5200 + noise(random, .018 * noiseFactor)
    const coldPressure = hotPressure + .12 + noise(random, .012 * noiseFactor)
    const coldTemp = 106 + Math.sin(i / 140) * 7 + noise(random, .8 * noiseFactor)
    let pressureDrop = 1.49 + (blast - 3500) / 6800 + noise(random, .018 * noiseFactor)
    const upperDrop = pressureDrop * .35 + noise(random, .012 * noiseFactor)
    const lowerDrop = pressureDrop - upperDrop
    const topPressure = 1.30 + noise(random, .004 * noiseFactor)
    const co2 = 22.3 + (oreCoke - 3.9) * 1.4 + noise(random, .22 * noiseFactor)
    const h2 = 6.6 + oxygen / 55000 + noise(random, .18 * noiseFactor)
    const topBase = 150 + (blast - 3500) * .035 - (oreCoke - 3.9) * 42
    const siTarget = .48 - (oxygen - 19000) / 180000 - (hotBlast - 1120) / 2600 + (oreCoke - 3.9) * .19
    silicon += (siTarget - silicon) / 10 + noise(random, .0035 * noiseFactor)

    const anomalyType = anomalyIndexes.get(i)
    if (anomalyType === 0) blast *= .35
    if (anomalyType === 1) oxygen *= 1.8
    if (anomalyType === 2) pressureDrop += 1.1
    if (anomalyType === 3) silicon += .35

    rows.push([
      formatHourTimestamp(i), round(blast, 2), round(hotPressure, 3), round(coldPressure, 3), round(coldTemp, 2),
      round(oxygen, 2), round(pressureDrop, 3), round(upperDrop, 3), round(lowerDrop, 3), round(topPressure, 3),
      round(hotBlast, 2), round(co2, 3), round(h2, 3), round(topBase + noise(random, 4), 2),
      round(topBase - 9 + noise(random, 4), 2), round(topBase + 6 + noise(random, 4), 2),
      round(topBase - 13 + noise(random, 4), 2), round(oreCoke, 3), round(silicon, 4),
    ])
  }

  const csv = [blastFurnaceHeaders, ...rows].map((row) => row.map(csvCell).join(',')).join('\n')
  const configLabel = `S${steady}_P${step}_N${noiseSigma}_A${anomalyCount}`
  return {
    csv: `\ufeff${csv}`,
    name: `sim_BF-SI_${configLabel}.csv`,
    rowCount,
    variableCount: blastFurnaceHeaders.length - 1,
    period: '90 d · 1 h 采样',
    summary: `高炉仿真压力测试 · 无阶跃基段 ${steady}%（仍含周期扰动） · 激励 ${step}% · 噪声 ${noiseSigma}σ · 异常 ${anomalyCount} 点`,
  }
}

const debutanizerHeaders = [
  '采集时间',
  '塔顶温度(℃)',
  '塔顶压力(kPa)',
  '回流流量(t/h)',
  '后续流程流量(t/h)',
  '第六塔板温度(℃)',
  '塔底温度A(℃)',
  '塔底温度B(℃)',
  'C4浓度(%)',
]

function formatMinuteTimestamp(index) {
  const date = new Date(Date.UTC(2026, 6, 1, 0, index, 0))
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`
}

export function buildDebutanizerSimulationCsv(config = {}) {
  const steady = Math.min(75, Math.max(20, Number(config.steady) || 45))
  const step = Math.min(35, Math.max(5, Number(config.step) || 18))
  const noiseSigma = Math.min(6, Math.max(1, Number(config.noise) || 3))
  const anomalyCount = Math.min(30, Math.max(0, Math.round(Number(config.anomalies) || 0)))
  const rowCount = 2_394
  const steadyRows = Math.round(rowCount * steady / 100)
  const dynamicRows = Math.max(1, rowCount - steadyRows)
  const seed = 7_000_000 + steady * 100_000 + step * 1_000 + noiseSigma * 100 + anomalyCount
  const random = seededRandom(seed)
  const anomalyIndexes = new Map()
  const refluxSeries = []
  const productSeries = []
  const tray6Series = []
  const rows = []
  const lag = 52

  for (let i = 0; i < anomalyCount; i += 1) {
    const index = Math.floor((i + 1) * rowCount / (anomalyCount + 1))
    anomalyIndexes.set(index, i % 4)
  }

  for (let i = 0; i < rowCount; i += 1) {
    const progress = Math.max(0, i - steadyRows) / dynamicRows
    const phase = i < steadyRows ? -1 : Math.min(2, Math.floor(progress * 3))
    const stepFactor = phase < 0 ? 0 : [-1, 0.75, -0.4][phase]
    const noiseFactor = noiseSigma / 3
    let reflux = 82 + stepFactor * step * 0.52 + Math.sin(i / 85) * 4.8 + noise(random, 0.45 * noiseFactor)
    let product = 112 - stepFactor * step * 0.40 + Math.sin(i / 110 + 0.7) * 6.2 + noise(random, 0.55 * noiseFactor)
    let pressure = 620 + stepFactor * step * 2.1 + Math.sin(i / 140 + 0.3) * 24 + noise(random, 2.2 * noiseFactor)
    let topTemp = 54 + 0.018 * pressure - 0.026 * reflux + noise(random, 0.12 * noiseFactor)
    let tray6 = 75 + 0.085 * product - 0.031 * reflux + noise(random, 0.16 * noiseFactor)
    let bottomA = 102 + 0.048 * product + 0.010 * pressure + noise(random, 0.18 * noiseFactor)
    let bottomB = bottomA + Math.sin(i / 70) * 1.2 + noise(random, 0.12 * noiseFactor)

    refluxSeries.push(reflux)
    productSeries.push(product)
    tray6Series.push(tray6)
    const lagIndex = Math.max(0, i - lag)
    const trayLagIndex = Math.max(0, i - lag + 8)
    let c4 = 1.18
      - 0.0105 * (refluxSeries[lagIndex] - 82)
      + 0.0072 * (productSeries[lagIndex] - 112)
      + 0.018 * (tray6Series[trayLagIndex] - 84)
      + 0.10 * Math.sin(i / 180)
      + noise(random, 0.018 * noiseFactor)

    const anomalyType = anomalyIndexes.get(i)
    if (anomalyType === 0) topTemp += 40
    if (anomalyType === 1) pressure += 450
    if (anomalyType === 2) reflux *= 0.25
    if (anomalyType === 3) c4 += 5.5

    rows.push([
      formatMinuteTimestamp(i), round(topTemp), round(pressure), round(reflux), round(product),
      round(tray6), round(bottomA), round(bottomB), round(c4),
    ])
  }

  const csv = [debutanizerHeaders, ...rows].map((row) => row.map(csvCell).join(',')).join('\n')
  const configLabel = `S${steady}_P${step}_N${noiseSigma}_A${anomalyCount}`
  return {
    csv: `\ufeff${csv}`,
    name: `sim-DEB-APC-2026-01_${configLabel}.csv`,
    rowCount,
    variableCount: debutanizerHeaders.length - 1,
    period: '39.9 h · 1 min 采样 · 52 min C4滞后',
    summary: `脱丁烷塔 7输入+C4输出 · 52分钟滞后 · 异常 ${anomalyCount} 点`,
  }
}

// 工业干燥器仿真数据仅用于接口验收；真实投运需接入带授权和仪表溯源信息的现场数据。
export function buildIndustrialDryerSimulationCsv(config = {}) {
  const step = Math.min(35, Math.max(5, Number(config.step) || 18))
  const noiseSigma = Math.min(6, Math.max(1, Number(config.noise) || 3))
  const anomalyCount = Math.min(30, Math.max(0, Math.round(Number(config.anomalies) || 0)))
  const headers = ['采集时间', '入口热风温度', '热风流量', '给料量', '产品水分', '物料出口温度', '尾气湿度']
  const rowCount = 867
  const random = seededRandom(8_670_000 + step * 1_000 + noiseSigma * 100 + anomalyCount)
  const anomalies = new Set(Array.from({ length: anomalyCount }, (_, i) => Math.floor((i + 1) * rowCount / (anomalyCount + 1))))
  const rows = []
  let moisture = 8.6
  let productTemp = 62
  let exhaustHumidity = 37
  for (let i = 0; i < rowCount; i += 1) {
    const phase = Math.floor(i / 145) % 3
    const excitation = [0, step / 100, -step / 140][phase]
    const hotAirTemp = 145 * (1 + excitation) + Math.sin(i / 42) * 2 + noise(random, .5 * noiseSigma)
    const airFlow = 8600 * (1 + excitation * .65) + Math.sin(i / 35) * 110 + noise(random, 24 * noiseSigma)
    const feedRate = 4.8 * (1 - excitation * .35) + Math.sin(i / 58) * .15 + noise(random, .025 * noiseSigma)
    moisture += ((9.1 - .025 * (hotAirTemp - 140) - .00009 * (airFlow - 8500) + .42 * (feedRate - 4.8)) - moisture) / 18 + noise(random, .015 * noiseSigma)
    productTemp += ((60 + .34 * (hotAirTemp - 140) - .38 * (feedRate - 4.8)) - productTemp) / 14 + noise(random, .025 * noiseSigma)
    exhaustHumidity += ((36 - .0011 * (airFlow - 8500) + 2.1 * (feedRate - 4.8)) - exhaustHumidity) / 22 + noise(random, .04 * noiseSigma)
    if (anomalies.has(i)) moisture += 2.8
    const date = new Date(Date.UTC(2026, 6, 1, 0, 0, i * 10))
    rows.push([date.toISOString().replace('T', ' ').slice(0, 19), round(hotAirTemp), round(airFlow), round(feedRate), round(moisture), round(productTemp), round(exhaustHumidity)])
  }
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\n')
  return {
    csv: `\ufeff${csv}`,
    name: `sim_DRYER-MIMO_P${step}_N${noiseSigma}_A${anomalyCount}.csv`,
    rowCount,
    variableCount: headers.length - 1,
    period: '144.5 min · 10 s 采样',
    summary: `工业干燥器 3输入3输出 · 激励 ${step}% · 异常 ${anomalyCount} 点`,
  }
}

export function buildSimulationCsv(project = {}, config = {}) {
  const scenario = project.scenarioId ?? ''
  if (scenario === 'debutanizer_column' || /脱丁烷|debutanizer|C4/i.test(`${project.name ?? ''} ${project.scene ?? ''}`)) {
    return buildDebutanizerSimulationCsv(config)
  }
  if (scenario === 'industrial_dryer' || /干燥|dryer/i.test(`${project.name ?? ''} ${project.scene ?? ''}`)) {
    return buildIndustrialDryerSimulationCsv(config)
  }
  return buildBlastFurnaceSimulationCsv(config)
}
