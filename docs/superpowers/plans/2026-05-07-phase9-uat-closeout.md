# Phase 9 UAT Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Close the remaining Phase 9 UAT polish rows so the native Parallax app can be truthfully reported as meeting the current UAT requirements.

**Architecture:** Treat `docs/phase9_dynamic_app_uat_matrix.md` as the closeout ledger. Each open row must get fresh simulator evidence, any discovered defect must get a focused Swift/API regression test, and the matrix must not be marked complete until all P0 rows are `PASS` and P1 rows are either `PASS` or explicitly carried with rationale. Figma nodes `118:2` and `85:2` remain pixel-level design references only; runtime content must stay dynamic and temporal.

**Tech Stack:** SwiftUI, Swift Testing, Xcode simulator, `xcrun simctl`, `xcodebuild`, FastAPI/pytest through `uv`, GPU-node validation for backend/integration proof.

**Execution status (2026-05-07):** Completed. Closeout evidence lives in `.phase9_evidence/uat_closeout_20260507T032416Z/`. UAT-M01 through UAT-M09 are `PASS`; the only new defect found was `UAT-FINDING-027`, a Timing Review Dynamic Type hierarchy issue fixed in `TimingReviewEstimateLayout` and covered by `reviewEstimateSupportingCaptionStaysSubordinateAtAccessibilitySizes`.

---

## Scope Guard

- Do not introduce task-management, project-management, routine-builder, generic assistant/planning, or "break it down" product semantics.
- Do not hard-code Figma dummy content, example names, canned rows, sample activities, or mock workflow data.
- Do not treat unfinished frames on Figma node `118:2` as UAT requirements.
- Do not touch Phase 10+ product scope while closing Phase 9 polish rows.
- Leave `.phase11_evidence/` untracked unless the user explicitly opens Phase 11 work.

## Simulator Interaction Rule

- `PARALLAX_DEMO_DRAWER` only auto-opens `Phase8DrawerWorkflow` aliases: `step_detail`, `friction_evidence`, `forgotten_timer`, `review_decision`, `preflight_evidence`, and `checkpoint_setup`.
- Home-owned drawers are not `PARALLAX_DEMO_DRAWER` aliases. Open `temporal_navigation`, `ask_about_time`, `quick_capture`, and `sync_queue` through UI actions and accessibility identifiers.
- Prefer simulator UI taps by accessibility identifier where the app exposes one: `118_9_ask_time` opens Ask About Time, `118_9_quick_capture` opens Quick Capture, and `118_199_view_queue` opens the sync queue from the sync-pending Home surface. The current header menu button is labeled `Back`; if that label is corrected during implementation, use the visible top-left menu control.
- Any screenshot captured after an unsupported drawer alias is invalid evidence and must be recaptured.

## Files And Responsibilities

- `docs/phase9_dynamic_app_uat_matrix.md` - authoritative UAT checklist, finding rows, evidence links, and final status.
- `.phase9_evidence/uat_closeout_<timestamp>/` - new closeout screenshots and logs for this plan.
- `apps/ios/Sources/ParallaxApp/CanonicalComponents.swift` - shared screen shell, cards, badges, bottom-sheet constants, and static row accessory policy.
- `apps/ios/Sources/ParallaxApp/TemporalHomeScreen.swift` - Temporal Home cards, timeline rows, hit areas, quick capture, and current-state surfaces.
- `apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift` - home-owned Ask, navigation, sync, and quick-capture drawers.
- `apps/ios/Sources/ParallaxApp/TimingLauncherSheet.swift` - timing launcher bottom sheet, measurement mode rows, and primary/cancel actions.
- `apps/ios/Sources/ParallaxApp/ActivitySetupScreen.swift` - empty/new activity setup and long activity input presentation.
- `apps/ios/Sources/ParallaxApp/TimingReviewScreen.swift` - timing review surface and bottom-attached review dock.
- `apps/ios/Sources/ParallaxApp/Phase8DrawerViews.swift` - step detail, friction, forgotten timer, preflight, checkpoint setup, and review decision drawer family.
- `apps/ios/Sources/ParallaxApp/TimingSessionScreen.swift` - active whole-task and checkpointed timing presentation.
- `apps/ios/Sources/ParallaxApp/TimingSliceViewModel.swift` - projection copy/state used by UI screens.
- `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift` - focused presentation, routing, projection, and layout regressions.
- `apps/ios/Tests/ParallaxCoreTests/Phase9RemediationTests.swift` - source scans blocking fixture/example/task-management copy.
- `.wolf/OPENWOLF.md`, `.wolf/cerebrum.md`, `.wolf/memory.md`, `.wolf/buglog.json`, `.wolf/anatomy.md` - durable handoff and defect memory updates for every real defect.

