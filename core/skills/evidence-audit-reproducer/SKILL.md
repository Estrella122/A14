---
name: evidence-audit-reproducer
description: Audit and reproduce an industrial Skill run from immutable inputs, parameters, versions, events, and artifact hashes.
business_skill_id: evidence_audit_reproducer
executor: audit
capability: audit_and_reproduce_evidence
---

# Evidence audit and reproducer

Verify input hashes, Skill and Executor versions, parameters, random seeds, event order, and produced artifacts. Report missing or changed evidence explicitly. Reproduction requires separate execution authorization and must not overwrite the audited run.
