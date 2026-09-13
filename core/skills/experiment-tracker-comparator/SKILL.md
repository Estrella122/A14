---
name: experiment-tracker-comparator
description: Compare registered industrial experiments only when their datasets, splits, targets, and metrics are compatible.
business_skill_id: experiment_tracker_comparator
executor: experiment
capability: compare_registered_experiments
---

# Experiment tracker and comparator

Require registered runs and comparable split/target evidence. Show parameter changes, metric deltas, artifact hashes, and non-comparable reasons. Never rank experiments that used different targets or evaluation populations as if they were equivalent.
