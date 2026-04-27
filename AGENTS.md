# Repository Guidelines

## Project Structure & Module Organization

This checkout contains the Parallax v1.3 artifact pack, not a full application implementation. The canonical source is `parallax_v1_3_artifact_pack/`; keep the zip archive in sync only when intentionally rebuilding the pack. Start with `README.md` and `AGENT_START_HERE.md`, then follow the source-of-truth order listed there.

Key directories:

- `docs/`: product, architecture, privacy, testing, operations, and implementation guidance.
- `contracts/`: OpenAPI, JSON Schema, Pydantic scaffold, event/job contracts, and design tokens.
- `database/`: baseline migrations, optional extension profiles, rollback notes, and example queries.
- `infrastructure/`: prototype Docker Compose, Caddy, ZFS, and object storage plans.
- `scripts/`: pack bootstrap and validation utilities.
- `examples/` and `tests_or_eval/`: payload samples, reference mockups, semantic test matrices, and eval cases.

## Build, Test, and Development Commands

Run commands from `parallax_v1_3_artifact_pack/` unless noted.

- `./scripts/bootstrap_dev.sh`: creates `infrastructure/.env` from the example file and prints the local startup command.
- `docker compose -f infrastructure/compose/docker-compose.parallax.prototype.yml --env-file infrastructure/.env up --build`: starts the prototype Postgres, Redis, Temporal, MinIO, API, worker, and Caddy stack. The API/worker Dockerfiles are expected in an implementation repository.
- `python3 scripts/validate_pack.py --skip-zip-check`: validates required files, JSON/YAML/Python parseability, migration order, mutation-envelope rules, and retired-name leakage.
- `python3 scripts/validate_pack.py --zip-path ../parallax_v1_3_artifact_pack.zip`: additionally checks archive contents against the extracted pack.

## Coding Style & Naming Conventions

Use `Parallax` for product copy, `parallax` for packages/services/databases, and `PARALLAX_` for environment variables. Preserve canonical contract names and enums; do not introduce retired placeholder names. Python implementation code should target Python 3.12+, FastAPI, Pydantic v2, explicit Alembic migrations, Ruff-style linting, and pytest. Keep optional profiles under `database/optional_profiles/`; baseline migration runners should read only `database/migrations/`.

## Testing Guidelines

Use `docs/12_testing_qa_release_rollback.md` as the test authority. Seed timing semantics tests from `tests_or_eval/temporal_semantics_test_matrix.csv`; use JSONL files in `tests_or_eval/` for LLM and retrieval evaluation. Contract changes must update OpenAPI, JSON Schema, examples, docs, and validation tests together.

## Commit & Pull Request Guidelines

This checkout has no `.git` history, so no project-specific commit convention can be inferred. Use concise imperative commits, for example `Add timing session contract tests`. PRs should describe the artifact or implementation change, link the relevant issue or ADR, list validation commands run, and include screenshots for UI/mockup changes.

## Security & Configuration Tips

Treat raw notes, transcripts, audio, embeddings, timing patterns, and context observations as privacy-sensitive. Do not log raw sensitive payloads. Every mutating API endpoint must carry a mutation envelope; resolver POST endpoints must remain read-only.