## Task 1: Prepare The Closeout Run

**Files:**
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`
- Create: `.phase9_evidence/uat_closeout_<timestamp>/screenshots/`
- Create: `.phase9_evidence/uat_closeout_<timestamp>/logs/`

- [x] **Step 1: Confirm current branch and untracked exclusions**

Run:

```bash
git status -sb
git rev-parse --short HEAD
```

Expected:

```text
## codex/phase9-dynamic-app-remediation...origin/codex/phase9-dynamic-app-remediation
<current short SHA>
```

Record the printed SHA in the closeout notes. It is acceptable for `.phase11_evidence/` to remain untracked. Do not stage it.

- [x] **Step 2: Create an evidence root for this closeout**

Run:

```bash
export RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export CLOSEOUT_ROOT=.phase9_evidence/uat_closeout_${RUN_ID}
mkdir -p "$CLOSEOUT_ROOT/screenshots" "$CLOSEOUT_ROOT/logs"
printf '%s\n' "$CLOSEOUT_ROOT" | tee /tmp/parallax_phase9_closeout_root.txt
```

Expected: the printed path starts with `.phase9_evidence/uat_closeout_`.

- [x] **Step 3: Rebuild the iOS app once before screenshot work**

Run:

```bash
xcodebuild \
  -project apps/ios/ParallaxNative.xcodeproj \
  -scheme ParallaxNative \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath apps/ios/DerivedDataUAT \
  build
```

Expected: `** BUILD SUCCEEDED **`.

- [x] **Step 4: Install a clean simulator build**

Run:

```bash
xcrun simctl terminate booted com.bgc.parallax.native >/dev/null 2>&1 || true
xcrun simctl uninstall booted com.bgc.parallax.native >/dev/null 2>&1 || true
xcrun simctl install booted apps/ios/DerivedDataUAT/Build/Products/Debug-iphonesimulator/ParallaxNative.app
```

Expected: exit code 0.

## Task 2: Close UAT-M01 Canonical Screen Shell/Header

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/CanonicalComponents.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture normal-size shell screenshots**

Run one launch per state:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
for state in '' launcher session reviewed checkpoint_setup; do
  name=${state:-home}
  SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
  SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
  SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
  SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m01-shell \
  SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=71717171-7171-4171-8171-717171717171 \
  SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M01 dynamic temporal activity with a longer title' \
  SIMCTL_CHILD_PARALLAX_DEMO_STATE="$state" \
  xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
  sleep 3
  xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M01-${name}-shell.jpg" >/dev/null
done
```

Expected: five screenshots exist.

- [x] **Step 2: Inspect all M01 screenshots visually**

Open every `M01-*.jpg`. Pass criteria:

- Header title/subtitle are centered and not clipped by side icons or Dynamic Island.
- Back/menu/sparkle icons look intentional and proportional.
- Top spacing is consistent across Home, Launcher, Session, Review, and Checkpoint Setup.
- No raw identifiers, task-management copy, or Figma dummy examples appear.

- [x] **Step 3: Patch shared shell only if a defect is visible**

