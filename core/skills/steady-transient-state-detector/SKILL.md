---
name: steady-transient-state-detector
description: Detect steady, transitional, and dynamic operating windows in cleaned training data.
business_skill_id: steady_transient_state_detector
executor: segmentation
capability: detect_operating_states
---

# Steady and transient state detector

Operate only on the frozen training partition. Record window size, step, features, thresholds, overlaps, and state labels. Treat detected states as statistical operating regimes unless validated plant-state labels are provided.
