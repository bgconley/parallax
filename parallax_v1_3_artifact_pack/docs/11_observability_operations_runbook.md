# 11 — Observability, Operations, and Runbooks

## Operational principle

Parallax should be observable across product behavior, timing correctness, AI behavior, and infrastructure health. It is not enough for the API to be up; source events must be flowing, workflows must be draining, model outputs must validate, and backups must be restorable.

## Health checks

### API health

`GET /v1/health` should report:

- API process status;
- database connectivity;
- Redis connectivity;
- Temporal client connectivity;
- object storage connectivity if configured;
- build/version metadata.

### Readiness

A service is ready only when it can safely accept traffic. The API can be live but not ready if migrations are pending or database connectivity is unavailable.

### Liveness

A service is live if the process event loop is healthy. Liveness should not depend on downstream services or it can cause restart storms.

## Core dashboards

### API dashboard

Metrics:

- request rate by route;
- p50/p95 latency;
- error rate by status and route;
- mutation duplicate replay rate;
- auth failures;
- cross-user scope test failures in CI.

### Temporal workflow dashboard

Metrics:

- workflow starts/completions/failures;
- retry counts;
- backlog by workflow type;
- activity latency;
- stuck workflows.

### Timing correctness dashboard

Metrics:

- event append latency;
- out-of-order event rate;
- impossible sequence rate;
- review completion rate;
- correction rate;
- sessions completed_unreviewed for more than 24 hours.

### AI/model dashboard

Metrics:

- model invocation count by role;
- schema validity rate;
- repair count;
- low-confidence output rate;
- sensitive flag rate;
- user correction rate after extraction;
- prompt/schema version distribution.

### Backup dashboard

Metrics:

- last successful database backup;
- last successful object backup;
- WAL/archive lag;
- last restore test date;
- encrypted backup verification status.

## Runbook — API unhealthy

1. Check container status.
2. Check database connection string and credentials.
3. Check migration state.
4. Check Redis if rate limiting/cache is required.
5. Check recent deploy logs.
6. Roll back to previous image if migration is not involved.
7. If migration is involved, follow migration rollback plan.

## Runbook — event append failures

1. Confirm API health.
2. Check idempotency log uniqueness errors.
3. Check timing_event enum mismatch.
4. Check client mutation envelope validity.
5. Check database disk space.
6. Confirm client retry behavior does not generate new mutation IDs for retries.

## Runbook — extraction backlog

1. Check Temporal worker health.
2. Check AI orchestrator availability.
3. Check model endpoint health.
4. Check schema validation failures.
5. Disable extraction workflow feature flag if backlog threatens core timing.
6. Keep annotation capture enabled.

## Runbook — query answers untrusted

1. Check query grounding evals.
2. Inspect evidence bundle construction.
3. Verify model prompt receives computed facts only.
4. Disable narrator and return deterministic facts if needed.
5. Record incident and update eval cases.

## Runbook — privacy deletion

1. Validate requester identity.
2. Create deletion workflow.
3. Delete or tombstone raw annotations, transcripts, audio objects, retrieval documents, embeddings, and query answers as requested.
4. Preserve minimal audit/tombstone only where necessary.
5. Record backup-retention implication.
6. Confirm completion to user.

## Incident severity

- SEV1: cross-user data exposure, raw context leak, destructive data loss, auth bypass.
- SEV2: timing event loss, backup failure, model endpoint public exposure, workflow backlog blocking product use.
- SEV3: delayed extraction, query narrator disabled, optional search profile unavailable.
- SEV4: UI copy bug, non-critical dashboard issue.

## Operational acceptance before private alpha

- Database backup tested.
- Object storage backup tested.
- Restore tested.
- API and worker dashboards exist.
- Raw context log scan passes.
- Model endpoints confirmed internal-only.
- Feature flags can disable extraction/narration without disabling timing.


## v1.3 context observability

Add metrics and alerts for context capture without exposing sensitive payload values.

Metrics:

- context snapshots accepted/rejected by source device and capture method;
- observations by type and permission state;
- place inference candidate count and confirmation rate;
- false-positive context review prompt rate;
- persisted `timing_review_flag` creation/update counts;
- feature vector recomputation count;
- redaction/delete jobs affecting context tables;
- sensor permission-denied rate;
- snapshot staleness distribution.

Never log raw coordinates, SSIDs, BSSIDs, beacon IDs, or sensitive place labels.
