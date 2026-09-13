---
name: final-artifact-exporter
description: Export and index existing registered artifacts without regenerating missing analysis results.
business_skill_id: final_artifact_exporter
executor: artifact
capability: export_existing_artifacts
---

# Final artifact exporter

Verify artifact existence, type, hash, run ownership, and safe download name. Export only requested existing artifacts and report missing items. Download requests never authorize report writing, model training, or pipeline reruns.
