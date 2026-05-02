# 23 — Agentic Implementation Guardrails

This document makes implicit handoff contracts explicit for an implementation agent.
It does not add product scope; it narrows choices so the first implementation stays
coherent.

## First implementation target

Build an API-first vertical slice before mobile background capture, Ask About Time,
model serving, PostGIS, ParadeDB, or TimescaleDB hardening.

The first working slice is:

1. baseline repository skeleton and local runtime;
2. PostgreSQL migrations from `database/migrations/` through the phase being built;
3. FastAPI health/version/auth stub;
4. activity create/list/get/resolve;
5. timing session create/event append/complete/get;
6. review/save decision and basic stats projection;
7. duplicate/offline replay contract tests;
8. a minimal client or UI proof that one user can time, finish, review, and inspect one run.

## Identity and auth

- `user_id` is inferred from auth context. Do not accept a client-supplied `user_id`
  on normal user-scoped endpoints.
- A private-alpha auth stub is acceptable for P0 if every query and mutation is
  still user-scoped and testable.
- Service/admin overrides must be internal, explicit, audited, and absent from the
  mobile/public client surface.

## Mutation and resolver rules

- Every mutating endpoint requires `MutationEnvelope`.
- `POST /v1/activities/resolve`, `POST /v1/places/resolve`,
  `POST /v1/activities/{activity_id}/merge-preview`, and
  `POST /v1/activities/{activity_id}/split-preview` are read-only POST
  exceptions. They must not create aliases, places, identity changes, events,
  jobs, or domain audit rows.
- `POST /v1/sync/push` has a top-level batch mutation envelope. Each mutating
  operation inside the batch keeps its endpoint-level mutation envelope.
- Duplicate mutation replay returns the original result and must not create a
  second source event, review flag, place, or job.
- Out-of-order timing/context payloads are persisted and reconciled; they are not
  dropped merely because related rows arrive later.

## Database and migrations

- The baseline runner reads `database/migrations/` only.
- `database/optional_profiles/` is opt-in SQL for extension-specific profiles and
  must not be applied during the first vertical slice unless the user explicitly
  asks for that profile.
- Source-of-truth timing tables stay relational PostgreSQL tables. TimescaleDB
  profiles are projections; PostGIS profiles are indexes/geometry helpers.
- `0007_retrieval_pgvector.sql` must preserve its native PostgreSQL FTS fallback
  when `vector` is unavailable.
- Use a real migration tool such as Alembic once the implementation repo exists;
  preserve the artifact migration order and names in the generated migration history.

## Context capture

- `context_capture_policy` is the backend authority for optional location, radio,
  motion, and device context capture and retention.
- OS permission state is necessary but not sufficient. If server policy disables a
  signal, the client must not collect or upload that signal.
- Timing must work with all sensor permissions denied.
- Context snapshots and observations are auxiliary evidence. They can prompt review
  or derived feature recomputation, but they do not silently rewrite timing events,
  spans, session totals, or activity baselines.
- `capture_context_snapshot_ref` is an offline/pending client reference only;
  resolve it to `capture_context_snapshot_id` when the snapshot row exists.

## Places and review flags

- `POST /v1/places/resolve` is read-only matching.
- `POST /v1/places` creates or confirms a user place and requires a mutation envelope.
- `PATCH /v1/places/{place_id}` edits or confirms an existing user place and requires
  a mutation envelope.
- `timing_review_flag` rows are prompts with evidence. Resolving or dismissing a
  flag must not mutate source timing facts.
- User review or correction is the only path from a review flag to changed derived
  totals or model inclusion.

## API and contract implementation

- OpenAPI is the canonical API shape. JSON Schema and Pydantic models must stay in
  sync with OpenAPI when implementation code generates or hand-writes models.
- `contracts/pydantic/parallax_contracts_v1_3.py` is scaffolding, not an independent
  source of truth. Do not build server behavior from it alone; regenerate or patch
  it from OpenAPI/JSON Schema before using it as implementation code.
- Endpoint responses may use a common envelope internally, but the concrete data
  shape must satisfy `contracts/openapi/parallax_api_v1_3.yaml`.
- Do not add undocumented endpoints, enum values, request fields, or response
  fields without updating contracts and adding an ADR.
- Raw notes, transcripts, prompts, raw coordinates, raw radio identifiers, and
  sensitive model inputs must not appear in normal logs or structured errors.

## Async workflows

- API request threads validate, persist, and enqueue. Heavy extraction, profile
  recomputation, feature-vector generation, and forgotten-timer detection run in
  Temporal workflows or equivalent durable jobs.
- Workflow retries must be idempotent.
- Workflow failure must preserve source timing facts and leave the user with a
  recoverable pending/review state.

## UI and UX guardrails

- The first screen should support the actual timing workflow, not a marketing page.
- Use product language from the design docs: run, detour, say what happened, useful
  run, place changed. Avoid exposing raw sensor jargon in normal UI.
- Permission prompts are feature-scoped and progressive. Never request every mobile
  permission at first launch.
- Place/context prompts should be sparse and actionable; prompt false positives are
  a product quality risk.

## Infrastructure guardrails

- Docker Compose is the first runtime target.
- k3s, extension profiles, model-serving hardening, and richer search profiles are
  later-phase work.
- Prototype Compose files may document flexible images, but implementation branches
  intended for private alpha must pin tested service image versions before release.
- MinIO or S3-compatible object storage is only for raw audio, exports, attachments,
  model artifacts, and eval artifacts; it is not a timing source of truth.

## Verification before handoff

Before claiming a phase complete, run:

- contract parse/validation checks;
- database migration application in a clean local database for the phase;
- user-scope authorization tests;
- mutation replay/idempotency tests;
- timing semantics tests for active/wall/friction separation;
- privacy log-scrub tests;
- any phase-specific evals in `tests_or_eval/`.
