# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

Phase 0-7 implementation work is present, and the runtime exposes the canonical
v1.3 API method surface. Later-phase depth remains baseline/deterministic until
each owning phase is expanded, but no canonical `/v1` endpoint is silently
absent at the API boundary.

See `docs/architecture/phase0_bootstrap.md`, `docs/architecture/phase1_core_loop.md`, `docs/architecture/phase2_review_profile.md`, `docs/architecture/phase3_context_capture.md`, `docs/architecture/phase4_structured_extraction.md`, `docs/architecture/phase5_checkpoints_latency_features.md`, `docs/architecture/phase7_grounded_ask.md`, and `docs/architecture/api_surface_phase_scope.md` for the current codepaths, implemented API subset, and validation commands.

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