If a shell defect appears, patch the smallest shared constant or layout in `CanonicalComponents.swift`. Add or update a regression in `Phase9UATRegressionTests.swift` that asserts the relevant layout contract, for example:

```swift
@Test func canonicalScreenHeaderKeepsStableIconAndTitleLanes() {
    #expect(CanonicalHeaderLayout.sideIconLaneWidth >= 36)
    #expect(CanonicalHeaderLayout.titleMinimumScaleFactor >= 0.70)
    #expect(CanonicalHeaderLayout.subtitleLineLimit >= 2)
}
```

If `CanonicalHeaderLayout` does not exist, create it in `CanonicalComponents.swift` next to the other layout enums and wire the existing constants through it.

- [x] **Step 4: Verify M01**

Run:

```bash
swift test --package-path apps/ios --filter Phase9UATRegressionTests
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M01**

If the screenshots pass, change `UAT-M01` from `IN PROGRESS` to `PASS` and list the `M01-*.jpg` evidence. If a patch was needed, add a new `UAT-FINDING-027` row with root cause, fix, tests, and screenshots.

## Task 3: Close UAT-M02 Temporal Home Cards And Timeline Rows

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeScreen.swift`
- Modify if projection copy defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeViewModel.swift`
- Modify if drawer launch defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture Temporal Home state screenshots**

Capture the default Home state first:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m02-home \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=72727272-7272-4272-8272-727272727272 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M02 temporal home dynamic activity title' \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M02-home-default.jpg" >/dev/null
```

Open and capture Home-owned drawers through UI actions:

```text
Use the simulator UI tool:
1. Tap accessibility id `118_9_ask_time`; capture `M02-home-ask-drawer.jpg`.
2. Dismiss the drawer.
3. Tap the visible top-left menu control, currently accessibility label `Back`; capture `M02-home-temporal-navigation.jpg`.
4. Dismiss the drawer.
5. Tap accessibility id `118_9_quick_capture`.
6. Tap text field `What happened?`; type `M02 queued timing note`.
7. Tap `Save timing note`; wait for Home to show the sync-pending surface.
8. Tap accessibility id `118_199_view_queue`; capture `M02-home-sync-queue.jpg`.
```

Expected: default, temporal navigation, Ask, and sync queue screenshots exist and were captured from real UI actions rather than unsupported drawer env aliases.

- [x] **Step 2: Inspect Home visuals**

Pass criteria:

- Focus card and timeline rows use left title lanes and right badge/action lanes without overlap.
- Timeline row hit areas match the visual row width.
- Badges are readable and not dominant.
- Quick capture and bottom actions are balanced.
- Empty/default copy is temporal and dynamic.

- [x] **Step 3: Patch Home defects**

Patch only the specific row/card/drawer that fails. If the issue is row hit shape or lane allocation, add a regression similar to:

```swift
@Test func temporalHomeTimelineRowsReserveRightBadgeLane() {
    #expect(TemporalHomeRowLayout.rightLaneMinimumWidth >= 86)
    #expect(TemporalHomeRowLayout.titleMinimumScaleFactor >= 0.72)
    #expect(TemporalHomeRowLayout.fullRowContentShapeEnabled)
}
```

Create `TemporalHomeRowLayout` in `TemporalHomeScreen.swift` if needed.

- [x] **Step 4: Verify M02**

Run:

```bash
swift test --package-path apps/ios --filter 'TemporalHome|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M02**

Set `UAT-M02` to `PASS` only after the screenshots pass visual inspection and any new defect has a regression/finding row.

## Task 4: Close UAT-M04 Timing Launcher And Activity Setup

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TimingLauncherSheet.swift`
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/ActivitySetupScreen.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture launcher and setup screenshots**

Run:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m04-launcher \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=74747474-7474-4474-8474-747474747474 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M04 launcher dynamic activity with a deliberately long temporal title' \
SIMCTL_CHILD_PARALLAX_DEMO_STATE=launcher \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M04-launcher-long-name.jpg" >/dev/null

