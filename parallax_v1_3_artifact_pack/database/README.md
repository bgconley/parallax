# Database README

Parallax uses PostgreSQL as the source of truth.

## Migration order

Apply baseline migrations by feature phase, not by blindly requiring every optional
profile in numeric order:

1. `0001_extensions_and_enums.sql`
2. `0002_identity_privacy_audit.sql`
3. `0003_activity_identity.sql`
4. `0004_timing_core.sql`
5. `0005_context_extraction_preflight.sql`
6. `0006_reviews_predictions_evidence.sql`
7. `0007_retrieval_pgvector.sql` when implementing retrieval; baseline FTS works without pgvector
8. `0008_jobs_sync_model_audit.sql`
9. `0011_capture_context_geospatial_sensor_fusion.sql` when implementing v1.3 context phases
10. `0014_timing_review_flags.sql` when implementing context/anomaly review prompts
11. `0015_firebase_external_identity.sql` when enabling Firebase Auth private-alpha identity
12. Dev only: `9999_seed_dev_data.sql`

Core timing and review features require migrations 0001–0006 and 0008.
Context-aware v1.3 features require 0011 after the core timing/event tables are
available, then 0014 for persisted review prompts. Firebase-backed private-alpha
auth requires 0015 for durable external identity mapping, invite/provisioning
metadata, and deleted-identity tombstones. Retrieval/Ask can begin with native PostgreSQL FTS in 0007; the
pgvector embedding tables self-skip unless the `vector` extension is available
and can be enabled. pgvector, TimescaleDB, ParadeDB, PostGIS, and the Timescale
capture-context profile are optional profiles and must not be required for the
first vertical slice.

Optional extension profiles live under `database/optional_profiles/` and are not
part of the baseline migration namespace:

- `0009_timescale_optional_analytics_profile.sql`
- `0010_paradedb_optional_search_profile.sql`
- `0012_postgis_optional_geospatial_profile.sql`
- `0013_timescale_capture_context_profile.sql`

## Extension posture

Required baseline:

- `pgcrypto`
- `citext`

Retrieval phase:

- `vector` / pgvector, if embedding retrieval is enabled. Migration 0007 keeps
  baseline FTS usable when pgvector is unavailable.

Optional profiles:

- `timescaledb` for analytics shadow tables and continuous aggregates.
- `pg_search` / ParadeDB for BM25 and richer lexical search.

Timescale profile caveat: `0009` and `0013` are prototype profile scripts and
must be live-tested against the selected Timescale/Tiger image before enabling.
They use exact `percentile_cont ... WITHIN GROUP` expressions in continuous
aggregates; if the target image rejects or performs poorly with those, use
Timescale Toolkit approximate percentile aggregates for the continuous aggregate
path and keep exact percentiles in ordinary batch SQL.

## Source-of-truth rule

The source-of-truth temporal tables are ordinary relational tables. Optional TimescaleDB analytics tables are projections. Do not move timing correctness into optional extension-only structures.

## Rollback

Rollback notes are in `database/rollback/README.md`. For private alpha and later, prefer forward-compatible compensating migrations over destructive rollback unless restoring from backup.

## v1.3 context/geospatial migrations

- `0011_capture_context_geospatial_sensor_fusion.sql` adds capture context snapshots, user places, geospatial observations, radio observations, device context observations, inferred place observations, and temporal feature vectors.
- `0014_timing_review_flags.sql` adds durable review flags for possible forgotten timers, context-quality issues, and anomaly prompts.
- `0015_firebase_external_identity.sql` adds Firebase external identity mapping,
  alpha invite metadata, and deleted identity tombstones for private-alpha auth.
- `optional_profiles/0012_postgis_optional_geospatial_profile.sql` is optional. It adds PostGIS geography columns and GiST indexes for place/radius queries.
- `optional_profiles/0013_timescale_capture_context_profile.sql` is optional. It adds TimescaleDB shadow metric tables for high-volume context analytics.

Core timing correctness does not require PostGIS or TimescaleDB. The baseline implementation should support manual place selection and numeric latitude/longitude storage without optional extensions.

Implement the baseline migration runner so it only reads `database/migrations/`
unless optional profiles are explicitly enabled. Do not force optional extensions
into the baseline database image just to satisfy numeric ordering.
