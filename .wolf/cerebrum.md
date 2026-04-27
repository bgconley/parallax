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

## Key Learnings

- **Project:** parallax
- **Canonical ZFS setup:** Parallax storage starts from `infrastructure/zfs/zfs_dataset_plan.md` and `infrastructure/zfs/create_parallax_datasets.sh`: datasets use the `parallax` namespace, mount under `/srv/parallax`, and the real ZFS pool name must be passed to the script.
- **GPU node storage additions:** Parallax uses existing `/tank/repos` and `/tank/venvs` parents, with project subdirectories `/tank/repos/parallax` and `/tank/venvs/parallax`.
- **Verified GPU node storage:** `tank/parallax/*` datasets are mounted under `/srv/parallax`; `/tank/repos/parallax` is on ZFS via `tank/repos`; `/tank/venvs/parallax` resolves to root ext4 and is expected.
- **Verified runtime permissions:** `/srv/parallax` is `root:root 0755`; `postgres` and `postgres_wal` are numeric `999:999 0700`; app-writable objects/exports/models/hf_cache/logs are `10001:bgconley 0770`; config/observability are `bgconley:bgconley 0755`; backups are `root:bgconley 0750`.
- **Remote sudo:** Use `ssh -tt` for commands that need remote sudo prompts. Do not run `sudo ssh` on the Mac for GPU-node sudo work.
- **UID display caveat:** UID/GID `999` displays as host-local names on the GPU node, but container compatibility depends on numeric IDs. Re-check Postgres data-dir UID/GID after the database image is pinned.

## Do-Not-Repeat

<!-- Mistakes made and corrected. Each entry prevents the same mistake recurring. -->
<!-- Format: [YYYY-MM-DD] Description of what went wrong and what to do instead. -->
- [2026-04-27] Do not infer Parallax storage layout from existing GPU-node directories before reading the canonical artifact. For ZFS/storage work, review the Parallax ZFS plan and dataset script first.
- [2026-04-27] Do not use local `sudo ssh` to satisfy a remote sudo prompt. Use `ssh -tt ... 'sudo -v && sudo <command>'` so sudo can read the password on the GPU node.
- [2026-04-27] Remove generated `.DS_Store` files before pack validation or commits; the artifact validator treats them as manifest drift.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
- [2026-04-27] Parallax storage policy is split into dataset bootstrap and permission-only application: `scripts/setup_gpu_node_storage.sh` creates/updates datasets and repo/venv paths; `scripts/apply_gpu_node_permissions.sh` reapplies runtime ownership/modes without touching datasets or Git state.
- [2026-04-27] Runtime service-write permissions use configurable numeric IDs with `10001:bgconley` as the default app/service owner and `999:999` as the provisional Postgres owner until the DB image is pinned.
