# API Surface Phase Scope

The canonical source of API truth remains
`parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml`.

This implementation currently exposes the Phase 0-4 API subset only. It is not the full v1.3 release contract, and it must not be described or shipped as the complete canonical v1.3 surface. Phase 5 and later endpoints remain unimplemented until the user explicitly starts those phases.

## Implemented Scope

The runtime exposes health/version endpoints plus the Phase 1 activity/timing
loop, Phase 2 review/profile endpoints, Phase 3 context-capture endpoints,
Phase 4 extraction/correction endpoints, and
`POST /v1/sync/push`.

`tests/test_phase1_contract_surface.py` enforces that the runtime surface is a
subset of the canonical OpenAPI and that no undocumented `/v1` endpoints are
introduced.

## Deferred Canonical Endpoints

These endpoints are canonical but intentionally not implemented in the current
Phase 0-4 runtime:

- `GET /v1/activities/{activity_id}/checkpoints`
- `GET /v1/activities/{activity_id}/preflight-checks`
- `GET /v1/privacy/settings`
- `GET /v1/sync/pull`
- `GET /v1/temporal/query/{answer_id}`
- `POST /v1/activities/{activity_id}/aliases`
- `POST /v1/activities/{activity_id}/preflight-checks`
- `POST /v1/activities/{activity_id}/relationships`
- `POST /v1/analytics/feature-vectors/recompute`
- `POST /v1/privacy/delete`
- `POST /v1/privacy/export`
- `POST /v1/privacy/redact`
- `POST /v1/temporal/predictions`
- `POST /v1/temporal/predictions/{prediction_id}/outcome`
- `POST /v1/temporal/query`
- `POST /v1/timing/sessions/{session_id}/event-spans`
- `PUT /v1/activities/{activity_id}/checkpoints`
- `PUT /v1/privacy/settings`
