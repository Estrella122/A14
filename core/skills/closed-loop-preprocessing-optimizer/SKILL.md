---
name: closed-loop-preprocessing-optimizer
description: Optimize preprocessing and model-selection settings on real frozen training and validation data under explicit bounds and constraints.
business_skill_id: closed_loop_preprocessing_optimizer
executor: closed_loop_preprocessing_optimizer
capability: optimize_preprocessing_closed_loop
---

# Closed-loop preprocessing optimizer

Require real training, validation and test partitions, selected segments, a field dictionary, an initial model, and explicit objective, bounds, constraints, search space, and policy. Search and stop using validation evidence only; freeze the winner before exactly one test evaluation. Never synthesize missing inputs or fall back to benchmark data. Persist every candidate, feasibility decision, stopping reason, winner, and provenance.
