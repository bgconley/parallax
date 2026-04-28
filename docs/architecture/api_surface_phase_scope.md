# API Surface Scope

The canonical source of API truth remains
`parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml`.

The runtime now exposes the canonical v1.3 `/v1` method surface. This closes the
earlier phase-subset route gap: full-contract clients receive a concrete route
for each canonical operation instead of an accidental 404 caused by a missing
router.

## Implementation Depth

Phases 0-4 remain the deepest implemented product paths:

- Phase 1 activity/timing/mutation replay paths are behaviorally implemented.
- Phase 2 review/profile paths are behaviorally implemented.
- Phase 3 context capture/place/review-flag paths are behaviorally implemented.
- Phase 4 extraction/correction paths are behaviorally implemented with durable
  workflow-run audit boundaries.

Later-phase endpoints are intentionally conservative baseline implementations.
They validate canonical schemas, enforce authenticated user scope and mutation
envelopes, persist or enqueue durable records where the baseline schema supports
it, and avoid optional-profile behavior until those phases are explicitly
expanded.

`tests/test_phase1_contract_surface.py` enforces that the runtime route surface
matches the canonical OpenAPI method/path set exactly.
