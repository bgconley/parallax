# Migrations

Baseline migrations are copied from the v1.3 artifact pack and applied in feature-phase order. The baseline runner reads only this directory and intentionally excludes `parallax_v1_3_artifact_pack/database/optional_profiles/`.

Current baseline order:

1. `0001_extensions_and_enums.sql`
2. `0002_identity_privacy_audit.sql`
3. `0003_activity_identity.sql`
4. `0004_timing_core.sql`
5. `0005_context_extraction_preflight.sql`
6. `0006_reviews_predictions_evidence.sql`
7. `0007_retrieval_pgvector.sql`
8. `0008_jobs_sync_model_audit.sql`
9. `0011_capture_context_geospatial_sensor_fusion.sql`
10. `0014_timing_review_flags.sql`
11. `0015_firebase_external_identity.sql`
12. `0016_activity_identity_preflight_decisions.sql`
13. `0017_resource_dependency_event_idempotency.sql`

`scripts/apply_migrations.py --smoke` runs the current implementation schema
smoke, not only the original Phase 0 checks. The current smoke covers Phase 0
core tables/enums, Phase 2 profile tables, Phase 3 context capture tables/enums,
Phase 4 extraction, correction, model-invocation, and preflight tables/enums,
Phase 5 checkpoint/latency/feature-vector tables, and Firebase external identity
mapping tables. Phase 6 adds activity identity decision records, soft-merge
auditability, idempotent resource dependency aggregation, and preflight lifecycle
decisions. Phase 7 adds baseline retrieval documents for grounded Ask About Time.
