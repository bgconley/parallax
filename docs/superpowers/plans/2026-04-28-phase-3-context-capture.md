# Phase 3 Context Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 3 only: context annotations, capture context policy/snapshots, places, and timing review flag APIs without starting Phase 4 extraction/inference.

**Architecture:** Keep timing routes/services focused on timing facts. Add a dedicated context schema/repository/service/route slice for annotations, snapshots, context policy, places, and review flags. Context is auxiliary evidence; it may link to timing events and annotations but must not change session duration totals by itself.

**Tech Stack:** FastAPI, Pydantic v2, PostgreSQL SQL migrations, psycopg, pytest, Ruff, mypy, Docker Compose on the GPU node.

---

## Canonical Scope

Phase 3 implements `docs/03_phased_implementation_plan.md` Subphases 3.1-3.4:

- `POST /v1/timing/sessions/{session_id}/annotations`
- `GET /v1/timing/annotations/{annotation_id}`
- `GET/PATCH /v1/privacy/context-capture-policy`
- `POST/GET /v1/timing/sessions/{session_id}/capture-context`
- `GET /v1/timing/sessions/{session_id}/review-flags`
- `PATCH /v1/timing/review-flags/{flag_id}`
- `POST/GET /v1/places`, `POST /v1/places/resolve`, `PATCH /v1/places/{place_id}`

Phase 4 seams only: annotations remain pending for later extraction; place inference and forgotten-timer detection are not implemented here.

## File Structure

- Create `services/api/parallax_api/schemas/context.py` for Phase 3 DTOs and enums.
- Create `services/api/parallax_api/repositories/context_repository.py` for in-memory context persistence.
- Create `services/api/parallax_api/repositories/postgres_context_repository.py` for PostgreSQL context persistence.
- Modify unit-of-work files to expose `contexts` as a focused repository boundary.
- Create `services/api/parallax_api/services/context_service.py` for mutation replay, policy enforcement, and read-only resolver rules.
- Create `services/api/parallax_api/routes/context.py` for Phase 3 endpoints.
- Modify `services/api/parallax_api/services/timing_service.py` narrowly to resolve existing/pending snapshot references on timing events.
- Modify `services/api/parallax_api/repositories/postgres_timing_repository.py` narrowly so timing events persist/load snapshot refs added by migration `0011`.
- Copy canonical migrations `0011_capture_context_geospatial_sensor_fusion.sql` and `0014_timing_review_flags.sql` into root `migrations/`.
- Modify `packages/db/parallax_db/migrations.py` and `runner.py` so current baseline migrations include Phase 3 context tables/enums.
- Modify `services/api/parallax_api/services/sync_service.py` to support offline annotation and capture snapshot replay.
- Create `services/api/tests/test_phase3_context_capture.py`.
- Create `scripts/phase3_smoke.py` and add `make phase3-smoke`.
- Add `docs/architecture/phase3_context_capture.md` and update `AGENTS.md`, OpenWolf notes, and contract-surface tests.

## Tasks

### Task 1: Phase 3 tests first

- [ ] Add API tests covering annotation creation/get, annotation source event creation, private/sensitive raw text retention, privacy-safe logging, policy get/patch, snapshot capture with all permissions denied, backend policy dropping disabled location/radio payloads, timing event snapshot-ref resolution, place resolver read-only behavior, user-confirmed place creation/update, review-flag list/resolve without changing session totals, and sync replay for annotation/snapshot operations.
- [ ] Run `uv run pytest services/api/tests/test_phase3_context_capture.py -q`.
- [ ] Expected result before implementation: failures because Phase 3 routes and schemas do not exist.

### Task 2: Migrations and schema smoke

- [ ] Copy canonical `0011` and `0014` migrations to root `migrations/`.
- [ ] Extend baseline migration discovery to include `0011` and `0014`, not optional profiles.
- [ ] Extend schema smoke checks to include context tables/enums and review flags.
- [ ] Run migration-related tests; expected result after implementation: current baseline detects Phase 3 schema objects.

### Task 3: Context persistence boundary

- [ ] Add context DTOs matching OpenAPI field names and enums.
- [ ] Add in-memory and Postgres context repositories for annotations, policies, snapshots, places, and review flags.
- [ ] Add snapshot reference resolution by matching pending `capture_context_snapshot_ref` against snapshot `client_mutation_id` or `idempotency_key`.
- [ ] Keep raw radio/location policy filtering in the service layer; repositories only persist filtered data.

### Task 4: Context service and routes

- [ ] Add a thin route module for Phase 3 endpoints.
- [ ] Use `MutationReplayService` for every mutating endpoint.
- [ ] Keep `/v1/places/resolve` read-only.
- [ ] Enforce context capture policy before storing observations.
- [ ] Do not log raw notes, raw coordinates, raw radio labels, or radio raw object refs.

### Task 5: Offline sync integration

- [ ] Register sync operation schemas for `create_context_annotation` and `create_capture_context_snapshot`.
- [ ] Dispatch through `ContextService` so nested endpoint validation, mutation replay, and policy filtering are identical to direct calls.
- [ ] Add tests proving sync operations apply effects and invalid nested payloads are rejected.

### Task 6: Smoke and docs

- [ ] Add `scripts/phase3_smoke.py` to exercise the Phase 3 acceptance gate against the GPU API and Postgres.
- [ ] Add `make phase3-smoke`.
- [ ] Document Phase 3 scope and the Phase 4 seam in `docs/architecture/phase3_context_capture.md`.
- [ ] Update AGENTS/OpenWolf status so Phase 4 remains inactive until explicitly started.

### Task 7: Verification

- [ ] Local: `uv run ruff check .`
- [ ] Local: `make typecheck`
- [ ] Local: `uv run pytest -q`
- [ ] Local: `make validate`
- [ ] Local: `make security`
- [ ] GPU: `uv sync --frozen --all-groups`
- [ ] GPU: `uv run ruff check .`
- [ ] GPU: `make typecheck`
- [ ] GPU: `uv run pytest -q`
- [ ] GPU: `make validate`
- [ ] GPU: `make dev-up`
- [ ] GPU: `make schema-smoke`
- [ ] GPU: health/ready/live curl checks
- [ ] GPU: `make phase1-smoke`, `make phase2-smoke`, `make phase3-smoke`
- [ ] GPU: clean throwaway database migration proof through `0014`

## Acceptance Gate Mapping

- Raw text annotation saves with extraction unavailable: annotation API stores text and marks extraction/transcription pending without invoking Phase 4.
- Annotation privacy: private/sensitive annotations persist and are absent from normal logs and validation errors.
- Source event: annotation creation appends exactly one `annotation_captured` timing event with replay protection.
- Sensor-denied path: timing and annotation capture work with denied/not-requested/unsupported sensor states.
- Snapshot linkage: timing events and annotations accept pending snapshot refs and resolve once the snapshot exists.
- Duration safety: context snapshots and review-flag resolution do not change session totals.
- Server policy authority: disabled server policy drops or degrades uploaded location/radio/device observations even if request says OS permissions are available.
- Non-primary surface: at least one widget/watch/shortcut capture method is covered by tests.
- Places: resolver is read-only; confirmed place creation/update requires mutation envelopes.
- Review flags: list and resolve APIs operate without mutating source timing events or derived totals.
