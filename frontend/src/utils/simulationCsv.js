const headers = ['dt', 'Fb', 'Ph', 'Pc', 'Tc', 'Fo', 'dP', 'dPu', 'dPl', 'Pt', 'Th', 'CO2', 'H2', 'Tt1', 'Tt2', 'Tt3', 'Tt4', 'R', 'Si']

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
  const date = new Date(Date.UTC(2013, 0, 1, index))
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:00:00`
}

function csvCell(value) {
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

// TODO(mock): 该生成器只用于压力测试；答辩主流程应使用项目内置的 Mendeley 高炉真实数据CSV。
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
  for (let i = 0; i < anomalyCount; i += 1) anomalyIndexes.set(Math.floor((i + 1) * rowCount / (anomalyCount + 1)), i % 4)

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

    const anomaly = anomalyIndexes.get(i)
    if (anomaly === 0) blast *= .35
    if (anomaly === 1) oxygen *= 1.8
    if (anomaly === 2) pressureDrop += 1.1
    if (anomaly === 3) silicon += .35

    rows.push([
      formatTimestamp(i), round(blast, 2), round(hotPressure, 3), round(coldPressure, 3), round(coldTemp, 2),
      round(oxygen, 2), round(pressureDrop, 3), round(upperDrop, 3), round(lowerDrop, 3), round(topPressure, 3),
      round(hotBlast, 2), round(co2, 3), round(h2, 3), round(topBase + noise(random, 4), 2),
      round(topBase - 9 + noise(random, 4), 2), round(topBase + 6 + noise(random, 4), 2),
      round(topBase - 13 + noise(random, 4), 2), round(oreCoke, 3), round(silicon, 4),
    ])
  }

  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\n')
  const configLabel = `S${steady}_P${step}_N${noiseSigma}_A${anomalyCount}`
  return {
    csv: `\ufeff${csv}`,
    name: `sim_BF-SI_${configLabel}.csv`,
    rowCount,
    variableCount: headers.length - 1,
    period: '90 d · 1 h 采样',
    summary: `高炉仿真压力测试 · 稳态 ${steady}% · 激励 ${step}% · 噪声 ${noiseSigma}σ · 异常 ${anomalyCount} 点`,
  }
}

export const buildFurnaceSimulationCsv = buildBlastFurnaceSimulationCsv
