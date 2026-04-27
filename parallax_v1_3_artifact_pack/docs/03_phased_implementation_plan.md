# 03 — Phased Implementation Plan

This plan is intentionally executable. Each phase has dependencies, subphases, deliverables, acceptance gates, validation criteria, and non-goals. Do not reorder phases unless an ADR documents the reason.

## Phase 0 — Repository, contracts, and local runtime foundation

### Goal

Create the implementation substrate without product complexity.

### Dependencies

None.

### Subphase 0.1 — Repository initialization

Deliverables:

- Monorepo layout matching `docs/13_repository_layout_coding_standards.md`.
- Root `README.md`, `AGENTS.md`, `.env.example`, `Makefile`, `pyproject.toml`, and package manifests.
- Generated code directories for API schemas and shared types.
- Contract validation task wired into CI.

Acceptance gate:

- A new contributor can clone the repo, copy `.env.example`, and run local validation commands.
- No retired or placeholder product names appear in new files.

### Subphase 0.2 — Local runtime

Deliverables:

- Docker Compose stack for API, Postgres, Redis, Temporal server, Temporal UI, MinIO, Caddy, and optional observability.
- Health check endpoints.
- Basic service-to-service networking.
- Secrets loaded from environment, not hard-coded.

Acceptance gate:

- `make dev-up` starts the stack.
- `GET /v1/health` returns healthy when Postgres and Redis are reachable.
- Model services are not publicly exposed.

### Subphase 0.3 — Database migration tooling

Deliverables:

- Migration runner.
- Migrations through `0006_reviews_predictions_evidence.sql` applied in order.
- Schema smoke tests.
- Rollback documentation.

Acceptance gate:

- Migrations apply to a clean database.
- Core tables and enums exist.
- Optional pgvector, ParadeDB, and Timescale migrations are not required for core loop.

### Phase 0 validation

Run:

- JSON/YAML contract parse checks.
- Migration ordering check.
- API health smoke test.
- Retired-name scan.
- Static type/lint baseline.

## Phase 1 — Core activity and timing session loop

### Goal

A user can create/select an activity, start a whole-task timing session, append source events, complete the run, and retrieve the session.

### Dependencies

Phase 0 complete.

### Subphase 1.1 — Activity API

Deliverables:

- `POST /v1/activities`
- `GET /v1/activities`
- `GET /v1/activities/{activity_id}`
- `POST /v1/activities/resolve`

Acceptance gate:

- Activities are scoped by authenticated user.
- Duplicate canonical keys are handled safely.
- Activity resolution returns explicit confidence and never merges silently.
- `POST /v1/activities/resolve` is read-only; alias creation remains a separate
  mutation-envelope endpoint.

### Subphase 1.2 — Timing session API

Deliverables:

- `POST /v1/timing/sessions`
- `GET /v1/timing/sessions/{session_id}`
- `POST /v1/timing/sessions/{session_id}/events`
- `POST /v1/timing/sessions/{session_id}/complete`

Acceptance gate:

- Session state moves through draft/running/completed_unreviewed.
- Events are append-safe.
- Out-of-order events are accepted and flag recomputation/review when needed.

### Subphase 1.3 — Offline/idempotency contract

Deliverables:

- Mutation envelope validation on every mutating endpoint.
- `client_mutation_log` upsert behavior.
- Duplicate replay returns previous result.
- Client clock drift metadata preserved.
- `POST /v1/sync/push` validates both the top-level batch mutation envelope and
  each operation payload's endpoint-level mutation envelope when present.

Acceptance gate:

- Replaying the same event three times creates one source event.
- Delayed event replay does not double-count active or wall time.
- API tests cover duplicate, out-of-order, and impossible event sequences.

### Phase 1 validation

A scripted test must create an activity, create a session, append start/pause/resume/complete events, fetch the session, and verify wall/active reconstruction.

## Phase 2 — Review, counting semantics, and first Activity Profile facts

### Goal

A completed run can be reviewed, counted, and converted into simple personal ranges.

### Dependencies

Phase 1 complete.

### Subphase 2.1 — Span derivation