xcrun simctl uninstall booted com.bgc.parallax.native >/dev/null 2>&1 || true
xcrun simctl install booted apps/ios/DerivedDataUAT/Build/Products/Debug-iphonesimulator/ParallaxNative.app
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m04-empty \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M04-activity-setup-empty.jpg" >/dev/null
```

Expected: launcher long-name and empty activity setup screenshots exist.

- [x] **Step 2: Inspect launcher/setup visuals**

Pass criteria:

- Measurement options use consistent icon/radio/title/detail lanes.
- Primary and secondary launcher buttons have balanced height and text scale.
- Long activity names wrap or scale without clipping.
- Empty setup input and action do not look sparse or oversized.

- [x] **Step 3: Patch launcher/setup defects**

If a defect is visible, patch `TimingLauncherSheet.swift` or `ActivitySetupScreen.swift` and add a layout regression:

```swift
@Test func timingLauncherModeRowsKeepStableLanesForLongActivityNames() {
    #expect(TimingLauncherSheetLayout.modeIconLaneWidth >= 54)
    #expect(TimingLauncherSheetLayout.modeTitleLineLimit >= 1)
    #expect(TimingLauncherSheetLayout.activityTitleLineLimit >= 2)
}
```

- [x] **Step 4: Verify M04**

Run:

```bash
swift test --package-path apps/ios --filter 'launcher|Activity|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M04**

Set `UAT-M04` to `PASS` with the new screenshot names only after visual inspection passes.

## Task 5: Close UAT-M05 Timing Review And Review Decision Drawer

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TimingReviewScreen.swift`
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/Phase8DrawerViews.swift`
- Modify if copy defects are found: `apps/ios/Sources/ParallaxApp/TimingSliceViewModel.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture review state and review drawer**

Run:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m05-review \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=75757575-7575-4575-8575-757575757575 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M05 review dynamic temporal activity' \
SIMCTL_CHILD_PARALLAX_DEMO_STATE=reviewed \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M05-review-screen.jpg" >/dev/null

SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m05-review-drawer \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=75757575-7575-4575-8575-757575757575 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M05 review dynamic temporal activity' \
SIMCTL_CHILD_PARALLAX_DEMO_STATE=reviewed \
SIMCTL_CHILD_PARALLAX_DEMO_DRAWER=review_decision \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M05-review-decision-drawer.jpg" >/dev/null
```

Expected: review screen and decision drawer screenshots exist.

- [x] **Step 2: Inspect review visuals**

Pass criteria:

- Summary values are user-facing and not raw canonical identifiers.
- Decision options fit without clipping at normal size.
- Bottom review dock remains attached and balanced.
- Save/discard actions have consistent hierarchy.

- [x] **Step 3: Patch review defects**

If any defect appears, add or update projection/layout tests:

```swift
@Test func reviewDecisionDrawerRowsHaveEnoughVerticalSpaceForAllChoices() {
    #expect(ReviewDecisionDrawerLayout.optionMinimumHeight >= 58)
    #expect(ReviewDecisionDrawerLayout.optionDetailLineLimit >= 2)
}
```

Create `ReviewDecisionDrawerLayout` in `Phase8DrawerViews.swift` if needed.

- [x] **Step 4: Verify M05**

Run:

```bash
swift test --package-path apps/ios --filter 'review|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M05**

Set `UAT-M05` to `PASS` after screenshot inspection and regression coverage for any new defect.

## Task 6: Close UAT-M06 Phase 8 Drawer Family

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/Phase8DrawerViews.swift`
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift`
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/CanonicalComponents.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture each drawer family**

Run:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
while read -r state drawer; do
  SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
  SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
  SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
  SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m06-drawers \
  SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=76767676-7676-4676-8676-767676767676 \
  SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M06 drawer family dynamic activity' \
  SIMCTL_CHILD_PARALLAX_DEMO_STATE="$state" \
  SIMCTL_CHILD_PARALLAX_DEMO_DRAWER="$drawer" \
  xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
  sleep 3
  xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M06-${drawer}.jpg" >/dev/null
done <<'EOF'
session step_detail
session friction_evidence
reviewed forgotten_timer
reviewed review_decision
default preflight_evidence
checkpoint_setup checkpoint_setup
EOF
```

