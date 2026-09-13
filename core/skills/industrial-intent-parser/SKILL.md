---
name: industrial-intent-parser
description: Resolve an industrial request into analysis, execution, explanation, or delivery intent without authorizing unstated mutations.
business_skill_id: industrial_intent_parser
executor: task_understanding
capability: parse_industrial_intent
---

# Industrial intent parser

Separate questions, hypothetical language, quotations, negations, and explicit commands. Preserve every positive and negative clause, summarize the objective, and emit an execution mode. Ambiguity must request clarification; it must not default to running a pipeline.
