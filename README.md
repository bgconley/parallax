# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

Phase 0 bootstrap is complete. The active implementation scope is Phase 1: the core activity and whole-task timing session loop. Optional PostGIS, TimescaleDB, ParadeDB, passive background capture, review/profile APIs, and advanced ML features stay out until their phases are explicitly started and verified.

See `docs/architecture/phase0_bootstrap.md` and `docs/architecture/phase1_core_loop.md` for the current codepaths and validation commands.

## Development

```bash
cp .env.example .env
uv run ruff check .
make typecheck
uv run pytest -q
make validate
make security
docker compose -f docker-compose.yml --env-file .env.example config
```

Backend integration, functional tests, and end-of-phase validation run on the GPU node documented in `AGENTS.md`.