Expected: one screenshot per Phase 8 drawer workflow. Capture `temporal_navigation`, `ask_about_time`, and `sync_queue` through the Home UI action steps in Task 3 and Task 8; do not use them as `PARALLAX_DEMO_DRAWER` values.

- [x] **Step 2: Inspect drawer family**

Pass criteria:

- Titles and subtitles fit.
- Nested actions are readable and have consistent heights.
- Disabled actions are readable but visually disabled.
- Terminal actions do not show drill-in chevrons.
- Content scrolls instead of clipping.
- Bottom sheet is attached where the design calls for a pull-up drawer.

- [x] **Step 3: Patch shared drawer defects first**

If multiple drawers share the defect, patch shared shell constants in `Phase8DrawerViews.swift`, `TemporalHomeDrawers.swift`, or `CanonicalComponents.swift`. Add a regression:

```swift
@Test func phase8DrawerFamilyKeepsScrollableContentAndReadableActions() {
    #expect(Phase8DrawerLayout.minimumActionHeight >= 54)
    #expect(Phase8DrawerLayout.contentBottomPadding >= 24)
    #expect(Phase8DrawerLayout.accessibilityHeightExpansionEnabled)
}
```

- [x] **Step 4: Verify M06**

Run:

```bash
swift test --package-path apps/ios --filter 'drawer|Phase8|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M06**

Set `UAT-M06` to `PASS` after all drawer screenshots pass visual inspection.

## Task 7: Close UAT-M07 Active Checkpointed Timing

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TimingSessionScreen.swift`
- Modify if projection defects are found: `apps/ios/Sources/ParallaxApp/TimingSliceViewModel.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/TimingSliceViewModelTests.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Start an active checkpointed run from the launcher**

Use simulator tapping rather than direct `session` launch:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m07-checkpointed \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=77777777-7777-4777-8777-777777777777 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M07 checkpointed dynamic activity' \
SIMCTL_CHILD_PARALLAX_DEMO_STATE=launcher \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
```

Then tap `Checkpointed timing` and `Start timing` using the simulator UI tool or manual simulator tap if accessibility labels are unavailable. Capture:

```bash
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M07-active-checkpointed-run.jpg" >/dev/null
```

- [x] **Step 2: Exercise checkpoint actions**

Tap `Complete checkpoint`, `Skip`, `Move`, and `Note` where available on the active checkpointed screen. Capture after each action:

```bash
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M07-checkpoint-action-state.jpg" >/dev/null
```

Expected: checkpoint state advances or clearly explains disabled/unavailable state without crowding.

- [x] **Step 3: Patch checkpoint timing defects**

If the active checkpointed state has cramped rows, tiny chips, wrong labels, or stale "step" language, patch `TimingSessionScreen.swift` or `TimingSliceViewModel.swift`. Add a regression:

```swift
@MainActor
@Test func activeCheckpointedTimingProjectionUsesCheckpointLanguageAndStableRows() async throws {
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "57575757-5757-4757-8757-575757575757")!,
        activityName: "Checkpointed language activity",
        deviceId: "ios-uat-checkpoint-language",
        eventStore: InMemoryPendingTimingEventStore()
    )
    await timing.startRun(mode: .checkpointed)
    #expect(timing.measurementMode == .checkpointed)
    #expect(timing.stepDetail.eyebrow.localizedCaseInsensitiveContains("checkpoint"))
    #expect(!timing.stepDetail.eyebrow.localizedCaseInsensitiveContains("step"))
}
```