Deliverables:

- Timeline reconstruction service.
- Derived `timing_event_span` creation.
- Active/wall/friction calculations.
- Bad-timer and impossible-sequence detection.

Acceptance gate:

- Resource detour excludes active time by default.
- Interruption excludes active baseline by default.
- Forgot-to-stop can mark the run as bad timer/corrupted.

### Subphase 2.2 — Review API

Deliverables:

- `POST /v1/timing/sessions/{session_id}/review`
- `POST /v1/timing/sessions/{session_id}/discard`
- Model update decision persistence.
- Correction/audit rows.

Acceptance gate:

- User can save useful, unusual, partial, active-only, friction-only, evidence-only, or discard decisions.
- Session `model_inclusion` matches review decision.
- Review changes trigger profile recomputation.

### Subphase 2.3 — First stats snapshots

Deliverables:

- `activity_stats_snapshot` computation for reviewed runs.
- p50/p80 active and wall estimates.
- confidence labels by sample size and variance.
- `GET /v1/activities/{activity_id}/profile`.

Acceptance gate:

- Activity Profile returns sample size, confidence, active range, wall range, recent reviewed runs, and limitations.
- LLM is not required.

## Phase 3 — Context annotation capture

### Goal

"Say what happened" works as a first-class, offline-safe source action.

### Dependencies

Phase 1 complete; Phase 2 can run in parallel for basic review integration.

### Subphase 3.1 — Annotation API

Deliverables:

- `POST /v1/timing/sessions/{session_id}/annotations`
- `GET /v1/timing/annotations/{annotation_id}`
- Raw note retention and redaction fields.
- Link to session, checkpoint, timer elapsed, and active elapsed.

Acceptance gate:

- Raw text annotation saves while extraction is unavailable.
- Annotation can be private/sensitive.
- Annotation creates a source event of type `annotation_captured`.

### Subphase 3.2 — Privacy-aware storage

Deliverables:

- Privacy settings enforced for raw text, audio, embeddings, and query quote use.
- Raw note deletion/redaction workflow stub.
- Logs scrub raw context.

Acceptance gate:

- Test proves raw note is not present in normal logs.
- Privacy settings affect retrieval-document creation.


### Subphase 3.3 — Capture context snapshots

Deliverables:

- `capture_context_snapshot` persistence and API support.
- `context_capture_policy` persistence and `GET/PATCH /v1/privacy/context-capture-policy`.
- Context snapshot creation at session start/pause/resume/completion, checkpoint boundaries, annotations, and quick chips.
- Permission-state recording.
- Linkage from `timing_event` and `temporal_context_annotation` to snapshots,
  including offline-safe pending references that resolve after out-of-order replay.
- Offline/idempotent replay for snapshots.

Acceptance gate:

- Timing and annotation capture succeed with no sensor permissions.
- A session start event can attach a context snapshot.
- Missing, denied, stale, or unsupported context is explicitly represented.
- Context snapshots never change duration totals by themselves.
- Backend policy disables capture even when OS permissions are granted.

### Subphase 3.4 — Mobile capture methods and sensor permission gates

Deliverables:

- Capture method enum support for manual button, widget, watch, voice, quick chip, shortcut, NFC tag, calendar import, review reconstruction, and background signal.
- Feature-scoped permission ladder for approximate/precise/background location and nearby/radio context.
- Place resolver remains read-only; user-confirmed place creation uses `POST /v1/places`.
- Per-run "ignore context for this run" behavior.
- Context privacy settings wired to storage policy.
- `0014_timing_review_flags.sql` and the review-flag API are implemented before
  forgotten-timer detection writes prompts.

Acceptance gate:

- User can capture from at least one non-primary surface in prototype or contract tests.
- Permission-denied paths remain productive and non-blocking.
- Raw radio/location context is not stored unless policy allows it.
- Timing review flags can be listed and resolved without mutating source timing
  events or session totals.


## Phase 4 — Structured extraction and event correction

### Goal

Context annotations produce validated, correctable candidate events.

### Dependencies

Phases 2 and 3 complete.

### Subphase 4.1 — AI orchestrator boundary

