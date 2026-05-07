# Repository Guidelines

## Project Structure & Module Organization

This checkout contains the Parallax v1.3 artifact pack plus the Phase 0-9 implementation work. Do not advance Phase 10 or later unless the user explicitly starts that phase. The canonical artifact source remains `parallax_v1_3_artifact_pack/`; keep the zip archive in sync only when intentionally rebuilding it. Start with `README.md` and `parallax_v1_3_artifact_pack/AGENT_START_HERE.md`.

Before making implementation or infrastructure decisions, read the relevant canonical artifact files first. Do not infer Parallax layout, storage, runtime, or service policy from existing GPU-node directories or other apps when a Parallax artifact covers the topic.

After any context compaction, resume, or session transition, re-read the canonical project docs before making code or infrastructure changes. For Phase 9 app remediation or any broad app behavior work, re-read this minimum set in order: `parallax_v1_3_artifact_pack/AGENT_START_HERE.md`, `parallax_v1_3_artifact_pack/docs/01_app_system_spec.md`, `parallax_v1_3_artifact_pack/docs/02_temporal_domain_model.md`, the relevant section of `parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md`, `parallax_v1_3_artifact_pack/database/README.md`, directly affected OpenAPI/event/job contracts, `parallax_v1_3_artifact_pack/docs/23_agentic_implementation_guardrails.md`, and `parallax_v1_3_artifact_pack/docs/12_testing_qa_release_rollback.md`.

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
- `make typecheck`: runs the static type baseline.
- `make validate`: validates the canonical artifact pack and local contract helper.
- `make security`: runs the Bandit and Semgrep security/static-analysis gate.
- `python3 parallax_v1_3_artifact_pack/scripts/validate_pack.py --zip-path parallax_v1_3_artifact_pack.zip`: validates artifact directory and archive parity.
- `bash -n scripts/setup_gpu_node_storage.sh scripts/apply_gpu_node_permissions.sh`: checks GPU-node shell scripts.
- `make dev-up`: starts the Docker Compose stack detached.
- `make dev-down`: stops the Docker Compose stack.
- `make dev-logs`: tails Compose logs.
- `make schema-smoke`: applies baseline migrations through the host-side Postgres port and runs schema smoke checks.
- `make phase1-smoke`: runs the Phase 1 API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase2-smoke`: runs the Phase 2 review/profile API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase3-smoke`: runs the Phase 3 context capture API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase4-smoke`: runs the Phase 4 extraction/correction/place-inference API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase5-smoke`: runs the Phase 5 checkpoints/latency/feature-vector API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase6-smoke`: runs the Phase 6 activity-identity/preflight API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase7-smoke`: runs the Phase 7 grounded Ask About Time API/Postgres acceptance smoke against the configured API and host database URL.
- `make phase8-smoke`: validates the Phase 8 repo-side design handoff and SwiftUI view-model contract tests on the Mac.
- `make phase9-smoke`: runs the Phase 9 optional-extension smoke against isolated Docker databases for pgvector, ParadeDB, PostGIS, and Timescale, and statically checks k3s readiness manifests.
- `make release-status`: prints the current full-release gate blockers without failing.
- `make release-gate`: fails while full-release/private-alpha blockers in `docs/release/release_gate_status.md` remain open.

## Coding Style & Naming Conventions

Use `Parallax` for product copy, `parallax` for packages/services/databases, and `PARALLAX_` for environment variables. Preserve canonical contract names and enums; do not introduce retired placeholders. Python code should target Python 3.12+, FastAPI, Pydantic v2, Alembic, Ruff, and pytest. Keep optional profiles under `database/optional_profiles/`.

## Testing Guidelines

Use `docs/12_testing_qa_release_rollback.md` as the test authority. Seed timing semantics from `tests_or_eval/temporal_semantics_test_matrix.csv`; use JSONL files in `tests_or_eval/` for LLM/retrieval evaluation. Contract changes must update OpenAPI, JSON Schema, examples, docs, and tests together.

## Phase 8 UI/UX Scope Guard

For Parallax, `figma_expansion_readiness_pack_v0_8_1/` is a design-language reference only: native iOS grammar, spacing, typography, card/chip patterns, accessibility posture, interaction tone, and Liquid Glass treatment. It is not product-scope authority.

