# Release Gate Status

release readiness: blocked

This document describes the Parallax release/private-alpha gates. The
machine-readable gate state lives in `docs/release/release_gate_evidence.json`;
`make release-status` reads that evidence file and treats missing, stale, or
evidence-free passed gates as blocked. `make release-gate` records a structured
proof artifact for each gate under `.release-gate-proofs/` before it writes the
final evidence JSON; the writer refuses to mark release readiness ready when any
gate proof is missing, stale, malformed, or for another commit.
Each compact evidence reference includes the proof artifact SHA-256, and
`release-status` blocks if the referenced proof file is missing, has changed, is
malformed, names a different gate, or names a different commit.
By default, release proof files are resolved under the repository root at
`.release-gate-proofs/`, even when the status scripts are launched from another
working directory.
The canonical v1.3 API surface is now exposed by runtime routes; later product
depth still follows the phased implementation plan, but no canonical endpoint is
silently absent at the API boundary.

## Gate Requirements

| Gate | Status | Evidence |
| --- | --- | --- |
| `backup_restore` | proof-required | `scripts/release_backup_restore_drill.py` restores the logical PostgreSQL dump into a throwaway database and restores object bytes into a separate restore namespace. |
| `privacy_export_delete_redact` | proof-required | `scripts/privacy_lifecycle_smoke.py` proves export/delete/redact enqueue durable workflows and worker completion mutates or reports source and derived lifecycle scope. |
| `performance_slo` | proof-required | `scripts/release_slo_smoke.py` exercises health, readiness, activity, timing, context, and extraction hot paths with p95 reporting. |
| `production_auth_provider` | proof-required | `scripts/release_auth_provider_probe.py` requires a real Firebase ID token, or mints one from release Firebase credentials, and proves authenticated runtime access. |
| `production_log_privacy_scan` | proof-required | `scripts/release_log_privacy_scan.py` proves representative sensitive payloads do not appear in structured errors or normal app logs. |
| `deployed_commit_parity` | proof-required | `scripts/verify_gpu_commit_parity.sh` checks `/tank/repos/parallax` against the audited Git SHA before GPU runtime evidence is accepted. |

## Required Release Proof Commands

Before release handoff, run these from the exact commit being released:

```bash
make release-snapshot-deployment
RELEASE_DEPLOYMENT_SNAPSHOT=/home/bgconley/parallax-release-parity-snapshots/<snapshot> make release-promote-deployment-check
make release-preflight
make release-gate
uv run python scripts/release_gate_status.py --summary
```

`make release-snapshot-deployment` is a non-mutating preservation step for the
GPU deployment checkout. It records the current HEAD, status, tracked diff, and
a sanitized archive of untracked files while excluding `.env`, JWTs, keys,
tokens, PEM files, and `secrets/` directories from the archive.

`make release-promote-deployment-check` is a dry-run guard for deployment parity.
It verifies that the named snapshot still matches the current dirty deployment
checkout, including tracked patch contents and sanitized untracked evidence, and
that the target release commit is available before any operator runs the
underlying promotion script with `--apply`. It refuses promotion when secret-like
untracked files would not be preserved by the sanitized snapshot.

`make release-preflight` is a read-only prerequisite check. It reports missing
release secrets by environment variable name only, checks the deployed GPU
checkout parity, and exits non-zero while release-gate prerequisites are missing.
When `RELEASE_DEPLOYMENT_SNAPSHOT` points at a locally accessible snapshot,
preflight also runs the same deployment promotion dry-run guard used by
`make release-promote-deployment-check`; when the checkout or snapshot path is not
local, preflight reports that the promotion dry-run was skipped instead of
claiming preservation was checked. Pass `--skip-gpu` to `scripts/release_preflight.py`
only for local environment diagnostics that intentionally skip both deployed
commit parity and deployment promotion dry-run checks. The Make target forwards
operator arguments through `RELEASE_PREFLIGHT_ARGS`, for example
`PARALLAX_RELEASE_BEARER_TOKEN=<token> make release-preflight RELEASE_PREFLIGHT_ARGS=--skip-gpu`
for a local auth/env-only diagnostic.

`make release-gate` is intentionally proof-based. It fails if GPU commit parity,
the live bearer-auth provider probe, privacy lifecycle smoke, SLO smoke, privacy
log scan, or real backup/restore drill cannot be executed successfully for the
current release candidate. Each proof command must emit a sanitized, structured
proof artifact for the current commit. A ready release must also publish a
commit-matched evidence JSON artifact with non-empty, hash-matched evidence for
every gate. The backup/restore drill writes temporary restored object bytes under
`${PARALLAX_RESTORE_DRILL_ROOT:-/srv/parallax/exports/release-restore-drill}`;
`/srv/parallax/backups` remains restricted local backup staging, not the writable
restore-drill scratch root.

For Firebase auth mode, the release auth provider probe accepts a fresh token in
`PARALLAX_RELEASE_BEARER_TOKEN`. If that is absent, it mints a short-lived token
using `PARALLAX_FIREBASE_WEB_API_KEY`, `PARALLAX_RELEASE_FIREBASE_EMAIL`, and
`PARALLAX_RELEASE_FIREBASE_PASSWORD`. Those values must come from secret
storage. The probe never writes ID tokens, refresh tokens, App Check tokens,
service-account JSON, raw Firebase UID, or raw email to release evidence. When
App Check enforce mode is configured, pass a fresh production App Check token in
`PARALLAX_RELEASE_APP_CHECK_TOKEN`; debug-provider App Check tokens are allowed
only in non-production Firebase projects.
