# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

The active implementation scope is Phase 0 bootstrap until the user explicitly starts a later phase. Phase 0 covers repository validation, Docker Compose runtime startup, API health readiness, and baseline migration tooling. Optional PostGIS, TimescaleDB, ParadeDB, passive background capture, and advanced ML features stay out of the baseline path until the core loop is authorized and verified.

See `docs/architecture/phase0_bootstrap.md` for the current Phase 0 codepath and validation commands.

## Development

```bash
cp .env.example .env
uv run ruff check .
uv run pytest -q
make validate
docker compose -f docker-compose.yml --env-file .env.example config
```

Backend integration, functional tests, and end-of-phase validation run on the GPU node documented in `AGENTS.md`.
