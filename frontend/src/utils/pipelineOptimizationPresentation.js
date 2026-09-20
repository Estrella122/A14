// Present persisted pipeline policy; never inherit standalone demo constraints.
export function pipelineConstraintChecks(candidate, constraints = {}) {
  const checks = {}
  if (Number.isFinite(constraints.min_r2)) checks.fit = { actual: candidate.r2, target: constraints.min_r2, passed: candidate.r2 >= constraints.min_r2 }
  if (Number.isFinite(constraints.min_coverage)) checks.coverage = { actual: candidate.coverage, target: constraints.min_coverage, passed: candidate.coverage >= constraints.min_coverage }
  return checks
}
