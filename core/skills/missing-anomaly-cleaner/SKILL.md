---
name: missing-anomaly-cleaner
description: Clean missing values and statistical anomalies in standardized industrial time series when the user explicitly requests data mutation.
business_skill_id: missing_anomaly_cleaner
executor: missing_anomaly_cleaner
capability: clean_missing_and_anomalies
---

# Missing and anomaly cleaner

Require standardized data and a field dictionary. Preserve chronological train/validation/test boundaries: input variables may use bounded forward fill inside a partition; controlled or quality outputs with missing or anomalous observations remain missing. Never use future partitions to fill earlier data. Return changed-row counts, rules, typed partition artifacts, limitations, and provenance. Statistical anomalies are not equipment-failure diagnoses.
