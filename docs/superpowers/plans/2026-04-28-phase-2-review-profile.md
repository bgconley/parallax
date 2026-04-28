# Phase 2 Review and Activity Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2 only: derive timing spans, save review/discard decisions, and compute the first Activity Profile facts from reviewed runs.

**Architecture:** Keep FastAPI routes thin. Put counting and percentile semantics in framework-free domain modules, orchestration in `TimingService`, and database details in timing repositories. Reuse the existing mutation replay boundary so review/discard remain idempotent and user-scoped.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PostgreSQL, pytest, Ruff, mypy, Docker Compose on the GPU node.

---

## Scope

Phase 2 deliverables from the canonical plan:

- Timeline reconstruction service and derived `timing_event_span` creation.
- Active, wall, and friction calculations for reviewed runs.
- Bad-timer/corrupted run marking path.
- `POST /v1/timing/sessions/{session_id}/review`.
- `POST /v1/timing/sessions/{session_id}/discard`.
- `model_update_decision` persistence.
- Correction/audit rows for review changes where applicable.
- `activity_stats_snapshot` computation for reviewed runs.
- `GET /v1/activities/{activity_id}/profile`.

Non-goals:

- Phase 3 context annotation capture.
- Optional pgvector, Timescale, ParadeDB, or PostGIS profiles.
- Later Temporal workflow implementation beyond synchronous Phase 2 recomputation.
- Ask About Time and LLM narration.

## File Responsibilities

- `services/api/parallax_api/domain/timing_spans.py`: pure event-to-span derivation and count-policy defaults.
- `services/api/parallax_api/domain/activity_stats.py`: pure percentile and confidence calculations.
- `services/api/parallax_api/schemas/timing.py`: OpenAPI-aligned Phase 2 DTOs for spans, review requests, model decisions, stats, and profiles.
- `services/api/parallax_api/repositories/timing_repository.py`: in-memory Phase 2 persistence for tests.
- `services/api/parallax_api/repositories/postgres_timing_repository.py`: PostgreSQL reads/writes for spans, decisions, snapshots, corrections, and profiles.
- `services/api/parallax_api/services/timing_service.py`: review/discard orchestration and mutation replay.
- `services/api/parallax_api/routes/timing.py`: review/discard endpoints.
- `services/api/parallax_api/routes/activities.py`: profile endpoint.
- `services/api/tests/test_phase2_review_profile.py`: API behavior tests for Phase 2 acceptance.
- `scripts/phase2_smoke.py`: GPU-node API/Postgres smoke proving the acceptance gate.
- `tests/test_phase1_contract_surface.py`: expand implemented endpoint subset to Phase 2.

## TDD Tasks

- [ ] Write failing API tests for resource-detour and interruption spans: wall counts, active excludes, and friction totals update after review.
- [ ] Write failing API tests for bad-timer/discard decisions: session becomes discarded or reviewed with `exclude`, and no stats baseline is polluted.
- [ ] Write failing API tests for all canonical review decisions mapping to `model_inclusion`.
- [ ] Write failing API tests for `GET /v1/activities/{activity_id}/profile`: sample size, confidence, active/wall p50/p80, recent reviewed runs, and limitations.
- [ ] Write failing replay tests proving duplicate review/discard mutations return the original `ModelUpdateDecision`.
- [ ] Implement pure span derivation and stats modules.
- [ ] Add schemas, repository protocol methods, in-memory persistence, and Postgres persistence.
- [ ] Add service orchestration and route handlers.
- [ ] Update sync replay to support Phase 2 review/discard operations only if needed by Phase 2 smoke.
- [ ] Add `make phase2-smoke` and run it on the GPU node.

## Acceptance Mapping

- Resource detour excludes active time by default: covered by span derivation tests and Phase 2 smoke.
- Interruption excludes active baseline by default: covered by span derivation tests and Phase 2 smoke.
- Forgot-to-stop can mark run as bad timer/corrupted: covered by discard/bad-timer review tests.
- User can save all canonical review decisions: covered by model-inclusion mapping tests.
- Session `model_inclusion` matches review decision: covered by review tests.
- Review changes trigger profile recomputation: covered by profile snapshot tests.
- Activity Profile returns sample size, confidence, active range, wall range, recent reviewed runs, and limitations: covered by profile endpoint tests and smoke.
- LLM not required: no model-serving or narration dependencies are introduced.

## Verification Plan

Local Mac unit/static checks:

- `uv run pytest services/api/tests/test_phase2_review_profile.py -q`
- `uv run pytest -q`
- `uv run ruff check .`
- `make typecheck`
- `make validate`
- `make security`

GPU-node functional/end-of-phase checks:

- `uv sync --frozen --all-groups`
- `uv run ruff check .`
- `make typecheck`
- `uv run pytest -q`
- `make validate`
- `make schema-smoke`
- `make phase1-smoke`
- `make phase2-smoke`
- targeted SQL proof that `model_update_decision`, `timing_event_span`, and `activity_stats_snapshot` rows exist for the smoke user.
