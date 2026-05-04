# Phase 10 Temporal Home Interactions

Phase 10 makes the temporal-focused Today/Temporal Home Figma page interaction-complete. It supersedes the broad task-oriented Today/Home interpretation for implementation purposes while preserving the canonical Today density: header, current focus, intelligence card, timeline/list block, quick capture, and bottom action pair.

## Source Of Truth

- Active Figma page: `118:2`
- Active implementation board: `118:3`
- Drawer workflow board: `85:3`
- Action map: `docs/phase10_temporal_home_interactions/action_map.json`
- iOS handoff: `apps/ios/DesignHandoff/phase10_temporal_home_interactions.json`

The page visually defines five target states:

- `118:9` Temporal Home Default
- `118:104` Temporal Home Needs Review
- `118:199` Temporal Home Sync Pending
- `118:294` Temporal Home Expanded Timing Run
- `118:346` Temporal Analytics Grounded Answer

## Scope Guard

Phase 10 remains temporal-only. Do not introduce agenda rows, due dates, generic task priority, project planning, broad settings, or general assistant workflows. Every visible control must resolve to a timing, review, preflight, sync, quick-capture, or grounded-answer behavior, or be explicitly marked `display_only`.

## Acceptance Gate

- Figma page `118:2` and drawer board `85:3` have audited prototype reactions for all interactive controls.
- Swift has no visible Phase 10 or drawer `Button` with an empty action.
- `scripts/phase10_temporal_home_contract.py` passes.
- Swift tests and Xcode build pass.
- GPU backend smoke covers temporal query, review flags, preflight decisions, review save/discard, and annotation creation.
