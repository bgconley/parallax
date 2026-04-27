# Repository Guidelines

## Project Structure & Module Organization

This checkout contains the Parallax v1.3 artifact pack, not a full application implementation. The canonical source is `parallax_v1_3_artifact_pack/`; keep the zip archive in sync only when intentionally rebuilding it. Start with `README.md` and `AGENT_START_HERE.md`.

Key directories:

- `docs/`: product, architecture, privacy, testing, operations, and implementation guidance.
- `contracts/`: OpenAPI, JSON Schema, event/job contracts, Pydantic scaffold, and design tokens.
- `database/`: migrations, optional profiles, rollback notes, and example queries.
- `infrastructure/`: prototype Compose, Caddy, ZFS, and object storage plans.
- `scripts/`: pack bootstrap and validation utilities.
- `examples/` and `tests_or_eval/`: payload samples, reference mockups, semantic test matrices, and eval cases.

## Build, Test, and Development Commands

Run commands from `parallax_v1_3_artifact_pack/` unless noted.

- `./scripts/bootstrap_dev.sh`: creates `infrastructure/.env` and prints the startup command.
- `docker compose -f infrastructure/compose/docker-compose.parallax.prototype.yml --env-file infrastructure/.env up --build`: starts the prototype service stack. API/worker Dockerfiles are expected in an implementation repo.
- `python3 scripts/validate_pack.py --skip-zip-check`: validates files, parseability, migration order, mutation envelopes, and retired-name leakage.
- `python3 scripts/validate_pack.py --zip-path ../parallax_v1_3_artifact_pack.zip`: also checks archive contents.

## Coding Style & Naming Conventions

Use `Parallax` for product copy, `parallax` for packages/services/databases, and `PARALLAX_` for environment variables. Preserve canonical contract names and enums; do not introduce retired placeholders. Python code should target Python 3.12+, FastAPI, Pydantic v2, Alembic, Ruff, and pytest. Keep optional profiles under `database/optional_profiles/`.

## Testing Guidelines

Use `docs/12_testing_qa_release_rollback.md` as the test authority. Seed timing semantics from `tests_or_eval/temporal_semantics_test_matrix.csv`; use JSONL files in `tests_or_eval/` for LLM/retrieval evaluation. Contract changes must update OpenAPI, JSON Schema, examples, docs, and tests together.

## Environment Routing

Unit tests may run locally on the Mac. Run all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations on the GPU node, because that is the deployment host. Keep frontend testing, Xcode and SwiftUI work, initial Figma work, and Playwright-based UI validation on the Mac.

Access the GPU node with `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.

## Commit & Pull Request Guidelines

Use concise imperative commits, for example `Add timing session contract tests`. PRs should describe the artifact or implementation change, link the issue or ADR, list validation commands run, and include screenshots for UI/mockup changes.

## Security & Configuration Tips

Treat raw notes, transcripts, audio, embeddings, timing patterns, and context observations as privacy-sensitive. Do not log raw sensitive payloads. Every mutating API endpoint must carry a mutation envelope; resolver POST endpoints must remain read-only.