Deliverables:

- Prompt/schema version registry.
- Model invocation logging with hashes, not raw prompts by default.
- Structured output validation and repair loop.
- Privacy filter before model calls.

Acceptance gate:

- Invalid model output is rejected and does not create durable truth.
- Model unavailable path leaves annotation in safe pending state.

### Subphase 4.2 — Extraction workflow

Deliverables:

- `ProcessContextAnnotationWorkflow`
- `POST /v1/timing/annotations/{annotation_id}/extract`
- Candidate `temporal_extracted_context_event` persistence.
- Confidence tier handling.

Acceptance gate:

- Sponge-detour golden case creates a resource detour candidate with wall-only count policy and suggested preflight check.
- Medium/low confidence events require confirmation or review.

### Subphase 4.3 — Correction API

Deliverables:

- `POST /v1/timing/extracted-events/{event_id}/confirm`
- `POST /v1/timing/extracted-events/{event_id}/correct`
- Split/merge/reclassify support.
- Audit trail.

Acceptance gate:

- Correction changes the derived span and stats after recomputation.
- Original model output remains auditable.


### Subphase 4.4 — Place and context inference workflow

Deliverables:

- `InferPlaceFromContextWorkflow`
- User-scoped place clustering from permitted geospatial/radio observations.
- Inferred place candidate persistence.
- Place confirmation/correction API.
- Review prompts for material place transitions and likely forgotten timers.

Acceptance gate:

- A run can show a human-readable place candidate without storing a sensitive label automatically.
- The user can confirm, rename, ignore, or mark a place private.
- A place transition can flag review but cannot silently trim a timer.
- Place inference works with coarse/manual context and degrades gracefully when sensors are unavailable.


## Phase 5 — Checkpoints, start latency, and transition latency

### Goal

Parallax can model phase-level duration and the hidden time around activities.

### Dependencies

Phases 1–4 complete.

### Subphase 5.1 — Checkpoint templates and runs

Deliverables:

- `GET /v1/activities/{activity_id}/checkpoints`
- `PUT /v1/activities/{activity_id}/checkpoints`
- Checkpoint events and run status handling.
- Checkpoint-level stats.

Acceptance gate:

- A checkpointed run can show which phase expanded.
- Skipped/moved checkpoints do not corrupt sequence.

### Subphase 5.2 — Start latency

Deliverables:

- intended start capture;
- `start_latency_observation` creation;
- Activity Profile start-latency section.

Acceptance gate:

- Start latency is not folded into active duration.
- User can decline start latency capture without nagging.

### Subphase 5.3 — Transition latency

Deliverables:

- transition observation table usage;
- between-session and between-checkpoint transitions;
- queryable transition patterns.

Acceptance gate:

- Transition delays can be explained separately from source/target activity duration.


### Subphase 5.4 — Contextual timing feature vectors

Deliverables:

- `temporal_feature_vector` generation.
- Context-aware feature families for time-of-day, work mode, actor mode, place, motion, capture method, and friction.
- Privacy-filtered feature eligibility rules.
- Evaluation fixtures for context-conditioned estimates.

Acceptance gate:

- Feature vectors are generated only from permitted, reviewed, or otherwise eligible source data.
- Disabling location/radio context invalidates or regenerates affected features.
- Activity Profile can compute a context-conditioned summary when sample thresholds are met.
- Low-sample contexts fall back to broader activity stats.


## Phase 6 — Activity identity and preflight learning

### Goal

Reduce fragmented histories and turn repeated friction into useful preflight checks.

### Dependencies

Phases 2–5 complete.

### Subphase 6.1 — Alias and relationship management

Deliverables:

- add alias endpoint;
- relationship endpoint;
- merge/split UX contract;
- audit records.

Acceptance gate:

- Suggested aliases are user-confirmed.
- Merging preserves history and can be audited.

### Subphase 6.2 — Resource dependencies and preflight

Deliverables:

- `GET /v1/activities/{activity_id}/preflight-checks`
- `POST /v1/activities/{activity_id}/preflight-checks`
- resource dependency aggregation.
- preflight suggestion thresholds.

