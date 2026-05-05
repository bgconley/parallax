# Cerebrum

> OpenWolf's learning memory. Updated automatically as the AI learns from interactions.
> Do not edit manually unless correcting an error.
> Last updated: 2026-05-03

## User Preferences

<!-- How the user likes things done. Code style, tools, patterns, communication. -->
- Unit tests may run on the Mac, but all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations must run on the GPU node where Parallax will live. Frontend testing, Xcode/SwiftUI work, initial Figma work, and Playwright UI validation should run on the Mac.
- GPU node access: `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.
- Before inferring anything about Parallax implementation or infrastructure from the GPU node, existing apps, or local conventions, review the relevant canonical artifact files and let them drive the decision.
- After any context compaction, resume, or session transition, re-read the canonical Parallax docs before code or infrastructure changes. For broad app behavior or Phase 9 remediation, start from `AGENT_START_HERE.md`, app spec, temporal domain model, relevant phase plan sections, database README, affected contracts, guardrails, and testing/QA guidance.
- Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. Pull remote updates into `/tank/repos/parallax` after Mac-side pushes.
- The existing `/tank/venvs/parallax` path is acceptable even though `tank/venvs` is root ext4 rather than ZFS.
- Use `uv` for GPU-node Parallax Python work, with `UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax`.
- Do not begin any later phase without explicit user instruction. Phase 0 through Phase 9 are complete. Do not start Phase 10 or broaden later work without explicit user instruction. Close and verify the current phase acceptance gate before advancing.
- For Parallax UI/Figma work, treat `figma_expansion_readiness_pack_v0_8_1/` as design-language reference only. Do not let it expand product scope beyond temporal workflows unless the user explicitly makes a new product-scope decision.
- Before treating Figma work as complete, capture screenshots of the new work, inspect carefully for overlap, cramped boundaries, alignment, centering, clipping, and text fit, then compare against the canonical mockups.
- For the Phase 8 Temporal Home / Today-style Figma target, preserve the canonical schema and density. Do not fix defects by showing fewer items or making larger text boxes; fix lane allocation, object placement, spacing, and border/text clearance inside the existing allocated space.

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
- **Deferred release hardening:** After Phase 0/1 hardening, remaining later-scope items are production/private-alpha auth provider and JWT/session validation, remaining canonical v1.3 endpoints, backup/restore plus WAL/archive proof, load/performance SLO validation, later-phase Temporal workflows, and production traffic/log privacy-scrub proof. Keep them visible but do not implement them during Phase 2 unless their phase or a release-hardening scope is explicitly started.
- **Phase 2 architecture:** Review/counting/profile code is split into pure domain modules (`timing_spans.py`, `activity_stats.py`, `review_decisions.py`), thin services/routes, and in-memory/Postgres repositories. Resource detours and interruptions are wall-only by default and excluded from active duration.
- **Phase 3 architecture:** Context capture code has a dedicated schema/repository/service/route slice; timing code only resolves and persists `capture_context_snapshot_id/ref`. Annotations create `annotation_captured` source events but stay pending for Phase 4 extraction.
- **GPU working-tree sync:** When rsyncing local uncommitted work to `/tank/repos/parallax`, exclude `.env` along with `.git`, `.venv`, `.DS_Store`, and `__pycache__`; otherwise `--delete` removes the GPU node's host-local Compose env file.
- **Phase 4 architecture:** Extraction, place inference, privacy lifecycle, and feature-vector requests use durable `workflow_run` records with the canonical workflow names; the current worker is lightweight but owns completion/failure state instead of silently succeeding from status text.
- **Phase 5 architecture:** Checkpoint-run state is isolated from timing persistence (`checkpoint_run_state.py` / `postgres_checkpoint_runs.py`), latency observations are isolated in dedicated persistence helpers, and feature-vector payload construction lives in pure `domain/feature_vectors.py`.
- **Phase 5 gate:** GPU validation must include `make schema-smoke`, `make phase1-smoke`, `make phase2-smoke`, `make phase3-smoke`, `make phase4-smoke`, and `make phase5-smoke`, plus clean-database migration proof when schema smoke coverage changes.
- **Phase 8 UI scope:** Parallax's active UI scope is temporal: timing sessions, timing launcher/calibration, timing review/correction, checkpoints or "break it down" only as timing workflow support, temporal home/current focus, offline/sync/AI-pending/needs-review/accessibility states for those workflows, and grounded temporal answers where Phase 7 supports them.
- **Phase 8 Figma source of truth:** Active Figma visual targets must be source-backed or canonical-derived from `parallax_v1_3_artifact_pack/examples/` and the current canonical Figma reference pages. Simplified vector drafts are superseded, not finished mockups.
- **Phase 8 Temporal Home Figma target:** The active Temporal Home source is Figma page `118:2`, `10 Phase 8 Temporal Home Canonical Allocation`; the active board is node `118:3`. The failed `106:2` temporal scope draft was deleted after QA because it did not preserve the corrected canonical allocation.
- **Phase 9 optional profiles:** Optional extension profiles live under `database/optional_profiles/` and remain outside the baseline migration runner. Prove them against selected Docker images with `make phase9-smoke` instead of assuming image compatibility.
- **Phase 9 app remediation:** The current remediation scope is app-wide dynamic behavior, not only Temporal Home. Runtime iOS screens must derive from user data, local state, and canonical APIs; Figma/example scenarios belong only in preview/test fixtures or artifact examples.
- **iOS project membership:** SwiftPM auto-discovers new files under `apps/ios/Sources`, but `ParallaxNative.xcodeproj` must be updated manually with PBX file references and source-build-phase membership for simulator builds.
- **Timescale restore proof:** Timescale logical restore must use custom-format `pg_dump`, create/enable TimescaleDB in the target database, call `timescaledb_pre_restore()`, run non-parallel `pg_restore`, then call `timescaledb_post_restore()`.
- **Phase 9 k3s probes/auth:** Production k3s manifests using `external_bearer` must set a non-HS JWT algorithm plus JWKS URL, issuer, and audience. API readiness must use `/v1/ready`; liveness must use `/v1/live`.

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
- [2026-04-28] Do not rsync to `/tank/repos/parallax` with `--delete` unless `.env` is excluded; GPU `make dev-up` requires the host-local env file.
- [2026-04-29] Do not grow `TimingRepository` with checkpoint/latency persistence logic directly. Keep checkpoint state, latency observation persistence, and feature-vector generation in cohesive helper/domain modules.
- [2026-05-03] Do not treat the broader Figma expansion pack as Parallax product scope. Use it for visual grammar only; keep Parallax screens temporal unless a canonical artifact or explicit product decision expands scope.
- [2026-05-03] Do not declare Figma work done from structural creation alone. Screenshot the result, inspect spacing/alignment/centering/clipping/overlap/text fit, and compare directly to canonical mockups before finalizing.
- [2026-05-04] Do not "fix" Temporal Home Figma density problems by reducing item count or making fewer/larger boxes. Preserve the canonical Today schema and fix allocation, lanes, spacing, and border/text clearance.
- [2026-05-04] Do not leave defective alternate Figma pages or point docs to a replacement while a user-linked page remains bad. Fix the actual linked page or delete the stale draft, then update the handoff source of truth.
- [2026-05-04] Do not validate Timescale continuous aggregates with current open-bucket sample data or inside an open transaction. Use closed historical buckets, explicit refresh windows, and autocommit around `refresh_continuous_aggregate()`.
- [2026-05-04] Do not point Kubernetes API readiness/liveness probes at the same dependency health endpoint. Readiness should prove dependency and migration readiness; liveness should prove only that the process is alive.
- [2026-05-05] Do not implement Figma/example scenarios as default Parallax runtime data. Activity names, notes, preflight text, checkpoint labels, people, and places in mockups/examples are fixtures unless entered by the user or returned by the backend.
- [2026-05-05] Do not trust `swift test` alone after adding iOS source files. Also update and verify `apps/ios/ParallaxNative.xcodeproj/project.pbxproj`, because Xcode simulator builds do not auto-include new Swift files.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
- [2026-04-27] Parallax storage policy is split into dataset bootstrap and permission-only application: `scripts/setup_gpu_node_storage.sh` creates/updates datasets and repo/venv paths; `scripts/apply_gpu_node_permissions.sh` reapplies runtime ownership/modes without touching datasets or Git state.
- [2026-04-27] Runtime service-write permissions use configurable numeric IDs with `10001:bgconley` as the default app/service owner and `999:999` as the provisional Postgres owner until the DB image is pinned.
- [2026-04-27] GPU-node dependency management follows the repository `uv.lock`: run `PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax uv sync --frozen --all-groups` from `/tank/repos/parallax`.
- [2026-04-27] Phase 0 Compose starts detached via `make dev-up`; use `make dev-logs` for logs and `make dev-down` for shutdown.
- [2026-04-27] API health readiness lives in `services/api/parallax_api/services/health.py`; route handlers stay thin and report Postgres/Redis dependency status without exposing raw connection details.
- [2026-04-27] Phase 0/1 hardening closed the actionable current-scope audit findings; remaining auth provider, full endpoint surface, backup/restore, performance, Temporal workflow, and production privacy-scrub work is deferred to the appropriate later phase or explicit release-hardening pass.
- [2026-04-28] Phase 2 uses synchronous baseline Activity Profile recomputation inside the API transaction path after review/discard because Temporal workflow implementation is a later-phase concern; the smoke test proves persisted spans, model-update decisions, and stats snapshots on the GPU node.
- [2026-04-28] Phase 3 baseline includes migrations `0011_capture_context_geospatial_sensor_fusion.sql` and `0014_timing_review_flags.sql` in the root migration stream. Optional PostGIS/Timescale context profiles remain excluded.
- [2026-04-29] Phase 5 derives checkpoint active spans from checkpoint event pairs linked to `checkpoint_run_id`; skipped checkpoints update run status but do not feed duration stats.
- [2026-04-29] Phase 5 feature vectors are generated by the workflow worker from reviewed timing data and current context-capture policy. Location/radio-disabled place vectors persist as not model-eligible with `context_disabled_by_policy`.
- [2026-05-03] Phase 8 UI design uses the expansion readiness pack for visual language only. The product deliverable remains Parallax's temporal subset, and non-temporal planner/task-management UI requires a canonical artifact or explicit product-scope decision before implementation.
- [2026-05-03] Phase 8 native UI/Figma implementation completed at `317308c` with the Phase 8 smoke, Swift tests, Xcode simulator build, and Python regression checks. Pause before Phase 9 unless the user explicitly starts it.
- [2026-05-04] Phase 8 Temporal Home Figma source is `118:2` / board `118:3`; `106:2` was deleted as a failed draft. `scripts/phase8_ui_contract.py` now enforces the active `118:3` board and screenshot evidence.
- [2026-05-04] Phase 9 optional-extension hardening adds root optional SQL profiles, Docker-backed extension smoke validation, k3s readiness manifests, and re-embedding/dual-read documentation without changing baseline source-of-truth semantics.
- [2026-05-05] Phase 9 app remediation is treated as a corrective app-wide implementation slice to satisfy earlier temporal-loop acceptance gates with dynamic activity, timing, context capture, review, profile, Ask, privacy, and sync behavior; it does not start Phase 10.
