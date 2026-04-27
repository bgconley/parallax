# Migrations

Baseline migrations are copied from the v1.3 artifact pack and applied in feature-phase order. The baseline runner reads only this directory and intentionally excludes `parallax_v1_3_artifact_pack/database/optional_profiles/`.

For the first temporal core path, apply:

1. `0001_extensions_and_enums.sql`
2. `0002_identity_privacy_audit.sql`
3. `0003_activity_identity.sql`
4. `0004_timing_core.sql`
5. `0005_context_extraction_preflight.sql`
6. `0006_reviews_predictions_evidence.sql`
7. `0008_jobs_sync_model_audit.sql`
