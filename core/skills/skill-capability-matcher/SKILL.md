---
name: skill-capability-matcher
description: Match resolved industrial intent to registered business Skills with calibrated rejection and negation handling.
business_skill_id: skill_capability_matcher
executor: routing
capability: match_skill_capabilities
---

# Skill capability matcher

Select direct business targets separately from dependencies and governance Skills. Retain routing scores and rejection reasons. Reject unknown requests and denied actions; never count automatically added dependencies as evidence that the user requested them.
