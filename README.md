# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

Phase 0 bootstrap is complete, and Phase 1-3 implementation work is present. The active implementation scope is Phase 4: structured context extraction, correction, and place inference. Phase 5 and later stay out until explicitly started and verified.

See `docs/architecture/phase0_bootstrap.md`, `docs/architecture/phase1_core_loop.md`, `docs/architecture/phase2_review_profile.md`, `docs/architecture/phase3_context_capture.md`, `docs/architecture/phase4_structured_extraction.md`, and `docs/architecture/api_surface_phase_scope.md` for the current codepaths, implemented API subset, and validation commands.

## Development

```bash
cp .env.example .env
uv run ruff check .
make typecheck
uv run pytest -q
make validate
make security
make release-status
docker compose -f docker-compose.yml --env-file .env.example config
```

Backend integration, functional tests, and end-of-phase validation run on the GPU node documented in `AGENTS.md`.