Active Parallax UI scope is temporal: timing sessions, timing launcher/calibration, timing review/correction, checkpointed timing only as temporal instrumentation, temporal home/current focus, offline/sync/AI-pending/needs-review/high-contrast/Dynamic Type/reduced-motion states for those workflows, and grounded temporal answers only where Phase 7 supports them.

Do not pull in broad task/project management, generic inbox/task-tracker flows, routine builders, broad weekly reviews, broad personalization/settings, "break it down" task decomposition, step-planning language, or unrelated assistant/planning workflows just because they are visible in the expansion pack or in Figma. Any non-temporal UI surface needs a canonical artifact or explicit product decision before implementation.

Active Figma visual targets must be source-backed or canonical-derived from `parallax_v1_3_artifact_pack/examples/` and the current canonical Figma reference pages. Current canonical visual references include `https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9/Parallax---v1.3-Native-Screens?node-id=118-2` and `https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9/Parallax---v1.3-Native-Screens?node-id=85-2`. Treat these Figma frames as pixel-level design authority only: layout, spacing, typography, component proportions, visual hierarchy, and interaction affordances. Do not hard-code their dummy/example content, user names, activity names, canned rows, task/project concepts, or mock workflow examples into runtime code. Runtime content and behavior must stay dynamic and come from canonical Parallax workflows, local state, user-entered data, and API/view-model projections. Node `118:2` is a mixed board that includes unfinished mocks, hotspots, and Phase 10 target material; use only complete canonical frames such as board `118:3` for current Phase 9 visual alignment unless the user explicitly opens later scope.

Simplified vector drafts are not finished mockups. Before treating Figma work as complete, capture screenshots of the new work, inspect for alignment, spacing, centering, clipping, overlap, cramped boundaries, and text fit, then compare directly against the canonical mockups.

Current active Temporal Home Figma target is `10 Phase 8 Temporal Home Canonical Allocation` at `https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9/Parallax---v1.3-Native-Screens?node-id=118-2`; the active implementation board is node `118:3`. The earlier `106:2` temporal scope draft was deleted after QA found unacceptable cramped text, lane collisions, and overlap risk.

For this target, preserve the canonical Today schema and density: header, current focus, intelligence card, timeline/list block, quick capture, and bottom action pair. Do not fix visual defects by reducing item count, removing canonical sections, or making oversized empty text boxes. Fix defects by reallocating lanes and positions: reserve right-side badge/action lanes, left-side title/meta lanes, progress/caption lanes, and drawer content lanes so objects do not overlap, clip, or crowd borders.

## Current Phase 9 UAT Polish Handoff

As of May 6, 2026, the Timing Session bottom pull-up drawer/dock defect has been fixed and simulator-verified, but the broader full-app Phase 9 polish audit remains active. Do not mark completion from `PQ15-timing-session-card-polish.jpg`, `PQ16-timing-session-anchored-dock-and-secondary-buttons.jpg`, `PQ29-timing-session-bottom-drawer-attached-v2.jpg`, or `PQ30-dynamic-type-timing-session-bottom-drawer-attached-v2.jpg`; those screenshots are rejected/intermediate because the drawer either crowded the preceding card or still ended above the physical bottom edge.

Accepted current state: `apps/ios/Sources/ParallaxApp/TimingSessionScreen.swift` uses a `ZStack(alignment: .bottom)` overlay for `bottomActionDock`, reserves scroll space behind the dock, ignores the bottom container safe area, extends the sheet fill through the safe area, and offsets the dock downward by the safe-area extension so it reads as an attached bottom drawer. The shared flat-bottom sheet shape lives in `CanonicalComponents.swift` and is used by Timing Session, Timing Review, Timing Launcher, and Phase 8 drawer overlays. Timing Review uses the same attached overlay pattern via `TimingReviewDockLayout`. Terminal drawer rows such as `Close` and `Cancel` no longer show drill-in chevrons.

Accepted evidence: `.phase9_evidence/presentation_quality_20260506T174000Z/screenshots/PQ31-dynamic-type-timing-session-bottom-drawer-attached-v3.jpg`, `.phase9_evidence/presentation_quality_20260506T174000Z/screenshots/PQ32-timing-session-bottom-drawer-attached-v3.jpg`, `.phase9_evidence/presentation_quality_20260506T174000Z/screenshots/PQ33-review-bottom-drawer-attached-v2.jpg`, `.phase9_evidence/presentation_quality_20260506T174000Z/screenshots/PQ36-temporal-navigation-terminal-chevron-fixed.jpg`, and `.phase9_evidence/presentation_quality_20260506T174000Z/screenshots/PQ37-ask-drawer-terminal-chevron-fixed.jpg`. Pixel inspection confirmed the Timing Session sheet spans to the physical bottom edge in the accepted `v3` screenshots.

