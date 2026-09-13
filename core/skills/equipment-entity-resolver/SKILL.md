---
name: equipment-entity-resolver
description: Resolve supported industrial equipment and scene identities from a request while preserving unknown-scene uncertainty.
business_skill_id: equipment_entity_resolver
executor: task_understanding
capability: resolve_equipment_entity
---

# Equipment entity resolver

Resolve equipment number, supported scene ID, and scene family using the project registry. Do not infer equipment from a measurement name alone. If request context and uploaded-data evidence disagree, expose the mismatch instead of silently overriding either source.
