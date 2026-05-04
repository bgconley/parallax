# Parallax Database Implementation Artifacts

Baseline migrations live in `migrations/` and remain the only migrations applied
by the default migration runner.

Optional extension profiles live in `database/optional_profiles/` and are enabled
only by explicit Phase 9 validation or deployment choice:

- `0009_timescale_optional_analytics_profile.sql`
- `0010_paradedb_optional_search_profile.sql`
- `0012_postgis_optional_geospatial_profile.sql`
- `0013_timescale_capture_context_profile.sql`

These profiles must not become source-of-truth timing storage. Timescale tables
are projections, PostGIS adds geography/index helpers, and ParadeDB/pgvector add
retrieval acceleration after the baseline PostgreSQL path is already proven.
