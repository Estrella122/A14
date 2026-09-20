import test from 'node:test'
import assert from 'node:assert/strict'
import {pipelineConstraintChecks} from '../src/utils/pipelineOptimizationPresentation.js'
test('pipeline UI uses actual 8% coverage and zero R2 gates, no standalone 70% gate',()=>{
 const pass=pipelineConstraintChecks({r2:.99,coverage:.2292},{min_r2:0,min_coverage:.08})
 assert.equal(pass.fit.passed,true);assert.equal(pass.coverage.passed,true);assert.deepEqual(Object.keys(pass),['fit','coverage'])
 assert.equal(pipelineConstraintChecks({r2:.9,coverage:.0347},{min_r2:0,min_coverage:.08}).coverage.passed,false)
 assert.deepEqual(pipelineConstraintChecks({r2:.9,coverage:.9}),{})
})
