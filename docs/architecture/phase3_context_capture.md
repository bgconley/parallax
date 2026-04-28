# Phase 3 Context Capture

Phase 3 extends the implemented canonical subset with context capture endpoints:

- `POST /v1/timing/sessions/{session_id}/annotations`
- `GET /v1/timing/annotations/{annotation_id}`
- `GET/PATCH /v1/privacy/context-capture-policy`
- `POST/GET /v1/timing/sessions/{session_id}/capture-context`
- `GET /v1/timing/sessions/{session_id}/review-flags`
- `PATCH /v1/timing/review-flags/{flag_id}`
- `POST/GET /v1/places`, `POST /v1/places/resolve`, `PATCH /v1/places/{place_id}`

The scope is limited to `docs/03_phased_implementation_plan.md` Phase 3. Structured extraction, place inference workflows, forgotten-timer detection, feature-vector generation, Ask About Time, and optional PostGIS/Timescale profiles remain out of scope until their owning phases are explicitly started.

## Architecture

Routes stay thin and delegate to `ContextService`. Context schemas live in `schemas/context.py`; context persistence lives behind a dedicated `contexts` unit-of-work repository. Timing repositories remain responsible for source timing events and session projections; their only Phase 3 change is persisting and loading `capture_context_snapshot_id` and `capture_context_snapshot_ref`.

## Semantics

Annotations are source actions and create `annotation_captured` timing events, but they do not start extraction in Phase 3. Capture snapshots are auxiliary evidence: they can link to timing events or annotations and can later feed Phase 4 workflows, but they never change duration totals by themselves. Pending offline snapshot refs resolve when the snapshot arrives by matching the snapshot mutation id or idempotency key.

The server-side `context_capture_policy` is authoritative. When policy disables a signal, uploaded observations are dropped or degraded even if the request reports OS permission as available. Places remain user-scoped; `POST /v1/places/resolve` is read-only and confirmation uses mutating place endpoints.

## Verification

Phase 3 is complete only when local unit/static checks pass and the GPU node passes `make schema-smoke`, `make phase1-smoke`, `make phase2-smoke`, and `make phase3-smoke` against the current working tree.
