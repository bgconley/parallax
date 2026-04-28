# Phase 1 Core Loop

Phase 1 implements only the canonical activity and whole-task timing session loop from `docs/03_phased_implementation_plan.md`.
Phase 1 implements a deliberate subset of the canonical v1.3 OpenAPI surface. Later endpoints remain deferred to their owning phases and must not be added as runtime stubs before those phases are explicitly started.

## Scope

- Activity create/list/get/resolve.
- Timing session create/get/event append/complete.
- Mutation envelope enforcement on mutating endpoints.
- PostgreSQL-backed replay through `client_mutation_log`.
- `POST /v1/sync/push` top-level and nested mutation-envelope validation plus replay of the supported Phase 1 operation payloads.
- Timer wall/active reconstruction for start, pause, resume, and complete events.
- Phase-scoped route-surface tests proving runtime endpoints match the Phase 1 canonical subset.

Out of scope: review decisions, Activity Profile facts, context capture, review flags, optional extension profiles, passive background capture, and ML/model-serving features.

## Codepath

- Routes stay thin in `services/api/parallax_api/routes/`.
- Business orchestration lives in `services/api/parallax_api/services/`.
- Persistence boundaries are defined by `repositories/unit_of_work.py`.
- Runtime persistence uses PostgreSQL repositories in `repositories/postgres_*`.
- Mac unit tests use `InMemoryUnitOfWorkFactory` for fast deterministic coverage.
- Timing reconstruction is framework-independent in `domain/timing_reconstruction.py`.

## Verification

Run Mac-safe checks locally:

```bash
uv run ruff check .
make typecheck
uv run pytest -q
make validate
make security
```

Run Phase 1 functional verification on the GPU node after syncing code and starting the stack:

```bash
export PATH=/home/bgconley/.local/bin:$PATH
export UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax
cd /tank/repos/parallax
make schema-smoke
make dev-up
make phase1-smoke
```

The smoke test creates an isolated user, proves duplicate replay creates one source event and one mutation-log row, verifies wall/active reconstruction, accepts out-of-order/impossible event sequences with recompute flagged, validates and applies sync push, and cleans up its test user unless `--keep-data` is passed.
