# Release Gate Status

release readiness: blocked

This document describes the Parallax release/private-alpha gates. The
machine-readable gate state lives in `docs/release/release_gate_evidence.json`;
`make release-status` reads that evidence file and treats missing, stale, or
evidence-free passed gates as blocked.
The canonical v1.3 API surface is now exposed by runtime routes; later product
depth still follows the phased implementation plan, but no canonical endpoint is
silently absent at the API boundary.

## Gate Requirements

| Gate | Status | Evidence |
| --- | --- | --- |
| `backup_restore` | proof-required | `scripts/release_backup_restore_drill.py` restores the logical PostgreSQL dump into a throwaway database and restores object bytes into a separate restore namespace. |
| `privacy_export_delete_redact` | proof-required | `scripts/privacy_lifecycle_smoke.py` proves export/delete/redact enqueue durable workflows and worker completion mutates or reports source and derived lifecycle scope. |
| `performance_slo` | proof-required | `scripts/release_slo_smoke.py` exercises health, readiness, activity, timing, context, and extraction hot paths with p95 reporting. |
| `production_auth_provider` | proof-required | `scripts/release_auth_provider_probe.py` requires a real bearer token from the configured provider and proves authenticated runtime access. |
| `production_log_privacy_scan` | proof-required | `scripts/release_log_privacy_scan.py` proves representative sensitive payloads do not appear in structured errors or normal app logs. |
| `deployed_commit_parity` | proof-required | `scripts/verify_gpu_commit_parity.sh` checks `/tank/repos/parallax` against the audited Git SHA before GPU runtime evidence is accepted. |

## Required Release Proof Commands

Before release handoff, run these from the exact commit being released:

```bash
make release-gate
uv run python scripts/release_gate_status.py --summary
```

`make release-gate` is intentionally proof-based. It fails if GPU commit parity,
the live bearer-auth provider probe, privacy lifecycle smoke, SLO smoke, privacy
log scan, or real backup/restore drill cannot be executed successfully for the
current release candidate. A ready release must also publish a commit-matched
evidence JSON artifact with non-empty evidence for every gate.
