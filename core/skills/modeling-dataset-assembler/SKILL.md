---
name: modeling-dataset-assembler
description: Assemble reproducible modeling rows from selected training windows without validation or test leakage.
business_skill_id: modeling_dataset_assembler
executor: modeling
capability: assemble_modeling_dataset
---

# Modeling dataset assembler

Join selected training windows, remove duplicate row IDs deterministically, and retain split and upstream hashes. Validate required inputs and controlled outputs. Validation and test rows must never enter the assembled training artifact.
