# Phase 2 Review and Activity Profile

Phase 2 extends the implemented canonical subset with review, discard, and profile endpoints:

- `POST /v1/timing/sessions/{session_id}/review`
- `POST /v1/timing/sessions/{session_id}/discard`
- `GET /v1/activities/{activity_id}/profile`

The scope is limited to `docs/03_phased_implementation_plan.md` Phase 2. Context annotations, extraction workflows, Ask About Time, optional extension profiles, and production auth provider work remain out of scope until their owning phases are explicitly started.

## Architecture

Routes stay thin and delegate to services. `TimingService` owns review/discard orchestration, mutation replay, and synchronous profile recomputation for the baseline vertical slice. Pure span and stats behavior lives in `services/api/parallax_api/domain/`; repositories own in-memory and PostgreSQL persistence for spans, model-update decisions, audit rows, and activity stats snapshots.

## Counting Semantics

Review derives `timing_event_span` rows from source events. `resource_detour` and `interruption` spans count toward wall time by default and are excluded from active duration. Active spans are derived from the remaining session intervals. Discard decisions set `model_inclusion=exclude`; `discard_all` marks the run as `bad_timer` so corrupted forgot-to-stop runs do not train Activity Profile ranges.

## Verification

Phase 2 is complete only when local unit/static checks pass and the GPU node passes `make schema-smoke`, `make phase1-smoke`, and `make phase2-smoke` against the current working tree.