Use this existing `TimingSliceViewModel` initializer shape rather than introducing a new convenience initializer.

- [x] **Step 4: Verify M07**

Run:

```bash
swift test --package-path apps/ios --filter 'checkpoint|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M07**

Set `UAT-M07` to `PASS` if active checkpointed screenshots pass. If a P1 issue remains, carry it explicitly with a named follow-up and rationale instead of leaving `IN PROGRESS`.

## Task 8: Close UAT-M08 Offline, Sync, And Error States

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeScreen.swift`
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/TemporalHomeDrawers.swift`
- Modify if projection defects are found: `apps/ios/Sources/ParallaxApp/TimingSliceViewModel.swift`
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Test: `apps/ios/Tests/ParallaxCoreTests/PendingSyncServiceTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture API-unavailable Ask and sync queue states**

Launch Home with the API unavailable:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
SIMCTL_CHILD_PARALLAX_API_BASE_URL=http://127.0.0.1:1 \
SIMCTL_CHILD_PARALLAX_AUTH_MODE=dev_header \
SIMCTL_CHILD_PARALLAX_DEV_USER_ID=11111111-1111-4111-8111-111111111111 \
SIMCTL_CHILD_PARALLAX_DEVICE_ID=ios-uat-m08-offline \
SIMCTL_CHILD_PARALLAX_ACTIVITY_ID=78787878-7878-4878-8878-787878787878 \
SIMCTL_CHILD_PARALLAX_ACTIVITY_NAME='M08 offline dynamic activity' \
xcrun simctl launch --terminate-running-process booted com.bgc.parallax.native >/dev/null
sleep 3
```

Use the simulator UI tool:

```text
1. Tap accessibility id `118_9_ask_time`; capture `M08-api-unavailable-ask.jpg`.
2. Dismiss the Ask drawer.
3. Tap accessibility id `118_9_quick_capture`.
4. Tap text field `What happened?`; type `M08 queued offline timing note`.
5. Tap `Save timing note`; wait for the sync-pending Home surface.
6. Capture `M08-sync-pending-home.jpg`.
7. Tap accessibility id `118_199_view_queue`.
```

Then capture the sync queue:

```bash
xcrun simctl io booted screenshot --type=jpeg "$CLOSEOUT_ROOT/screenshots/M08-sync-queue.jpg" >/dev/null
```

- [x] **Step 2: Inspect offline/error states**

Pass criteria:

- Copy says pending changes, queued questions, retry, or backend unavailable in human language.
- Retry controls are visible but not visually louder than the actual state.
- Icons and badges are proportionate.
- No internal `mutation`, snake_case, raw enum, or transport error dumps appear.

- [x] **Step 3: Patch offline/sync defects**

Patch projection copy in `TimingSliceViewModel.swift` or row/drawer layout in `TemporalHomeScreen.swift` / `TemporalHomeDrawers.swift`. Add a regression:

```swift
@MainActor
@Test func offlineAndSyncCopyDoesNotExposeTransportOrMutationInternals() async throws {
    let store = InMemoryPendingTimingEventStore()
    let timing = TimingSliceViewModel(
        activityId: UUID(uuidString: "58585858-5858-4858-8858-585858585858")!,
        activityName: "Offline sync copy activity",
        deviceId: "ios-uat-offline-copy",
        eventStore: store
    )
    await timing.startRun()
    let visibleCopy = timing.pendingSyncRows.map { "\($0.title) \($0.detail)" }.joined(separator: " ")
    let banned = ["mutation", "URLSession", "NSURLError", "session_started", "resource_detour_started"]
    for phrase in banned {
        #expect(!visibleCopy.localizedCaseInsensitiveContains(phrase))
    }
}
```

Use the current `pendingSyncRows` projection rather than inventing a new `SyncQueueProjection` type.

- [x] **Step 4: Verify M08**

Run:

```bash
swift test --package-path apps/ios --filter 'sync|offline|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M08**

