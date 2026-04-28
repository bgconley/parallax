# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

Phase 0 bootstrap is complete, and Phase 1-3 implementation work is present. The active implementation scope is Phase 3: context annotation capture and capture-context support. Phase 4 and later stay out until explicitly started and verified.

See `docs/architecture/phase0_bootstrap.md`, `docs/architecture/phase1_core_loop.md`, `docs/architecture/phase2_review_profile.md`, and `docs/architecture/phase3_context_capture.md` for the current codepaths and validation commands.

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
