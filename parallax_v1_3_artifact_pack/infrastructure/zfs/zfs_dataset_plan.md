# ZFS Dataset Plan

Use the `parallax` namespace for all datasets.

| Dataset | Mountpoint | Purpose | Snapshot cadence | Notes |
|---|---|---|---|---|
| `pool/parallax/postgres` | `/srv/parallax/postgres` | PostgreSQL data | frequent | database-aware backups still required |
| `pool/parallax/postgres_wal` | `/srv/parallax/postgres_wal` | WAL/archive | frequent | keep on reliable storage |
| `pool/parallax/objects` | `/srv/parallax/objects` | MinIO/object data | hourly/daily | raw audio/export artifacts may live here |
| `pool/parallax/exports` | `/srv/parallax/exports` | user export staging | daily | encrypted and lifecycle-managed |
| `pool/parallax/models` | `/srv/parallax/models` | model weights | daily/weekly | can be large; not all need remote backup |
| `pool/parallax/hf_cache` | `/srv/parallax/hf_cache` | model cache | optional | disposable cache |
| `pool/parallax/logs` | `/srv/parallax/logs` | service logs | daily | raw context must not be logged |
| `pool/parallax/backups` | `/srv/parallax/backups` | local backup staging | daily | encrypt before offsite |
| `pool/parallax/observability` | `/srv/parallax/observability` | metrics/traces | daily | retention by policy |
| `pool/parallax/config` | `/srv/parallax/config` | non-secret config | daily | secrets should not live here |

## Backup requirements

ZFS snapshots are useful but not sufficient for PostgreSQL. Use database-aware backup tooling such as pgBackRest, WAL-G, or an equivalent. Test restore before alpha.