Set `UAT-M08` to `PASS` if screenshots pass. If a P1 item remains, carry it with explicit rationale and linked evidence.

## Task 9: Close UAT-M09 Accessibility And Dynamic Type

**Files:**
- Modify if defects are found: `apps/ios/Sources/ParallaxApp/CanonicalComponents.swift`
- Modify if defects are found: affected SwiftUI screen or drawer files
- Test: `apps/ios/Tests/ParallaxAppTests/Phase9UATRegressionTests.swift`
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`

- [x] **Step 1: Capture accessibility-size screenshots for remaining families**

Set the simulator to an accessibility content-size category:

```bash
xcrun simctl ui booted content_size accessibility-extra-extra-extra-large
```

Capture:

- Home default
- Timing launcher
- Review screen
- Review decision drawer
- Checkpoint setup
- Ask drawer
- Sync queue drawer
- Active checkpointed timing

Name screenshots:

```text
M09-dynamic-type-home.jpg
M09-dynamic-type-launcher.jpg
M09-dynamic-type-review.jpg
M09-dynamic-type-review-drawer.jpg
M09-dynamic-type-checkpoint-setup.jpg
M09-dynamic-type-ask.jpg
M09-dynamic-type-sync-queue.jpg
M09-dynamic-type-checkpointed-session.jpg
```

Use the launch commands and UI action paths from Tasks 3 through 8 to reach each state. Restore the simulator after the screenshots:

```bash
xcrun simctl ui booted content_size large
```

- [x] **Step 2: Inspect Dynamic Type screenshots**

Pass criteria:

- Content scrolls rather than clipping.
- Button labels fit or wrap intentionally.
- Decorative icons remain fixed/proportional.
- Small captions remain logically small but readable.
- Large headings do not crowd side controls.

- [x] **Step 3: Patch Dynamic Type defects**

Patch the specific screen first. If multiple screens fail the same way, patch shared constants in `CanonicalComponents.swift` or drawer shells. Add a regression:

```swift
@Test func dynamicTypeDrawerLayoutAllowsContentToScrollBeforeClippingActions() {
    #expect(Phase8DrawerLayout.accessibilityHeightExpansionEnabled)
    #expect(Phase8DrawerLayout.contentBottomPadding >= 24)
    #expect(Phase8DrawerLayout.closeButtonFixedSize)
}
```

Use existing layout enums where possible.

- [x] **Step 4: Verify M09**

Run:

```bash
swift test --package-path apps/ios --filter 'Dynamic|accessibility|Phase9UATRegressionTests'
```

Expected: all filtered tests pass.

- [x] **Step 5: Update UAT-M09**

Set `UAT-M09` to `PASS` if screenshots pass. If a P1 accessibility case remains because of a simulator/tooling limitation, carry it explicitly with the exact limitation and next manual verification path.

## Task 10: Run Full Verification And GPU-Node Validation

**Files:**
- Modify: `docs/phase9_dynamic_app_uat_matrix.md`
- Modify: `docs/superpowers/plans/2026-05-07-phase9-uat-closeout.md`
- Modify: `.wolf/memory.md`
- Modify if new bugs were found: `.wolf/buglog.json`
- Modify if new evidence folders were created: `.wolf/anatomy.md`

- [x] **Step 1: Run full local iOS tests**

Run:

```bash
swift test --package-path apps/ios
```

Expected: `Test run with 96 tests` or higher, all passed.

- [x] **Step 2: Run Xcode simulator build**

Run:

```bash
xcodebuild \
  -project apps/ios/ParallaxNative.xcodeproj \
  -scheme ParallaxNative \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath apps/ios/DerivedDataUAT \
  build
```

Expected: `** BUILD SUCCEEDED **`.

- [x] **Step 3: Run targeted local API regressions**

Run:

```bash
uv run pytest \
  services/api/tests/test_timing_sessions.py \
  services/api/tests/test_phase2_review_profile.py \
  services/api/tests/test_phase3_context_capture.py \
  -q