## Environment Routing

Unit tests may run locally on the Mac. Run all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations on the GPU node, because that is the deployment host. Keep frontend testing, Xcode and SwiftUI work, initial Figma work, and Playwright-based UI validation on the Mac.

Access the GPU node with `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.

For GPU-node storage, start from `parallax_v1_3_artifact_pack/infrastructure/zfs/zfs_dataset_plan.md` and `create_parallax_datasets.sh`. Use the `parallax` ZFS namespace and `/srv/parallax` mountpoints from the artifact; pass the actual pool name to the script.

Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. `tank/venvs` is currently root ext4 on this host, not ZFS; that is expected and accepted. After pushing from the Mac, pull updates into `/tank/repos/parallax`.

If you need to rsync an uncommitted working tree to the GPU node for validation, exclude `.env`, `.git`, `.venv`, `.DS_Store`, and `__pycache__` so host-local runtime configuration is not deleted.

Use `uv` for the Parallax app environment on the GPU node. `uv` is available at `/home/bgconley/.local/bin/uv`, but non-interactive SSH sessions may not include `~/.local/bin` on `PATH`. Run GPU-node checks with `PATH=/home/bgconley/.local/bin:$PATH` and `UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax` so `uv` uses the accepted venv path and does not create `/tank/repos/parallax/.venv`.

GPU-node runtime storage is verified under `tank/parallax` mounted at `/srv/parallax`. Apply permissions with `scripts/apply_gpu_node_permissions.sh` after datasets exist. Remote sudo commands need a TTY, for example `ssh -tt -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 'sudo -v && sudo /tmp/apply_gpu_node_permissions.sh'`.

Current permission policy: `/srv/parallax` is `root:root 0755`; Postgres and WAL are numeric `999:999 0700`; service-writable objects/exports/models/cache/logs are `10001:bgconley 0770`; config and observability are `bgconley:bgconley 0755`; backups are `root:bgconley 0750`. Host names for UID/GID `999` may display as unrelated local accounts; verify numeric IDs against the pinned container image when the DB image is finalized.

Phase work must be explicit. Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, and Phase 9 are complete. Do not start Phase 10 or broaden later work unless the user directly instructs you to begin that scope. The current runtime API exposes the canonical v1.3 method/path surface, but later-phase endpoints are baseline implementations until their owning phase receives explicit product-depth work.

The Phase 0 runtime uses Parallax-specific localhost ports to coexist with other GPU-node stacks: API `18000`, Postgres `15432`, Redis `16379`, Temporal `17233`, Temporal UI `18088`, MinIO `19000/19001`, and Caddy `18080/18443`. Container-to-container URLs still use service names such as `postgres:5432` and `redis:6379`.

Development/test API auth may use `X-Parallax-User-Id`; missing or malformed values must fail with a structured 401. Do not reintroduce an implicit development user fallback.

## Release Hardening Notes

Keep these distinctions visible during later work:

- `dev_header` remains development/test only. Production uses `external_bearer` with issuer/audience-bound JWT verification and JWKS support.
- Full route coverage does not mean every later-phase endpoint has mature product behavior; later phases still own deeper UX/model/analytics expansion.
- Release readiness is proof-based, not status-text based. `make release-gate` must run the commit-parity, bearer-auth provider, SLO, privacy-log, and real backup/restore proof commands; without live provider evidence the release status remains blocked.
- Context, extraction, place-inference, privacy, and feature-vector workflows now have durable `workflow_run` records; replacing the lightweight worker with a Temporal SDK implementation must preserve the same workflow names and idempotency behavior.

`docs/release/release_gate_evidence.json` is the machine-readable release status
source. `docs/release/release_gate_status.md` explains the gates for humans.

## Commit & Pull Request Guidelines

Use concise imperative commits, for example `Add timing session contract tests`. PRs should describe the artifact or implementation change, link the issue or ADR, list validation commands run, and include screenshots for UI/mockup changes.

## Security & Configuration Tips

Treat raw notes, transcripts, audio, embeddings, timing patterns, and context observations as privacy-sensitive. Do not log raw sensitive payloads. Every mutating API endpoint must carry a mutation envelope; resolver POST endpoints must remain read-only.
