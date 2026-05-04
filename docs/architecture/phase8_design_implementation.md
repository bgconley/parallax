# Phase 8 Design Implementation

Phase 8 adds the repo-side native UI boundary for Parallax without changing
backend contracts.

## Scope

- `apps/ios/` is a Swift Package containing design tokens, canonical UI
  projections, offline pending-event persistence, API request construction, and
  SwiftUI P0 screens.
- `apps/ios/DesignHandoff/phase8_figma_handoff.json` is the code-ready frame and
  component inventory for the created Figma file.
- `scripts/phase8_ui_contract.py` validates the handoff inventory against the
  canonical design-token version, required surfaces, required states, component
  inventory, examples, Figma evidence, and UI projection coverage.

## Boundaries

The UI package treats backend/domain enums as canonical and maps them to display
states. It does not introduce competing timing, count-policy, review, capture, or
workflow states.

The package is intentionally separate from `services/api/` so UI concerns do not
enter routes, repositories, services, or database modules.

## Figma Status

The Phase 8 Figma file exists and contains the Parallax temporal UI kit,
canonical/expansion references, a core timing loop prototype, P0 screen/state
frames, and accessibility/offline stress frames:

```text
https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9
```

The file imports the canonical reference mockups and UI payload examples from
`parallax_v1_3_artifact_pack/examples/`. It also imports
`figma_expansion_readiness_pack_v0_8_1/` as design-language grammar only. That
pack covers a larger task application, so the implementation keeps the visual
language but constrains actual Parallax frames to temporal tracking.

The Figma cleanup pass corrected cramped header lanes, dynamic type wrapping,
and component-card title overflow. The handoff metadata records the verified
nodes and the zero-issue overlap audit.

The core-flow board was then rebuilt from the canonical reference mockup images
themselves. Those five source-backed components are now the finished visual
targets; the earlier simplified vector drafts live on a superseded page.

The P0 and stress-state pages follow the same rule. They use canonical-derived
state cards with the reference mockup preserved as the visual substrate and
state-specific behavior documented in the card rail.

The drawer workflow board is the source for second-level Phase 8 bottom sheets:

```text
https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9/Parallax---v1.3-Native-Screens?node-id=85-3
```

It defines six implementation targets: step detail, friction evidence
confirmation, forgotten-timer review, model-inclusion review decision,
preflight evidence lifecycle, and checkpoint setup expansion. The SwiftUI
implementation uses custom bottom overlays for these drawers rather than native
generic sheets so the dimmed context, top handle, card lanes, chip rows, and
action geometry follow the Figma artifact closely.

The runnable iOS app target is:

```text
apps/ios/ParallaxNative.xcodeproj
scheme: ParallaxNative
bundle id: com.bgc.parallax.native
```

The app target stays thin and imports the package modules:

- `ParallaxDesignSystem`
- `ParallaxCore`
- `ParallaxApp`

The Phase 8 drawer implementation lives in `ParallaxApp` display/view-model
code. API request construction and canonical enums remain in `ParallaxCore`.

Final Figma QA evidence for this board is stored at:

```text
.phase8_evidence/screenshots/figma-drawer-expansion-qa-final-board.png
```

Simulator visual evidence for the implemented drawer workflows is stored at:

```text
.phase8_evidence/screenshots/simulator/phase8-ios-step-detail.jpg
.phase8_evidence/screenshots/simulator/phase8-ios-friction-evidence.jpg
.phase8_evidence/screenshots/simulator/phase8-ios-forgotten-timer.jpg
.phase8_evidence/screenshots/simulator/phase8-ios-review-decision.jpg
.phase8_evidence/screenshots/simulator/phase8-ios-preflight-evidence.jpg
.phase8_evidence/screenshots/simulator/phase8-ios-checkpoint-setup.jpg
```

The matching Figma node exports used for side-by-side review are stored at:

```text
.phase8_evidence/screenshots/figma/figma-step-detail.png
.phase8_evidence/screenshots/figma/figma-friction-evidence.png
.phase8_evidence/screenshots/figma/figma-forgotten-timer.png
.phase8_evidence/screenshots/figma/figma-review-decision.png
.phase8_evidence/screenshots/figma/figma-preflight-evidence.png
.phase8_evidence/screenshots/figma/figma-checkpoint-setup.png
```

Required frame naming remains:

```text
Parallax / <Surface> / <State> / <Breakpoint or Device>
```

Required component naming remains:

```text
Parallax/<ComponentName>/<Variant>
```

## Verification

Run:

```text
make phase8-smoke
```

This executes:

- `python3 scripts/phase8_ui_contract.py`
- `swift test --package-path apps/ios`
- `xcodebuild -project apps/ios/ParallaxNative.xcodeproj -scheme ParallaxNative -destination 'generic/platform=iOS Simulator' -derivedDataPath apps/ios/DerivedData build`
