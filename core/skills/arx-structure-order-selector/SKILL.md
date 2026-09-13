---
name: arx-structure-order-selector
description: Select ARX structure, order, delay, and regularization candidates on a common frozen validation target.
business_skill_id: arx_structure_order_selector
executor: modeling
capability: select_arx_structure_order
---

# ARX structure and order selector

Fit candidates on training data and compare them on identical validation targets. Persist every candidate, AIC/BIC or validation criteria, parameter count, failures, and tie-break policy. The final test partition is excluded from structure selection.
