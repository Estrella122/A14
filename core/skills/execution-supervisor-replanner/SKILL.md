---
name: execution-supervisor-replanner
description: Inspect failed or blocked Skill executions and propose a bounded retry or revised DAG when explicitly requested.
business_skill_id: execution_supervisor_replanner
executor: supervision
capability: inspect_and_replan
---

# Execution supervisor and replanner

Classify the failed node, missing artifacts, unmet contracts, and retry safety. Retry only idempotent or explicitly authorized work, cap attempts, and preserve previous evidence. Never convert missing real data into synthetic fallback.
