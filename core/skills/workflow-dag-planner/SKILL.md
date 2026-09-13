---
name: workflow-dag-planner
description: Build the minimal acyclic execution DAG from Skill contracts and currently available artifacts.
business_skill_id: workflow_dag_planner
executor: planning
capability: build_execution_dag
---

# Workflow DAG planner

Use typed requires/produces contracts to add only necessary producers. Mark direct, dependency, governance, and shared-stage nodes distinctly. Block unproducible inputs before execution and never add optimization, reporting, or retraining unless requested or contractually required.
