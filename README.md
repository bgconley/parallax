# Parallax

Parallax is a temporal-first personal intelligence app implemented from the canonical v1.3 artifact pack in `parallax_v1_3_artifact_pack/`.

The first implementation target is the API-first temporal core: activities, timing sessions, append-safe source events, review gates, and contract validation. Optional PostGIS, TimescaleDB, ParadeDB, passive background capture, and advanced ML features stay out of the baseline path until the core loop is verified.

## Development

```bash
cp .env.example .env
uv run pytest
uv run ruff check .
python3 parallax_v1_3_artifact_pack/scripts/validate_pack.py --skip-zip-check
```

Backend integration, functional tests, and end-of-phase validation run on the GPU node documented in `AGENTS.md`.
