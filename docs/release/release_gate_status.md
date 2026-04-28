# Release Gate Status

release readiness: ready

This document tracks the machine-visible Parallax release/private-alpha gates.
The canonical v1.3 API surface is now exposed by runtime routes; later product
depth still follows the phased implementation plan, but no canonical endpoint is
silently absent at the API boundary.

## Verified Gates

| Gate | Status | Evidence |
| --- | --- | --- |
| `backup_restore` | passed | `scripts/release_backup_restore_drill.py` verifies migration-state restore, PostgreSQL logical dump viability, and object-path copy/restore checks on the target runtime. |
| `privacy_export_delete_redact` | passed | `/v1/privacy/settings`, `/v1/privacy/export`, `/v1/privacy/redact`, and `/v1/privacy/delete` are implemented with mutation envelopes and workflow audit records. |
| `performance_slo` | passed | `scripts/release_slo_smoke.py` exercises health, readiness, activity, timing, context, and extraction hot paths with p95 reporting. |
| `production_auth_provider` | passed | `external_bearer` supports issuer/audience-bound JWKS verification for RS256/ES256 and keeps development header auth disabled outside development/test. |
| `production_log_privacy_scan` | passed | `scripts/release_log_privacy_scan.py` proves representative sensitive payloads do not appear in structured errors or normal app logs. |
| `deployed_commit_parity` | passed | `scripts/verify_gpu_commit_parity.sh` checks `/tank/repos/parallax` against the audited Git SHA before GPU runtime evidence is accepted. |

## Required Release Proof Commands

Before release handoff, run these from the exact commit being released:

```bash
make release-gate
scripts/verify_gpu_commit_parity.sh
uv run python scripts/release_slo_smoke.py --api-url "$PARALLAX_API_URL"
uv run python scripts/release_log_privacy_scan.py --api-url "$PARALLAX_API_URL"
uv run python scripts/release_backup_restore_drill.py --database-url "$PARALLAX_HOST_DATABASE_URL" --object-root /srv/parallax/objects
```
