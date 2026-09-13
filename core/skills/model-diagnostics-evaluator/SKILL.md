---
name: model-diagnostics-evaluator
description: Evaluate a persisted industrial model's metrics, stability, residual, and baseline evidence without silently retraining it.
business_skill_id: model_diagnostics_evaluator
executor: model_diagnostics_evaluator
capability: evaluate_model_diagnostics
---

# Model diagnostics evaluator

Read a persisted model artifact and its metrics. Evaluate finite test metrics, AR-pole stability, persistence-baseline improvement, residual evidence, and final-test policy, then write a separate diagnostic assessment. Missing evidence produces `blocked` or `partial`; it must never cause implicit retraining or fabricate a pass.
