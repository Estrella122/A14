---
name: csv-asset-manager
description: Validate and register uploaded industrial CSV assets with stable hashes and provenance.
business_skill_id: csv_asset_manager
executor: asset
capability: register_csv_asset
---

# CSV asset manager

Validate readability, size, encoding, shape, and basic schema before registration. Preserve the original file, compute a content hash, and return a typed source-data reference. Asset registration does not imply field semantics or authorize analysis.
