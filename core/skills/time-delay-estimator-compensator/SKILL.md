---
name: time-delay-estimator-compensator
description: Estimate nonnegative input-output delays on modeling data and create delay-compensated artifacts without retraining a model.
business_skill_id: time_delay_estimator_compensator
executor: time_delay_estimator_compensator
capability: estimate_and_compensate_delay
---

# Time-delay estimator and compensator

Resolve controlled output and eligible external inputs from the field dictionary. Search only nonnegative lags on contiguous time segments, enforce minimum overlap, record boundary hits, and write both delay estimates and compensated data. A correlation peak is statistical timing evidence, not proof of causality. Never trigger model training from a delay-only request.
