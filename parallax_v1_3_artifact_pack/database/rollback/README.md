# Rollback Notes

Parallax should prefer forward-compatible compensating migrations after real user data exists.

## Pre-alpha

For local/prototype development, destructive rollback is acceptable if no real user data exists.

## Private alpha and later

- Do not drop raw context tables without export/delete review.
- Do not remove enum values without compatibility migration.
- Do not roll back a migration that has produced user-visible derived data unless a compensating migration or restore plan exists.
- For irreversible migrations, mark them irreversible and require backup restore for rollback.

## Optional extensions

Optional TimescaleDB, ParadeDB, and PostGIS profiles live under
`database/optional_profiles/` and should be disabled via feature flags before
attempting rollback. Their projection tables/indexes can be dropped without
deleting source truth.
