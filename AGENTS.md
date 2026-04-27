# Repository Guidelines

## Project Structure & Module Organization

This checkout contains the Parallax v1.3 artifact pack plus the initial Phase 0/1 implementation scaffold. The canonical artifact source remains `parallax_v1_3_artifact_pack/`; keep the zip archive in sync only when intentionally rebuilding it. Start with `README.md` and `parallax_v1_3_artifact_pack/AGENT_START_HERE.md`.

Before making implementation or infrastructure decisions, read the relevant canonical artifact files first. Do not infer Parallax layout, storage, runtime, or service policy from existing GPU-node directories or other apps when a Parallax artifact covers the topic.

Key directories:

- `services/api/`: FastAPI shell, routes, schemas, repositories, services, and API unit tests.
- `packages/contracts/` and `packages/db/`: local validation and database helper packages.
- `migrations/`: copied baseline SQL migrations used by the implementation scaffold.
- `docs/`: product, architecture, privacy, testing, operations, and implementation guidance.
- `infra/`: copied prototype Compose, Caddy, and ZFS artifacts for implementation use.
- `scripts/`: GPU-node storage setup plus validation utilities.
- `parallax_v1_3_artifact_pack/`: canonical docs, contracts, database artifacts, scripts, examples, and eval cases.

## Build, Test, and Development Commands

Run implementation commands from the repository root unless noted.

- `uv run pytest -q`: runs local unit tests.
- `uv run ruff check .`: runs Python lint checks.
- `make validate`: validates the canonical artifact pack and local contract helper.
- `bash -n scripts/setup_gpu_node_storage.sh scripts/apply_gpu_node_permissions.sh`: checks GPU-node shell scripts.
- `docker compose up --build`: starts the prototype stack from the root include file.

## Coding Style & Naming Conventions

Use `Parallax` for product copy, `parallax` for packages/services/databases, and `PARALLAX_` for environment variables. Preserve canonical contract names and enums; do not introduce retired placeholders. Python code should target Python 3.12+, FastAPI, Pydantic v2, Alembic, Ruff, and pytest. Keep optional profiles under `database/optional_profiles/`.

## Testing Guidelines

Use `docs/12_testing_qa_release_rollback.md` as the test authority. Seed timing semantics from `tests_or_eval/temporal_semantics_test_matrix.csv`; use JSONL files in `tests_or_eval/` for LLM/retrieval evaluation. Contract changes must update OpenAPI, JSON Schema, examples, docs, and tests together.

## Environment Routing

Unit tests may run locally on the Mac. Run all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations on the GPU node, because that is the deployment host. Keep frontend testing, Xcode and SwiftUI work, initial Figma work, and Playwright-based UI validation on the Mac.

Access the GPU node with `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.

For GPU-node storage, start from `parallax_v1_3_artifact_pack/infrastructure/zfs/zfs_dataset_plan.md` and `create_parallax_datasets.sh`. Use the `parallax` ZFS namespace and `/srv/parallax` mountpoints from the artifact; pass the actual pool name to the script.

Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. `tank/venvs` is currently root ext4 on this host, not ZFS; that is expected and accepted. After pushing from the Mac, pull updates into `/tank/repos/parallax`.

GPU-node runtime storage is verified under `tank/parallax` mounted at `/srv/parallax`. Apply permissions with `scripts/apply_gpu_node_permissions.sh` after datasets exist. Remote sudo commands need a TTY, for example `ssh -tt -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 'sudo -v && sudo /tmp/apply_gpu_node_permissions.sh'`.

Current permission policy: `/srv/parallax` is `root:root 0755`; Postgres and WAL are numeric `999:999 0700`; service-writable objects/exports/models/cache/logs are `10001:bgconley 0770`; config and observability are `bgconley:bgconley 0755`; backups are `root:bgconley 0750`. Host names for UID/GID `999` may display as unrelated local accounts; verify numeric IDs against the pinned container image when the DB image is finalized.

## Commit & Pull Request Guidelines

Use concise imperative commits, for example `Add timing session contract tests`. PRs should describe the artifact or implementation change, link the issue or ADR, list validation commands run, and include screenshots for UI/mockup changes.

## Security & Configuration Tips

Treat raw notes, transcripts, audio, embeddings, timing patterns, and context observations as privacy-sensitive. Do not log raw sensitive payloads. Every mutating API endpoint must carry a mutation envelope; resolver POST endpoints must remain read-only.
