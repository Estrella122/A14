# Skill Resolution implementation report

## Implemented flow

`plan_skills()` now performs Task Understanding, builds a `DataContext` from the supplied `run_id` pipeline snapshot, recalls candidates through routing/lexical signals, evaluates real preconditions, scores candidates, resolves capabilities once, loads only the resolved Skill resources, and passes the same resolution to `build_analysis_plan()`.

## Unified truth and responsibilities

- `core/skills/routing.py` remains the action boundary, question/negation protection, and recall layer.
- `core/skills/capability_resolver.py` is the only final capability resolver. It owns task understanding, evidence flags, preconditions, scoring, and explainable traces.
- `core/skills/skill_loader.py` performs discovery and explicit resource loading; it no longer makes substring decisions.
- `core/skills/industrial-analysis/scripts/build_analysis_plan.py` consumes resolution and context and emits selected, skipped, blocked, documentation, and trace sections.

`TaskUnderstanding` is represented as a compatibility dictionary with `task_kind`, `semantic_intents`, `requested_outputs`, `execution_requested`, `negations`, `constraints`, and `explicit_capabilities`. Knowledge questions are classified as `knowledge_explanation`, load reference documents only, and never create an execution plan.

`DataContext` in `core/skills/context.py` separates `project_context_scene` from `detected_scene` and includes confidence/status, standardized fields, semantic types, mapping confidence, numeric/sample/time-axis evidence, quality, equipment/process context, and available artifacts. `run_id` is now resolved to its pipeline snapshot before planning.

Scoring uses semantic intent, context fit, data preconditions, scene fit, dependency readiness, and a low-weight lexical recall term. Every candidate exposes all six scores, final score, preconditions, status, selection, selected Skill IDs, and a human-readable reason. Missing numeric fields, time axis, samples, unknown scene, or low mapping confidence block/defer capabilities instead of bypassing requirements.

Scenario support is discovered dynamically from Registry templates; fixed three-scenario assumptions were removed.

## Validation

All tests pass: **129 tests, 1 skipped**.

The five abnormal-behavior paraphrases resolve to a stable core of `DATA_PROFILING`, `DATA_QUALITY_ANALYSIS`, `TREND_ANALYSIS`, and `ANOMALY_DETECTION` when valid ordered numeric data is present. Optional time-series/stability capabilities are selected only when their intent and preconditions score sufficiently.

The knowledge cases `异常检测是什么意思？`, `介绍一下趋势分析`, and `相关性和因果有什么区别` resolve as `knowledge_explanation`; they select no execution capabilities and do not start a pipeline.

## Real pipeline snapshot trace

Using run `20260912_120655_05cef490`, the planner observed:

- project context scene: `debutanizer_column`
- detected scene: `thermal_power_boiler_long_tail`
- scene status/confidence: `confirmed` / `0.948`
- standardized fields: 31 (30 numeric), mapping confidence `0.99`
- samples: `86400`; ordered/regular time axis: true/true
- data quality: `90.49`; artifacts available: standardization, cleaning, modeling, reports, and CSV outputs

For `帮我找异常`, the selected capabilities were:

| capability | final score | preconditions | status |
|---|---:|---|---|
| ANOMALY_DETECTION | 0.992 | readable, numeric, sufficient samples, ordered/timestamp | selected |
| DATA_PROFILING | 0.972 | readable | selected |
| DATA_QUALITY_ANALYSIS | 0.972 | readable | selected |
| TREND_ANALYSIS | 0.972 | numeric + ordered/timestamp | selected |

The trace confirms that the project scene did not overwrite the detected boiler scene, and that the resolver used snapshot evidence and Registry artifacts.

## Modified files

`core/skills/context.py`, `core/skills/capability_resolver.py`, `core/skills/runtime.py`, `core/skills/routing.py` integration points, `core/skills/skill_loader.py`, `core/skills/catalog.py`, `core/skills/industrial-analysis/scripts/build_analysis_plan.py`, `core/services/agent_chat.py`, `core/agent_api.py`, `core/test_skill_routing.py`, `core/test_skill_loader.py`, `core/test_skill_refactor.py`, `core/test_multi_scenario.py`, and `core/tests.py`.

Remaining risk: routing still exposes legacy-compatible recall field names for API compatibility; final selection is ignored by runtime and is performed only by `capability_resolver.py`.
