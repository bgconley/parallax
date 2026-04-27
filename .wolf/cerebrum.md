# Cerebrum

> OpenWolf's learning memory. Updated automatically as the AI learns from interactions.
> Do not edit manually unless correcting an error.
> Last updated: 2026-04-27

## User Preferences

<!-- How the user likes things done. Code style, tools, patterns, communication. -->
- Unit tests may run on the Mac, but all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations must run on the GPU node where Parallax will live. Frontend testing, Xcode/SwiftUI work, initial Figma work, and Playwright UI validation should run on the Mac.
- GPU node access: `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.
- Before inferring anything about Parallax implementation or infrastructure from the GPU node, existing apps, or local conventions, review the relevant canonical artifact files and let them drive the decision.
- Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. Pull remote updates into `/tank/repos/parallax` after Mac-side pushes.
- The existing `/tank/venvs/parallax` path is acceptable even though `tank/venvs` is root ext4 rather than ZFS.
- Use `uv` for GPU-node Parallax Python work, with `UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax`.
- Do not begin Phase 1 or any later phase without explicit user instruction. Close and verify the current phase acceptance gate first.

## Key Learnings

- **Project:** parallax
- **Canonical ZFS setup:** Parallax storage starts from `infrastructure/zfs/zfs_dataset_plan.md` and `infrastructure/zfs/create_parallax_datasets.sh`: datasets use the `parallax` namespace, mount under `/srv/parallax`, and the real ZFS pool name must be passed to the script.
- **GPU node storage additions:** Parallax uses existing `/tank/repos` and `/tank/venvs` parents, with project subdirectories `/tank/repos/parallax` and `/tank/venvs/parallax`.
- **Verified GPU node storage:** `tank/parallax/*` datasets are mounted under `/srv/parallax`; `/tank/repos/parallax` is on ZFS via `tank/repos`; `/tank/venvs/parallax` resolves to root ext4 and is expected.
- **Verified runtime permissions:** `/srv/parallax` is `root:root 0755`; `postgres` and `postgres_wal` are numeric `999:999 0700`; app-writable objects/exports/models/hf_cache/logs are `10001:bgconley 0770`; config/observability are `bgconley:bgconley 0755`; backups are `root:bgconley 0750`.
- **Remote sudo:** Use `ssh -tt` for commands that need remote sudo prompts. Do not run `sudo ssh` on the Mac for GPU-node sudo work.
- **UID display caveat:** UID/GID `999` displays as host-local names on the GPU node, but container compatibility depends on numeric IDs. Re-check Postgres data-dir UID/GID after the database image is pinned.
- **GPU uv path:** `uv` is installed at `/home/bgconley/.local/bin/uv`; non-interactive SSH sessions do not include that path by default, so prefix `PATH=/home/bgconley/.local/bin:$PATH`.
- **GPU venv binding:** Use `UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax` for `uv sync`, `uv run pytest`, `uv run ruff`, and `make validate` on the GPU node. Do not create or use `/tank/repos/parallax/.venv`.
- **Phase 0 runtime ports:** Compose binds to Parallax-specific localhost ports on the GPU node: API `18000`, Postgres `15432`, Redis `16379`, Temporal `17233`, Temporal UI `18088`, MinIO `19000/19001`, Caddy `18080/18443`.
- **Baseline migration runner:** `scripts/apply_migrations.py` applies only the baseline `migrations/` files discovered by `packages/db/parallax_db/runner.py`; optional profiles remain excluded until explicitly enabled.
- **Temporal image quirk:** `temporalio/auto-setup:1.24` rejects `DB=postgresql`; use `DB=postgres12`.
- **Artifact SQL correction:** PostgreSQL expression uniqueness must be represented as a unique expression index, not a table-level `UNIQUE(activity_id, lower(resource_name))` constraint.

## Do-Not-Repeat

<!-- Mistakes made and corrected. Each entry prevents the same mistake recurring. -->
<!-- Format: [YYYY-MM-DD] Description of what went wrong and what to do instead. -->
- [2026-04-27] Do not infer Parallax storage layout from existing GPU-node directories before reading the canonical artifact. For ZFS/storage work, review the Parallax ZFS plan and dataset script first.
- [2026-04-27] Do not use local `sudo ssh` to satisfy a remote sudo prompt. Use `ssh -tt ... 'sudo -v && sudo <command>'` so sudo can read the password on the GPU node.
- [2026-04-27] Remove generated `.DS_Store` files before pack validation or commits; the artifact validator treats them as manifest drift.
- [2026-04-27] Do not install GPU-node Python tools with system `python3 -m pip install --user`; Ubuntu blocks it via PEP 668. Use the existing user-level `uv` binary at `/home/bgconley/.local/bin/uv`.
- [2026-04-27] Avoid single quotes inside Python snippets embedded in single-quoted SSH heredocs; assign values like `session_id = session["id"]` before f-strings to avoid shell-stripping bugs.
- [2026-04-27] Do not start Phase 1 before Phase 0 is completely verified. Phase progression requires explicit user instruction and current acceptance-gate evidence.
- [2026-04-27] Do not bind Parallax Phase 0 services to common host ports such as `5432`, `6379`, or `8000` on the GPU node; Structura and other stacks may already use them.
- [2026-04-27] Do not use `DB=postgresql` with `temporalio/auto-setup:1.24`; it exits with "Unsupported driver specified". Use `DB=postgres12`.
- [2026-04-27] Do not put expression uniqueness inside a PostgreSQL table-level `UNIQUE` constraint. Use a unique expression index after table creation.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
- [2026-04-27] Parallax storage policy is split into dataset bootstrap and permission-only application: `scripts/setup_gpu_node_storage.sh` creates/updates datasets and repo/venv paths; `scripts/apply_gpu_node_permissions.sh` reapplies runtime ownership/modes without touching datasets or Git state.
- [2026-04-27] Runtime service-write permissions use configurable numeric IDs with `10001:bgconley` as the default app/service owner and `999:999` as the provisional Postgres owner until the DB image is pinned.
- [2026-04-27] GPU-node dependency management follows the repository `uv.lock`: run `PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax uv sync --frozen --all-groups` from `/tank/repos/parallax`.
- [2026-04-27] Phase 0 Compose starts detached via `make dev-up`; use `make dev-logs` for logs and `make dev-down` for shutdown.
- [2026-04-27] API health readiness lives in `services/api/parallax_api/services/health.py`; route handlers stay thin and report Postgres/Redis dependency status without exposing raw connection details.
