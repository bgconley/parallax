# Phase 0 Bootstrap

Phase 0 is complete. Its scope is repository validation, local/GPU runtime bootstrap, health readiness, and baseline migration tooling. Later phases still require explicit user instruction before work begins.

## Runtime Path

The root `docker-compose.yml` includes `infra/compose/docker-compose.parallax.prototype.yml`.
That file is an implementation derivative of the canonical prototype Compose file in
`parallax_v1_3_artifact_pack/infrastructure/compose/`. The derivative keeps the same
Phase 0 service set, but adapts it for the accepted GPU-node runtime by using
Parallax-specific localhost ports, `/srv/parallax` bind mounts, root `.env` loading,
service health checks, pinned external service images, and API/worker Dockerfiles.

Services bind stateful paths to the canonical GPU-node ZFS mountpoints under `/srv/parallax`:

- Postgres data: `/srv/parallax/postgres`
- Postgres WAL: `/srv/parallax/postgres_wal`
- MinIO objects: `/srv/parallax/objects`
- service logs/config: `/srv/parallax/logs`, `/srv/parallax/config`

Host ports are Parallax-specific localhost ports so the stack can coexist with other apps on the GPU node: API `18000`, Postgres `15432`, Redis `16379`, Temporal `17233`, Temporal UI `18088`, MinIO `19000/19001`, and Caddy `18080/18443`.

## Code Boundaries

- `services/api/parallax_api/routes/health.py`: thin HTTP response construction only.
- `services/api/parallax_api/services/health.py`: runtime dependency checks for Postgres, Redis, Temporal, and object storage.
- `packages/db/parallax_db/runner.py`: baseline SQL migration application and schema smoke checks.
- `scripts/apply_migrations.py`: repo-root CLI wrapper for the migration runner.
- `services/worker/parallax_worker/main.py`: Phase 0 worker process placeholder only; no domain workflows yet.

## Verification Commands

Mac-safe checks:

```bash
uv run ruff check .
make typecheck
uv run pytest -q
make validate
make security
python3 parallax_v1_3_artifact_pack/scripts/validate_pack.py --zip-path parallax_v1_3_artifact_pack.zip
docker compose -f docker-compose.yml --env-file .env.example config
```

GPU-node runtime checks from `/tank/repos/parallax`:

```bash
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax uv sync --frozen --all-groups
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax uv run ruff check .
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make typecheck
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax uv run pytest -q
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make validate
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make security
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make dev-up
PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make schema-smoke
curl -fsS http://127.0.0.1:18000/v1/health
curl -fsS http://127.0.0.1:18000/v1/ready
curl -fsS http://127.0.0.1:18000/v1/live
```
