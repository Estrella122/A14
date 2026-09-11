const headers = [
  '采集时间',
  'GAS_FLOW_NM3H',
  '助燃风量[Nm3/h]',
  'ZONE1_TEMP_C',
  '二段炉温(℃)',
  '均热段温度(°F)',
  'WALKING_BEAM_SPEED',
  '入炉温度',
  'SLAB_OUT_TEMP_C',
  '炉压(kPa)',
  'O2_PERCENT',
  '板坯厚度',
  'THROUGHPUT',
]

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

function formatTimestamp(index) {
  const date = new Date(Date.UTC(2026, 6, 1, 0, 0, index))
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`
}

function csvCell(value) {
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function buildFurnaceSimulationCsv(config = {}) {
  const steady = Math.min(75, Math.max(20, Number(config.steady) || 45))
  const step = Math.min(35, Math.max(5, Number(config.step) || 18))
  const noiseSigma = Math.min(6, Math.max(1, Number(config.noise) || 3))
  const anomalyCount = Math.min(30, Math.max(0, Math.round(Number(config.anomalies) || 0)))
  const rowCount = 21_600
  const steadyRows = Math.round(rowCount * steady / 100)
  const dynamicRows = Math.max(1, rowCount - steadyRows)
  const seed = steady * 100_000 + step * 1_000 + noiseSigma * 100 + anomalyCount
  const random = seededRandom(seed)
  const anomalyIndexes = new Map()

  for (let i = 0; i < anomalyCount; i += 1) {
    const index = Math.floor((i + 1) * rowCount / (anomalyCount + 1))
    anomalyIndexes.set(index, i % 4)
  }

  let zone1 = 930
  let zone2 = 1115
  let zone3 = 1230
  let discharge = 1160
  const rows = []
  const stepPattern = [-1, 0.7, -0.35]

  for (let i = 0; i < rowCount; i += 1) {
    const dynamicProgress = Math.max(0, i - steadyRows) / dynamicRows
    const phase = i < steadyRows ? -1 : Math.min(2, Math.floor(dynamicProgress * 3))
    const stepFactor = phase < 0 ? 0 : stepPattern[phase]
    const slowDrift = Math.sin(i / 1_800)
    const noiseFactor = noiseSigma / 3
    let gas = 24_200 * (1 + stepFactor * step / 100) + slowDrift * 180 + noise(random, 85 * noiseFactor)
    let air = 43_600 + stepFactor * step / 100 * 15_000 + Math.sin(i / 1_250) * 380 + noise(random, 260 * noiseFactor)
    let speed = 1.2 - stepFactor * 0.12 + Math.sin(i / 2_300) * 0.025 + noise(random, 0.009 * noiseFactor)
    const entry = 170 + Math.sin(i / 2_000) * 7 + noise(random, 1.2 * noiseFactor)
    const thickness = [180, 200, 220, 250][Math.floor(i / 5_400) % 4]
    const zone1Target = 755 + gas * 0.0072 - speed * 8
    const zone2Target = 992 + gas * 0.0052 - speed * 4
    const zone3Target = 1110 + gas * 0.005 - speed * 2
    zone1 += (zone1Target - zone1) / 260 + noise(random, 0.11 * noiseFactor)
    zone2 += (zone2Target - zone2) / 420 + noise(random, 0.09 * noiseFactor)
    zone3 += (zone3Target - zone3) / 620 + noise(random, 0.07 * noiseFactor)
    const dischargeTarget = 0.16 * zone1 + 0.31 * zone2 + 0.53 * zone3 + 10 - speed * 5
    discharge += (dischargeTarget - discharge) / 780 + noise(random, 0.04 * noiseFactor)
    let pressure = 0.006 + (air / Math.max(gas, 1) - 1.8) * 0.004 + noise(random, 0.00065 * noiseFactor)
    let oxygen = 3.1 + (air / Math.max(gas, 1) - 1.8) * 3.2 + noise(random, 0.055 * noiseFactor)
    const production = 162 + speed * 9 - thickness * 0.025 + noise(random, 1.5 * noiseFactor)

    const anomalyType = anomalyIndexes.get(i)
    if (anomalyType === 0) zone1 += 230
    if (anomalyType === 1) pressure += 0.09
    if (anomalyType === 2) oxygen = 18.6
    if (anomalyType === 3) gas *= 0.22

    rows.push([
      formatTimestamp(i), round(gas), round(air), round(zone1), round(zone2), round(zone3 * 9 / 5 + 32),
      round(speed, 4), round(entry), round(discharge), round(pressure, 5), round(oxygen), thickness, round(production),
    ])

    if (anomalyType === 0) zone1 -= 230
  }

  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\n')
  const configLabel = `S${steady}_P${step}_N${noiseSigma}_A${anomalyCount}`
  return {
    csv: `\ufeff${csv}`,
    name: `sim_FUR-APC-2026-02_${configLabel}.csv`,
    rowCount,
    variableCount: headers.length - 1,
    period: '6 h · 1 s 采样',
    summary: `稳态 ${steady}% · 阶跃 ${step}% · 噪声 ${noiseSigma}σ · 异常 ${anomalyCount} 点`,
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

export function buildSimulationCsv(project = {}, config = {}) {
  if (project.id === 'debutanizer-c4' || /脱丁烷|debutanizer|C4/i.test(`${project.name ?? ''} ${project.scene ?? ''}`)) {
    return buildDebutanizerSimulationCsv(config)
  }
  return buildFurnaceSimulationCsv(config)
}
