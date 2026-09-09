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
