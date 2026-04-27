# 14 — Architectural Decision Records Summary

## ADR-001 — Canonical product name is Parallax

Decision: Use **Parallax** for all product, package, service, schema, Docker, environment, and Figma naming.

Rationale: Eliminates ambiguity and retired-name drift.

Consequences: Earlier placeholders and retired names are not valid in new files.

## ADR-002 — Backend/domain model is canonical; UI is a projection

Decision: Use backend/domain schemas as source truth. UI view models map to domain objects instead of defining competing contracts.

Rationale: Prevents drift between design and implementation.

Consequences: UI state names such as "waiting active" are derived from spans/events, not standalone domain states.

## ADR-003 — `user_id` is the canonical identity field

Decision: Use `user_id` in database, API internals, events, and schemas.

Rationale: Aligns database and backend contracts.

Consequences: `account_id` is not used in domain contracts.

## ADR-004 — Postgres is the system of record

Decision: Use PostgreSQL as the source-of-truth database.

Rationale: Temporal data, relationships, JSONB model metadata, FTS, and vector retrieval can be handled in one operationally mature database.

Consequences: Optional search/analytics profiles must not undermine source truth.

## ADR-005 — pgvector is the baseline vector extension when retrieval begins

Decision: Use pgvector for embedding-backed retrieval in the baseline retrieval phase.

Rationale: Keeps vectors close to source data and user scoping.

Consequences: Separate embedding tables by dimension/profile.

## ADR-006 — ParadeDB is optional, not mandatory

Decision: Treat ParadeDB/`pg_search` as a feature-flagged richer lexical/hybrid search profile.

Rationale: Avoids making early implementation depend on extension compatibility.

Consequences: Native PostgreSQL FTS must work first.

## ADR-007 — TimescaleDB is optional analytics acceleration, not source truth

Decision: Use TimescaleDB only for analytics shadow tables/continuous aggregates if measured pressure justifies it.

Rationale: Timing correctness depends on event semantics and review, not only time-series partitioning.

Consequences: Core timing tables remain portable.

## ADR-008 — LLMs interpret and narrate; they do not own numeric truth

Decision: Numeric facts come from deterministic computation. LLMs produce structured candidates or explanations.

Rationale: Prevents hallucinated estimates and builds user trust.

Consequences: Evidence bundles and schema validation are mandatory.

## ADR-009 — Every mutating endpoint requires an offline mutation envelope

Decision: Every mutation includes client mutation/device/timestamp/idempotency metadata.

Rationale: Offline timing is a core product requirement.

Consequences: API and DB idempotency are P0.

## ADR-010 — Raw context is privacy-sensitive by default

Decision: Raw notes, transcripts, audio, prompts, and embeddings receive explicit privacy controls.

Rationale: User trust and safety.

Consequences: Logs, embeddings, query quotes, and model fallback are privacy-gated.


## ADR-011 — Add capture context snapshots as auxiliary evidence

Decision: Add `capture_context_snapshot` as the root object for geospatial, radio, device, and permission context captured around timing actions.

Rationale: Timing analytics need context to explain variance, detect forgotten timers, and support place-aware estimates. Attaching context directly into every timing event would overfit the event model and make privacy/redaction harder.

Consequences:

- Timing events remain valid without context.
- Context can arrive late and be processed asynchronously.
- Privacy policy can redact context without deleting the timing event.
- Feature vectors can be regenerated from reviewed source data and permitted context.

## ADR-012 — Keep PostGIS and Timescale context analytics optional

Decision: Baseline Parallax uses PostgreSQL relational tables with numeric coordinates and JSONB feature metadata. PostGIS and TimescaleDB profiles are optional.

Rationale: The core app should run in a simple local/dev database. Geospatial indexing and time-series continuous aggregates are valuable but should not be required for the first vertical slice.

Consequences:

- Optional migrations must be compatibility-tested before enabling.
- Optional profile SQL lives in `database/optional_profiles/`, outside the
  baseline migration runner.
- Source-of-truth semantics remain in baseline tables.
- Production can enable PostGIS/Timescale when query volume or geospatial workloads justify it.

## ADR-013 — Resolver POST endpoints are read-only exceptions

Decision: `POST /v1/activities/resolve` and `POST /v1/places/resolve` use request
bodies for richer matching inputs but are read-only operations.

Rationale: Offline idempotency rules remain strict without forcing mutation
envelopes onto non-mutating resolver calls.

Consequences:

- Resolver endpoints must not create aliases, places, events, jobs, or domain audit rows.
- Activity alias creation, place creation, place confirmation, and place updates use
  documented mutation-envelope endpoints.

## ADR-014 — Context capture policy is the backend permission authority

Decision: `context_capture_policy` controls whether optional location, radio,
motion, and device context can be captured or retained.

Rationale: OS permissions are necessary but not sufficient for a privacy-sensitive
personal intelligence app.

Consequences:

- Mobile clients must fetch and enforce the policy before optional capture.
- Policy changes trigger invalidation or recomputation of derived context features.
- Review flags are evidence prompts; they do not alter timing truth without user action.
