---
name: high-snr-dynamic-segment-extractor
description: Extract reproducible high-SNR dynamic windows from the frozen training partition for industrial system identification.
business_skill_id: high_snr_dynamic_segment_extractor
executor: high_snr_dynamic_segment_extractor
capability: extract_high_snr_segments
---

# High-SNR dynamic segment extractor

Use only cleaned training data, its frozen split manifest, and the field dictionary. Detect candidate windows, calculate the documented robust second-difference SNR proxy, score dynamics, and persist selected segments and modeling rows. Do not read validation or test values during selection. Report overlap, window policy, selected-row identifiers, estimator assumptions, and upstream hashes.
