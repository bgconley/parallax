# Release Gate Status

release readiness: blocked

This document tracks release/private-alpha gates that are outside the current
Phase 0-4 implementation scope. No Phase 5 endpoint or workflow is implemented by this gate; it only prevents the current phase-scoped runtime from being
mistaken for a releasable full v1.3 system.

## Blocked Gates

| Gate | Status | Minimum Evidence Required |
| --- | --- | --- |
| `backup_restore` | blocked | Database backup, object backup, and restore drill pass on the GPU node. |
| `privacy_export_delete_redact` | blocked | Canonical privacy export, delete, and redact endpoints are implemented and verified. |
| `performance_slo` | blocked | API timing/profile/context hot paths meet documented p95 targets on the GPU node. |
| `production_auth_provider` | blocked | Production/private-alpha auth provider is selected, configured, and verified. |
| `production_log_privacy_scan` | blocked | Representative sensitive payloads do not appear in normal application logs. |
| `phase5_plus_workflows` | blocked | Later-phase Temporal/model workflows are implemented only after their phases start. |

## Current Non-Release Scope

The implemented runtime is valid only as the documented Phase 0-4 subset. The
canonical OpenAPI remains the target contract for later phases, but unstarted
Phase 5+ endpoints must remain unavailable until explicitly implemented.
