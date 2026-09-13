---
name: system-identification-trainer
description: Train a reproducible industrial system-identification model from frozen modeling, validation, and test partitions.
business_skill_id: system_identification_trainer
executor: system_identification_trainer
capability: train_system_identification_model
---

# System-identification trainer

Require a modeling dataset, field dictionary, frozen split, and validation/test partitions. Select structure on the common validation target, fit only with training data, freeze the winning model, and touch the final test once. Persist coefficients, selected inputs, delays, split hashes, model metrics, and diagnostics. Do not start closed-loop optimization unless it is separately requested.
