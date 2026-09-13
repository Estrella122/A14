---
name: signal-noise-ratio-estimator
description: Estimate a documented SNR proxy for industrial time windows without claiming instrument-calibrated noise power.
business_skill_id: signal_noise_ratio_estimator
executor: segmentation
capability: estimate_signal_noise_ratio
---

# Signal-to-noise ratio estimator

Use cleaned training windows and the documented robust second-difference proxy. Return signal power, noise power, SNR, sample count, and estimator assumptions. Constant or insufficient series are unavailable, not perfect-SNR observations.
