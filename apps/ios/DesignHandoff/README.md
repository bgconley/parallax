# Parallax Phase 8 Design Handoff

This directory is the repo-side Phase 8 handoff for the native UI and Figma
pass.

`phase8_figma_handoff.json` records the code-ready inventory and the created
Figma file. The canonical token source remains:

```text
parallax_v1_3_artifact_pack/contracts/design/design_tokens.json
```

The created Figma file is:

```text
name: Parallax - v1.3 Native Screens
url: https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9
file_key: OYOtLrgwZmqAqsURzYJBM9
status: created
```

The file imports the canonical Phase 8 reference mockups and payload examples
from `parallax_v1_3_artifact_pack/examples/`. It also imports
`figma_expansion_readiness_pack_v0_8_1/` as visual grammar only; that pack was
written for a broader task app, so Parallax keeps the same design language while
limiting implemented frames to temporal tracking.

The current Figma pass includes a visual refinement audit: screen headers use
bounded title lanes, dynamic type stress cards are sized for safe wrapping, and
the temporal UI kit uses readable visible labels while preserving canonical
component node names.

The `04 Core Flow Prototype - Timing Loop` page now uses source-backed
components for all five canonical reference mockups. The earlier simplified
vector drafts were moved to `08 Superseded Vector Drafts` so they are not used
as finished visual targets.

The `05 P0 Screens + States` and `06 Accessibility + Offline Stress` pages also
use canonical-derived state cards. Each card keeps a canonical reference mockup
as the visual substrate and records the state behavior in a handoff rail instead
of inventing unrelated low-fidelity screens.

Frames use the naming pattern:

```text
Parallax / <Surface> / <State> / <Breakpoint or Device>
```

Component names should use:

```text
Parallax/<ComponentName>/<Variant>
```
