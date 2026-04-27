# Phase 0/1 Temporal Core Implementation Plan

> Status note, 2026-04-27: this is a historical combined plan. The user has
> explicitly started Phase 1. Current Phase 0 and Phase 1 scope and verification
> live in `docs/architecture/phase0_bootstrap.md` and
> `docs/architecture/phase1_core_loop.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Parallax repository foundation and first API-level activity/timing session loop from the v1.3 artifact pack.

**Architecture:** Keep routes thin and place business rules in services. Use repository interfaces so Phase 1 behavior can be unit-tested on the Mac and later verified against PostgreSQL on the GPU node. Treat OpenAPI/JSON Schema and artifact migrations as canonical.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest, Ruff, explicit SQL migrations, Docker Compose.

---

### Task 1: Repository Foundation

**Files:**
- Create: `README.md`, `.env.example`, `.gitignore`, `Makefile`, `pyproject.toml`
- Create: `migrations/README.md`
- Create: `docs/architecture/README.md`, `docs/privacy/raw_context.md`, `evals/README.md`
- Copy: artifact baseline SQL into `migrations/`

- [ ] Write tests for contract/migration discovery in `tests/test_contract_validation.py`.
- [ ] Run `uv run pytest tests/test_contract_validation.py -q` and verify import failures before implementation.
- [ ] Implement `packages/contracts/parallax_contracts/validation.py` for JSON/YAML parsing, mutation-envelope checks, and retired-name scanning.
- [ ] Implement `packages/db/parallax_db/migrations.py` for ordered baseline migration discovery.
- [ ] Run `uv run pytest tests/test_contract_validation.py -q` and `uv run ruff check .`.

### Task 2: API Shell and Runtime

**Files:**
- Create: `services/api/parallax_api/main.py`
- Create: `services/api/parallax_api/settings.py`
- Create: `services/api/parallax_api/auth.py`
- Create: `services/api/parallax_api/routes/health.py`
- Create: `services/api/tests/test_health.py`

- [ ] Write failing tests for `GET /v1/health` and `GET /v1/version`.
- [ ] Implement typed settings and a Phase 1 auth stub that requires `X-Parallax-User-Id` and rejects missing or malformed values.
- [ ] Keep health/version endpoints free of domain writes.
- [ ] Run the focused health tests locally.

### Task 3: Activity Loop

**Files:**
- Create: `services/api/parallax_api/schemas/common.py`
- Create: `services/api/parallax_api/schemas/activity.py`
- Create: `services/api/parallax_api/repositories/activity_repository.py`
- Create: `services/api/parallax_api/services/activity_service.py`
- Create: `services/api/parallax_api/routes/activities.py`
- Create: `services/api/tests/test_activities.py`

- [ ] Write failing tests for create/list/get activity and duplicate canonical key handling.
- [ ] Write a failing resolver test proving `POST /v1/activities/resolve` is read-only.
- [ ] Implement mutation envelope validation and activity service behavior.
- [ ] Run activity tests locally.

### Task 4: Timing Session Loop

**Files:**
- Create: `services/api/parallax_api/schemas/timing.py`
- Create: `services/api/parallax_api/repositories/timing_repository.py`
- Create: `services/api/parallax_api/services/timing_service.py`
- Create: `services/api/parallax_api/routes/timing.py`
- Create: `services/api/tests/test_timing_sessions.py`

- [ ] Write failing tests for session create/get, event append, complete, and duplicate event replay.
- [ ] Implement append-safe timing events and state transitions `draft -> running/paused -> completed_unreviewed`.
- [ ] Preserve client clock fields and idempotency metadata.
- [ ] Run timing tests locally.

### Task 5: Backend Verification on GPU Node

**Files:**
- Modify: `Makefile`, `docker-compose.yml`, `infra/compose/docker-compose.yml`

- [ ] Push or sync the implementation to the GPU node.
- [ ] Run backend/integration checks on the GPU node using `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.
- [ ] Verify contract parsing, migration application, API health, and first scripted activity/session flow.
- [ ] Report phase status against Phase 0 and Phase 1 acceptance gates.
