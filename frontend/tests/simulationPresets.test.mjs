import test from 'node:test'
import assert from 'node:assert/strict'
import { buildCausalBlastFurnace, buildPresetDataset, DEMO_DEFAULTS, LEGACY_DEFAULTS, isVerifiedConfiguration } from '../src/utils/simulationPresets.js'
import { buildSimulationCsv } from '../src/utils/simulationCsv.js'
const project = { scenarioId: 'blast_furnace' }
test('causal data is reproducible, seed changes observations, and provenance binds exact bytes', async () => {
  const a = await buildPresetDataset(project, 'full_demo', DEMO_DEFAULTS)
  const b = await buildPresetDataset(project, 'full_demo', DEMO_DEFAULTS)
  assert.equal(a.csv, b.csv); assert.equal(a.manifest.file_hash, b.manifest.file_hash)
  assert.notEqual(a.csv, buildCausalBlastFurnace({ ...DEMO_DEFAULTS, seed: 7 }).csv)
  assert.equal(a.manifest.source_type, 'SYNTHETIC'); assert.match(a.name, /^SYNTHETIC_/)
  assert.deepEqual(a.csv.slice(1).split('\n')[0].split(','), ['dt','Fb','Fo','Th','R','Si'])
  assert.equal(a.csv.split('\n').length, DEMO_DEFAULTS.rows + 1)
  assert.equal(a.manifest.sampling_interval.value, 3600)
  assert.equal(Object.keys(a.manifest.units).length,6)
  const training = a.reference.excitation_events.filter(e => e.start_row < DEMO_DEFAULTS.rows * .6)
  assert.equal(new Set(training.map(e=>e.channel)).size, 4)
  assert.ok(training.some(e=>e.normalized_level>0) && training.some(e=>e.normalized_level<0))
  assert.equal(new Set(training.slice(0,4).map(e=>e.start_row)).size,4)
  assert.ok(!a.csv.includes('clean_target') && !a.csv.includes('injections'))
})
test('measurement corruption does not enter process state; explicit zero stays zero', async () => {
  const p = { ...DEMO_DEFAULTS, noise:0, processNoise:0, anomalies:0, targetSpikes:0, processShocks:0, step:0 }
  const clean = buildCausalBlastFurnace(p)
  const spikes = buildCausalBlastFurnace({...p, anomalies:3, targetSpikes:2})
  assert.deepEqual(clean.reference.clean_target, spikes.reference.clean_target)
  assert.notEqual(clean.csv, spikes.csv)
  assert.equal(clean.parameters.noise,0); assert.equal(clean.parameters.anomalies,0); assert.equal(clean.parameters.step,0)
  assert.notDeepEqual(clean.reference.clean_target,buildCausalBlastFurnace({...p,processShocks:2}).reference.clean_target)
  const custom = await buildPresetDataset(project,'full_demo',{...DEMO_DEFAULTS,noise:0})
  assert.equal(custom.mode,'custom'); assert.equal(custom.manifest.verified_default,false)
  assert.equal(isVerifiedConfiguration('industrial_dryer','full_demo',DEMO_DEFAULTS),false)
})
test('legacy pressure output is preserved for all scenes and never inherits demo badge', async () => {
  for (const scenarioId of ['blast_furnace','debutanizer_column','industrial_dryer']) {
    const p = {scenarioId}; const old = buildSimulationCsv(p,LEGACY_DEFAULTS)
    const now = await buildPresetDataset(p,'challenge',LEGACY_DEFAULTS,'legacy_pressure_v1')
    assert.equal(now.csv,old.csv); assert.equal(now.manifest.verified_default,false)
    assert.ok(Number.isFinite(now.manifest.explicit_seed))
  }
  await assert.rejects(buildPresetDataset({scenarioId:'industrial_dryer'},'full_demo',DEMO_DEFAULTS))
})
