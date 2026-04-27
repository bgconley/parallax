# 13 — Repository Layout and Coding Standards

## Recommended repository layout

```text
parallax/
  apps/
    ios/
    web/                         # optional admin/dev console only
  services/
    api/
      parallax_api/
      tests/
    worker/
      parallax_worker/
      tests/
    ai_orchestrator/
      parallax_ai/
      tests/
    estimator/
      parallax_estimator/
      tests/
  packages/
    contracts/
    shared_types/
    db/
  migrations/
  infra/
    compose/
    caddy/
    k3s/
    zfs/
  evals/
    context_extraction/
    query_grounding/
    estimator/
  docs/
    product/
    architecture/
    privacy/
    operations/
  scripts/
  tests/
```

## Root files

Required:

- `README.md`
- `AGENTS.md`
- `.env.example`
- `Makefile`
- `pyproject.toml`
- `docker-compose.yml`
- `migrations/README.md`
- `docs/architecture/README.md`
- `docs/privacy/raw_context.md`
- `evals/README.md`

## Python standards

- Python 3.12+ recommended.
- FastAPI for API.
- Pydantic v2 for schemas.
- SQLAlchemy or SQLModel acceptable, but migrations must remain explicit.
- Alembic for application migrations.
- Ruff or equivalent linting.
- Pytest for tests.
- No raw SQL string interpolation with user input.

## API standards

- All routes under `/v1`.
- Request/response models generated or validated from contracts.
- Treat the Pydantic contract file as scaffold unless regenerated from OpenAPI/JSON
  Schema in the implementation repository.
- Every mutating endpoint requires mutation envelope.
- Resolver POST endpoints are read-only exceptions and must not write domain data.
- Every DB query is user-scoped.
- Errors use structured error shape.
- No raw sensitive payloads in logs.

## Database standards

- Use `uuid` primary keys.
- Use `timestamptz` for timestamps.
- Store client and server time for offline events.
- Keep optional extension SQL under `database/optional_profiles/` and out of the
  baseline migration runner.
- Use explicit enums for stable state machines.
- Use `jsonb` for model metadata and flexible payloads, not as a substitute for first-class temporal concepts.
- Store embeddings by dimension/profile.
- Add indexes for user/time/status access paths.
- Keep optional extension migrations separate.

## Temporal workflow standards

- Workflow code must be deterministic.
- LLM calls, DB calls, HTTP calls, and object storage calls are activities, not workflow logic.
- Workflow activities must be idempotent.
- Persist workflow metadata in `workflow_run`.

## AI standards

- Prompt versions are explicit.
- Schema versions are explicit.
- Raw prompts/responses are not logged by default.
- Model outputs validate before persistence.
- Low-confidence outputs do not train models.
- Every model output has correction path or is internal only.

## UI/iOS standards

- UI state maps to canonical domain state.
- Local timing source actions persist before network sync.
- Screen state includes offline/pending/review-needed variants.
- Dynamic Type and high contrast are first-class.
- Use Parallax design tokens and naming.
- Do not create separate UI enums that conflict with backend enums.

## Documentation standards

- Any contract change updates OpenAPI, JSON Schema, docs, examples, and tests.
- Any architectural deviation gets an ADR.
- Risk changes update risk register.
- Implementation drift updates source-of-truth artifacts before becoming accepted.
