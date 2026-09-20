import { buildSimulationCsv } from './simulationCsv.js'

export const GENERATOR_VERSION = 'causal-process-v3'
export const DEMO_VERSION = 'blast-furnace-demo-v3'
// Set only after the frozen default and both verification seeds pass acceptance.
export const DEMO_VERIFIED = false
export const DEMO_DEFAULTS = Object.freeze({ seed: 20260921, rows: 1440, step: 18, noise: 0.004, processNoise: 0.0008, anomalies: 4, targetSpikes: 0, processShocks: 0, targetEvery: 1 })
export const LEGACY_DEFAULTS = Object.freeze({ steady: 45, step: 18, noise: 3, anomalies: 12 })
export const CHALLENGES = Object.freeze({
  high_noise: { ...DEMO_DEFAULTS, noise: 0.06, targetSpikes: 5 },
  sparse_target: { ...DEMO_DEFAULTS, targetEvery: 48 },
  low_excitation: { ...DEMO_DEFAULTS, step: 0 },
  process_shock: { ...DEMO_DEFAULTS, processShocks: 4 },
})
export function isVerifiedConfiguration(scenario, mode, parameters) {
  return DEMO_VERIFIED && scenario === 'blast_furnace' && mode === 'full_demo' && Object.entries(DEMO_DEFAULTS).every(([k, v]) => Number(parameters[k]) === v)
}
function random(seed) {
  let state = seed >>> 0
  return () => { state = (1664525 * state + 1013904223) >>> 0; return state / 4294967296 }
}
function bounded(value, fallback, min, max, integer = false) {
  const n = value == null || value === '' ? fallback : Number(value)
  if (!Number.isFinite(n) || n < min || n > max || (integer && !Number.isInteger(n))) throw new Error(`生成参数必须在 ${min}–${max} 范围内`)
  return n
}
export function generationParameters(config = {}) {
  return {
    seed: bounded(config.seed, DEMO_DEFAULTS.seed, 0, 4294967295, true), rows: bounded(config.rows, 1440, 150, 10000, true),
    step: bounded(config.step, 18, 0, 35), noise: bounded(config.noise, 0.004, 0, 0.2),
    processNoise: bounded(config.processNoise, 0.0008, 0, 0.1), anomalies: bounded(config.anomalies, 4, 0, 30, true),
    targetSpikes: bounded(config.targetSpikes, 0, 0, 30, true), processShocks: bounded(config.processShocks, 0, 0, 30, true),
    targetEvery: bounded(config.targetEvery, 1, 1, 100, true),
  }
}
export function buildCausalBlastFurnace(config = {}) {
  const p = generationParameters(config)
  const excitation = [1, 2, 3, 4].map(i => random(p.seed + 7919 * i))
  const processRandom = random(p.seed + 50021), observationRandom = random(p.seed + 60013)
  const white = r => (r() + r() + r() + r() - 2)
  const holds = [35, 43, 51, 59], offsets = [8, 15, 22, 29], delays = [2, 3, 4, 5]
  const gains = [0.018, -0.06, 0.04, 0.05], levels = [0, 0, 0, 0], states = [0, 0, 0, 0]
  const inputs = [], cleanTarget = [], events = [], injections = [], rows = []
  const indices = count => new Set(Array.from({ length: count }, (_, i) => Math.floor((i + 1) * p.rows / (count + 1))))
  const sensorSpikes = indices(p.anomalies), targetSpikes = indices(p.targetSpikes), shocks = indices(p.processShocks)
  const headers = ['dt', 'Fb', 'Fo', 'Th', 'R', 'Si']
  let state = 0.5
  for (let t = 0; t < p.rows; t++) {
    for (let j = 0; j < 4; j++) {
      if (t >= offsets[j] && (t - offsets[j]) % holds[j] === 0) {
        // Independently timed signed changes, with occasional true steady holds.
        levels[j] = (Math.floor(excitation[j]() * 5) - 2) / 2 * p.step / 18
        events.push({ channel: headers[j + 1], start_row: t, hold_samples: holds[j], normalized_level: levels[j] })
      }
      states[j] += 0.45 * (levels[j] - states[j])
    }
    inputs.push([...states])
    let equilibrium = 0.5
    for (let j = 0; j < 4; j++) equilibrium += gains[j] * inputs[Math.max(0, t - delays[j])][j]
    state = 0.6 * state + 0.4 * equilibrium + white(processRandom) * p.processNoise
    if (shocks.has(t)) { state += 0.08; injections.push({ row: t, channel: 'Si', type: 'process_shock', magnitude: 0.08 }) }
    cleanTarget.push(state)
    const values = [3500 + 360 * states[0], 19000 + 2200 * states[1], 1120 + 50 * states[2], 3.9 + 0.2 * states[3], state]
    const scales = [2200, 14000, 350, 1.2, 1]
    for (let j = 0; j < 5; j++) values[j] += white(observationRandom) * p.noise * scales[j]
    if (sensorSpikes.has(t)) { const j = injections.filter(x => x.type === 'input_sensor_spike').length % 4; values[j] += [900, 7000, 180, 0.65][j]; injections.push({ row: t, channel: headers[j + 1], type: 'input_sensor_spike' }) }
    if (targetSpikes.has(t)) { values[4] += 0.3; injections.push({ row: t, channel: 'Si', type: 'target_measurement_spike', magnitude: 0.3 }) }
    if (t % p.targetEvery !== 0) values[4] = null
    const timestamp = new Date(Date.UTC(2026, 0, 1, t)).toISOString().replace('T', ' ').slice(0, 19)
    rows.push([timestamp, ...values.map((v, j) => v == null ? '' : Number(v.toFixed(j === 4 ? 6 : 4)))])
  }
  const csv = '\ufeff' + [headers, ...rows].map(r => r.join(',')).join('\n')
  const fieldRules = {
    dt: { unit: 'datetime', role: 'time', position: 0, rule: 'UTC origin 2026-01-01, hourly observations' },
    Fb: { unit: 'm3/min', role: 'manipulated', position: 1, rule: '3500 + 360*u0; independent actuator, observation noise and optional local sensor spikes' },
    Fo: { unit: 'm3/h', role: 'manipulated', position: 2, rule: '19000 + 2200*u1; independent oxygen actuator' },
    Th: { unit: 'degC', role: 'manipulated', position: 3, rule: '1120 + 50*u2; independent hot blast temperature actuator' },
    R: { unit: 'ratio', role: 'manipulated', position: 4, rule: '3.9 + 0.2*u3; independent ore/coke actuator' },
    Si: { unit: 'percent', role: 'controlled', position: 5, rule: 'stable first-order causal state plus separate observation noise; challenge corruption never feeds back into state' },
  }
  return { csv, rowCount: p.rows, variableCount: 5, period: `${p.rows} h · 1 h 采样`, parameters: p, fieldRules,
    reference: { clean_target: cleanTarget, target_unit: 'percent', injections, excitation_events: events,
      process: { state_pole: 0.6, delays_samples: delays, gains, actuator_pole: 0.55, hold_samples: holds },
      use: 'Independent acceptance only; never send to pipeline, model features or LLM context' } }
}
export async function buildPresetDataset(project, mode, config, challenge = 'high_noise') {
  const scenario = project.scenarioId
  const supported = scenario === 'blast_furnace'
  if (mode === 'full_demo' && !supported) throw new Error('当前场景尚未验证完整流程演示，请使用挑战测试或自定义。')
  const legacy = !supported || challenge === 'legacy_pressure_v1'
  const generated = legacy ? buildSimulationCsv(project, config) : buildCausalBlastFurnace(config)
  const parameters = generated.parameters ?? {
    steady: Math.min(75, Math.max(20, Number(config.steady) || 45)),
    step: Math.min(35, Math.max(5, Number(config.step) || 18)),
    noise: Math.min(6, Math.max(1, Number(config.noise) || 3)),
    anomalies: Math.min(30, Math.max(0, Math.round(Number(config.anomalies) || 0))),
  }
  const legacySeed = scenario === 'industrial_dryer' ? 8670000 + parameters.step * 1000 + parameters.noise * 100 + parameters.anomalies
    : (scenario === 'debutanizer_column' ? 7000000 : 0) + parameters.steady * 100000 + parameters.step * 1000 + parameters.noise * 100 + parameters.anomalies
  const effectiveMode = mode === 'full_demo' && !Object.entries(DEMO_DEFAULTS).every(([k, v]) => Number(parameters[k]) === v) ? 'custom' : mode
  const id = legacy ? 'legacy_pressure_v1' : effectiveMode === 'full_demo' ? 'blast_furnace_full_demo' : effectiveMode === 'challenge' ? challenge : 'custom'
  const bytes = new TextEncoder().encode(generated.csv)
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('')
  const version = legacy ? 'legacy_pressure_v1' : GENERATOR_VERSION
  const manifest = { preset_id: id, preset_version: legacy ? '1' : DEMO_VERSION, scenario_id: scenario, source_type: 'SYNTHETIC', generator_version: version,
    explicit_seed: legacy ? legacySeed : parameters.seed, effective_generation_parameters: parameters, rows: generated.rowCount, sampling_interval: { value: scenario === 'industrial_dryer' ? 10 : scenario === 'debutanizer_column' ? 60 : 3600, unit: 's' },
    units: generated.fieldRules ?? { source: 'existing scenario fields.csv; legacy generator column mapping' },
    process_assumptions: legacy ? 'Legacy pressure test; target spikes may persist through recursive state, sigma is an arbitrary scale, not calibrated sensor uncertainty.' : 'Known low-order stable synthetic mechanism. Independent actuators; process disturbance changes state, observation noise/spikes do not. Not factory validation or independent algorithm superiority evidence.',
    anomaly_design: legacy ? 'Legacy mixed-channel pressure anomalies' : 'Default: four local input-sensor spikes; nonzero process and measurement noise; no target spike. Challenges explicitly configure target spikes, process shocks or sparse targets.',
    file_hash: hash, hash_algorithm: 'sha256', verified_default: isVerifiedConfiguration(scenario, effectiveMode, parameters), mode: effectiveMode }
  const name = legacy ? `SYNTHETIC_${generated.name}` : `SYNTHETIC_${scenario}_${id}_${DEMO_VERSION}_seed${parameters.seed}.csv`
  return { ...generated, name, manifest, mode: effectiveMode, summary: `${scenario} · SYNTHETIC 合成数据 · ${id} · ${version}`, reference: generated.reference ?? { use: 'Legacy generator does not expose clean reference; legacy output retained unchanged.' } }
}
