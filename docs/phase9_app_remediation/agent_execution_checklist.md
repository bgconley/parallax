# Phase 9 App Remediation Agent Execution Checklist

Follow this checklist in order. Do not skip directly to UI edits.

## 0. Restore Context

- Read `AGENT_START_HERE.md`.
- Read the canonical docs and contracts listed in `README.md`.
- Re-read `docs/23_agentic_implementation_guardrails.md`.
- Re-read the directly affected OpenAPI schemas before changing DTOs or routes.
- Run `git status --short` and identify unrelated local files.

## 1. Establish Failing Tests

- Add source leak test for runtime Swift files.
- Add runtime config tests proving no default example activity/preflight exists.
- Add app store empty/create/select tests.
- Add dynamic timing lifecycle tests.
- Add dynamic quick capture/friction tests.
- Add Ask connected-mode request test.
- Add button-action inventory test.
- Run Swift tests and confirm the new tests fail for the current app.

## 2. Add Core DTO/API Support

- Add OpenAPI-aligned DTOs.
- Add missing API request builders.
- Add typed decode helpers.
- Update API client tests.
- Keep existing mutation-envelope behavior intact.

## 3. Build Runtime App Store

- Add app store and local app-state cache.
- Add activity cache/store if needed.
- Wire launch through app store.
- Remove `.liveDemo()` from default runtime paths.
- Keep demo factories only in preview/test fixtures.

## 4. Implement Activity Flow

- Empty state.
- Create activity.
- Select activity.
- Connected list/refresh.
- Offline local creation and sync-safe mapping.

## 5. Implement Timing Flow

- Dynamic launcher.
- Measurement mode selection.
- Start session.
- Pause/resume.
- Finish.
- Dynamic context capture.
- Dynamic friction capture.
- Dynamic checkpoint display and actions.

## 6. Implement Review Flow

- Dynamic review metrics.
- Review flags.
- Save useful.
- Mark unusual.
- Active-only/friction-only choices.
- Discard choices.
- Forgotten timer correction from real flag/user evidence only.

## 7. Implement Secondary Surfaces

- Activity Profile from profile endpoint.
- Ask About Time input, submit, answer/evidence display.
- Privacy policy surface.
- Offline/sync queue.

## 8. Replace Static Drawers

- Convert each drawer to projection/input driven.
- Remove demo UUID defaults.
- Require real selected entities for entity-specific decisions.
- Add empty states where data does not exist.

## 9. Run Local Gates

- `swift test`
- Xcode build.
- `uv run pytest -q`
- `uv run ruff check .`
- `make typecheck`
- `make validate`
- `make phase8-smoke`
- `make release-status`

## 10. Run GPU/Simulator UAT

- Commit and push.
- Pull on GPU node.
- Run backend phase smokes on GPU node.
- Launch clean simulator connected to GPU-node API.
- Execute dynamic UAT flow from `testing_uat_plan.md`.
- Save screenshots and backend evidence under `.phase9_evidence/`.

## 11. Completion Report

The final report must include:

- changed files;
- fixture strings removed from runtime;
- dynamic flow summary;
- local command results;
- GPU-node command results;
- simulator UAT evidence path;
- known residual risks, if any.