```

Expected: all tests pass.

- [x] **Step 4: Validate matrix has no open P0 rows**

Run:

```bash
if rg -n '^\| UAT-M0[12456] \|.*\| (IN PROGRESS|PENDING|FAIL|BLOCKED) \|' docs/phase9_dynamic_app_uat_matrix.md; then
  exit 1
fi
```

Expected: no matches and exit code 0 from the `if` block. `UAT-M03` is already `PASS`; this command checks the remaining P0 rows.

- [x] **Step 5: Validate source-copy guards**

Run:

```bash
rg -n "Break it down|first step|step plan|Steps in order|Start first step|Show all steps|Done with this step|Step breakdown|Routine run|Learning how this workflow|Routine timing|Split into smaller steps|Start from this step|step changes|active step|No active timing step|What this step|Waiting step detail|task list" apps/ios/Sources/ParallaxApp apps/ios/Sources/ParallaxCore -g '*.swift'
```

Expected: exit code 1 with no matches.

- [x] **Step 6: Run GPU-node backend validation**

Run from the Mac:

```bash
CLOSEOUT_ROOT=$(cat /tmp/parallax_phase9_closeout_root.txt)
ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 \
  'cd /tank/repos/parallax && \
   git fetch origin codex/phase9-dynamic-app-remediation && \
   git checkout codex/phase9-dynamic-app-remediation && \
   git pull --ff-only && \
   PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax \
   uv run pytest services/api/tests/test_timing_sessions.py services/api/tests/test_phase2_review_profile.py services/api/tests/test_phase3_context_capture.py -q' \
  | tee "$CLOSEOUT_ROOT/logs/gpu-node-api-regressions.txt"
```

Expected: all GPU-node tests pass and the command output is recorded under `$CLOSEOUT_ROOT/logs/gpu-node-api-regressions.txt`.

- [x] **Step 7: Update OpenWolf closeout memory**

Append a concise `.wolf/memory.md` row recording:

- which `UAT-M*` rows were closed,
- evidence root,
- local test counts,
- GPU-node test result,
- any P1 rows carried with rationale.

If any defect was fixed, add a `.wolf/buglog.json` entry with root cause, fix, validation, and screenshots.

- [x] **Step 8: Commit and push closeout**

Run:

```bash
git status --short
git add docs/phase9_dynamic_app_uat_matrix.md docs/superpowers/plans/2026-05-07-phase9-uat-closeout.md .phase9_evidence .wolf/OPENWOLF.md .wolf/cerebrum.md .wolf/memory.md .wolf/buglog.json .wolf/anatomy.md apps/ios/Sources apps/ios/Tests services/api services/api/tests
git status --short
if git diff --cached --name-only | rg '^\.phase11_evidence/'; then
  echo '.phase11_evidence must not be staged for Phase 9 closeout'
  exit 1
fi
git commit -m "Close Phase 9 UAT polish matrix"
git push -u origin codex/phase9-dynamic-app-remediation
```

Expected: push succeeds. `.phase11_evidence/` remains unstaged unless explicitly scoped by the user.

## Definition Of Done

- `UAT-M01`, `UAT-M02`, `UAT-M04`, `UAT-M05`, and `UAT-M06` are `PASS`.
- `UAT-M07`, `UAT-M08`, and `UAT-M09` are `PASS` or explicitly carried with evidence-backed rationale.
- No UAT P0 row remains `IN PROGRESS`, `PENDING`, `FAIL`, or `BLOCKED`.
- Every newly discovered defect has a `UAT-FINDING-*` row, a regression test, and simulator evidence.
- Every P0 screen family has fresh simulator screenshots under the closeout evidence root.
- Backend/API regressions pass locally and on the GPU node.
- `swift test --package-path apps/ios` and the Xcode simulator build pass.
- OpenWolf memory and anatomy reference the final closeout evidence.
