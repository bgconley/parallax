# Phase 10 Temporal Home Interactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the temporal-focused Today/Temporal Home Figma screens and SwiftUI implementation interaction-complete.

**Architecture:** Phase 10 is an additive interaction and workflow handoff layer over the completed Phase 8/9 baseline. The machine-readable action map is canonical for the screen/action inventory; Swift and validation scripts must agree with it. Figma prototype wiring proves visual intent, while Swift tests prove route/workflow execution.

**Tech Stack:** Figma MCP, SwiftUI, Swift Testing, Python 3 validation scripts, canonical Parallax v1.3 OpenAPI/events/jobs contracts.

---

### Task 1: Artifact Pack And Contract

**Files:**
- Create: `docs/phase10_temporal_home_interactions/README.md`
- Create: `docs/phase10_temporal_home_interactions/action_map.md`
- Create: `docs/phase10_temporal_home_interactions/action_map.json`
- Create: `docs/phase10_temporal_home_interactions/figma_reactions_expected.json`
- Create: `docs/phase10_temporal_home_interactions/workflow_matrix.md`
- Create: `apps/ios/DesignHandoff/phase10_temporal_home_interactions.json`
- Create: `scripts/phase10_temporal_home_contract.py`

- [ ] Create the human and JSON action map for all selectable-looking elements on Figma nodes `118:9`, `118:104`, `118:199`, `118:294`, and `118:346`.
- [ ] Record every element as exactly one of `drawer`, `navigation`, `local_queue`, `api_workflow`, or `display_only`.
- [ ] Validate the map against Swift enum raw values and expected Figma prototype reactions.

### Task 2: Figma Prototype Wiring

**Files:**
- Modify: Figma file `OYOtLrgwZmqAqsURzYJBM9`
- Write evidence: `.phase10_evidence/screenshots/figma/`

- [ ] Add prototype reactions for page `118:2` and drawer board `85:3`.
- [ ] Export actual reaction metadata into `docs/phase10_temporal_home_interactions/figma_reactions_actual.json`.
- [ ] Capture refreshed screenshots for the five 118 screens and drawer board.

### Task 3: Swift Action Model And Temporal Home UI

**Files:**
- Create: `apps/ios/Sources/ParallaxApp/TemporalHomeModels.swift`
- Create: `apps/ios/Sources/ParallaxApp/TemporalHomeActionMap.swift`
- Create: `apps/ios/Sources/ParallaxApp/TemporalHomeViewModel.swift`
- Create: `apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift`
- Create: `apps/ios/Sources/ParallaxApp/TemporalHomeScreen.swift`
- Modify: `apps/ios/Sources/ParallaxApp/TodayScreen.swift`
- Modify: `apps/ios/Sources/ParallaxApp/ParallaxRootView.swift`
- Modify: `apps/ios/ParallaxNative.xcodeproj/project.pbxproj`

- [ ] Add a typed action enum whose raw values match `action_map.json`.
- [ ] Replace broad task-oriented Today content with the temporal 118 states.
- [ ] Ensure every visible SwiftUI `Button` has a real action route.

### Task 4: Workflow Execution

**Files:**
- Modify: `apps/ios/Sources/ParallaxApp/TimingSliceViewModel.swift`
- Modify: `apps/ios/Sources/ParallaxApp/Phase8DrawerModels.swift`
- Modify: `apps/ios/Sources/ParallaxApp/Phase8DrawerViews.swift`
- Modify: `apps/ios/Sources/ParallaxCore/ParallaxAPIClient.swift`

- [ ] Wire all Phase 8 nested drawer actions to explicit `Phase8DrawerAction` values.
- [ ] Add local queue/view-model methods for pause, skip, move, note, friction correction, ignored evidence, keep-note-only, checkpoint optional, start-from-step, retry sync, and temporal quick capture.
- [ ] Add canonical API request builders for temporal query, review flags, extracted-event confirm, and extracted-event correct.

### Task 5: Tests And Smokes

**Files:**
- Create: `apps/ios/Tests/ParallaxAppTests/TemporalHomeActionMapTests.swift`
- Create: `apps/ios/Tests/ParallaxAppTests/Phase8DrawerActionTests.swift`
- Modify: `apps/ios/Tests/ParallaxAppTests/TimingSliceViewModelTests.swift`
- Modify: `apps/ios/Tests/ParallaxCoreTests/APIClientTests.swift`
- Modify: `Makefile`

- [ ] Add action-map coverage tests for every `118` action id.
- [ ] Add drawer action tests proving no nested drawer button remains a no-op.
- [ ] Add API request-shape tests for Phase 10 canonical endpoints.
- [ ] Add `make phase10-smoke`.

### Task 6: Verification Gate

- [ ] Run `python3 scripts/phase10_temporal_home_contract.py`.
- [ ] Run `swift test --package-path apps/ios`.
- [ ] Run `xcodebuild -project apps/ios/ParallaxNative.xcodeproj -scheme ParallaxNative -destination 'generic/platform=iOS Simulator' -derivedDataPath apps/ios/DerivedData build`.
- [ ] Run `make phase10-smoke`.
- [ ] Run existing Phase 8 smoke to prove no regression.
- [ ] Run GPU backend smoke for affected canonical workflows before marking Phase 10 complete.