Acceptance gate:

- Repeated sponge detours can suggest "Check sponge/scrubber before washing pans."
- Preflight checks can be accepted, hidden, snoozed, or retired.

## Phase 7 — Grounded Ask About Time

### Goal

Answer plain-language timing questions using deterministic facts and evidence.

### Dependencies

Phases 2–6 complete; retrieval can be baseline FTS before pgvector.

### Subphase 7.1 — Query planner and deterministic facts

Deliverables:

- query intent classifier;
- activity/entity resolution;
- SQL aggregation;
- evidence bundle creation.

Acceptance gate:

- Answers can be generated without LLM narration.
- Facts include sample size, window, confidence, limitations.

### Subphase 7.2 — Retrieval and narration

Deliverables:

- retrieval documents;
- optional pgvector embeddings;
- evidence selection;
- LLM narration constrained to evidence payload.
- `POST /v1/temporal/query`
- `GET /v1/temporal/query/{answer_id}`

Acceptance gate:

- Query grounding evals pass.
- Answers do not invent stats or quote private raw context without permission.

## Phase 8 — Design implementation and Figma alignment

### Goal

Turn the design language and reference mockups into code-ready native screens.

### Dependencies

Can begin after Phase 1 contracts but must follow data model alignment.

### Subphase 8.1 — Figma artifact alignment

Deliverables:

- Parallax-named Figma file.
- P0 screens and state variants.
- Tokens and components aligned to `contracts/design/design_tokens.json`.
- Prototype for the flagship loop.

Acceptance gate:

- Figma frames use Parallax names.
- Screens include offline, pending, needs-review, high-contrast, and Dynamic Type states.

### Subphase 8.2 — UI implementation

Deliverables:

- app shell;
- core screens;
- local event persistence;
- API integration;
- contract tests for view-model mappings.

Acceptance gate:

- UI can complete first vertical slice.
- UI state enums are projections, not conflicting domain enums.

## Phase 9 — Optional extension hardening and operations maturity

### Goal

Enable optional search/analytics enhancements only when baseline behavior is proven.

### Dependencies

Phase 7 complete for ParadeDB/pgvector hardening; Phase 2 complete for Timescale analytics.

### Subphase 9.1 — pgvector retrieval

Acceptance gate:

- HNSW indexes work for selected embedding dimensions.
- Re-embedding plan and dual-read comparison exist.

### Subphase 9.2 — ParadeDB profile

Acceptance gate:

- BM25 index syntax validated against selected database image.
- Hybrid lexical/vector retrieval improves measured query/evidence quality.

### Subphase 9.3 — Timescale profile

Acceptance gate:

- Analytics shadow table/continuous aggregates work without changing source-of-truth semantics.
- Backup/restore tested.

### Subphase 9.4 — k3s readiness

Acceptance gate:

- Compose remains source for local dev.
- k3s manifests support internal-only model endpoints, secrets, volumes, and health checks.


### Subphase 9.5 — Optional PostGIS profile

Acceptance gate:

- `database/optional_profiles/0012_postgis_optional_geospatial_profile.sql` applies to the selected database image.
- `user_place` and `geospatial_observation` receive geography columns and GiST indexes.
- Radius/place lookup queries use `ST_DWithin` or equivalent index-aware functions.
- Turning off PostGIS leaves baseline numeric lat/lon storage and manual place selection intact.

### Subphase 9.6 — Optional Timescale capture-context profile

Acceptance gate:

- `database/optional_profiles/0013_timescale_capture_context_profile.sql` applies to the selected database image.
- High-volume context metrics can be aggregated without changing source-of-truth tables.
- Continuous aggregates/backfill jobs are tested.
- Backup/restore is validated for both source tables and optional shadow analytics tables.


## Global release gates

No private alpha until:

- first vertical slice passes;
- raw context logging is disabled by default;
- offline timing and review draft work;
- privacy settings exist and affect behavior;
- query answers are evidence-backed;
- cross-user data isolation tests pass;
- accessibility checklist passes;
- backup/restore runbook is tested at least once in staging.
