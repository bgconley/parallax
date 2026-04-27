# 08 — API and Offline Sync Specification

## API principles

The Parallax API is temporal-first, user-scoped, idempotent, and evidence-aware.

Every mutating endpoint must:

- require authentication;
- infer `user_id` from auth context;
- validate request schema;
- require a mutation envelope;
- enforce idempotency;
- avoid heavy model work on the request thread;
- record enough audit metadata to debug sync conflicts.

`POST /v1/activities/resolve` and `POST /v1/places/resolve` are explicit
read-only resolver exceptions despite using POST request bodies. They must not
persist aliases, confirm places, emit outbox events, enqueue jobs, or write domain
audit rows. Activity aliases use `/v1/activities/{activity_id}/aliases`; place
creation/confirmation uses `POST /v1/places`; place edits use
`PATCH /v1/places/{place_id}`.

## Mutation envelope

Canonical mutation envelope:

```json
{
  "client_mutation_id": "mut_01HV...",
  "client_device_id": "device_01HV...",
  "client_timestamp": "2026-04-26T14:03:00Z",
  "idempotency_key": "device_01HV...:mut_01HV...",
  "client_sequence": 42
}
```

The `client_mutation_id` must be unique per device. The `idempotency_key` can be identical to the pair of device and mutation ID or a separate client-generated key.

## Response envelope

Most API responses should include:

```json
{
  "data": {},
  "server_time": "2026-04-26T14:03:01Z",
  "sync": {
    "mutation_accepted": true,
    "duplicate_replay": false,
    "recompute_queued": true
  }
}
```

The OpenAPI contract defines concrete shapes for each endpoint.

## Conflict rules

### Duplicate mutation

Return the original result. Do not create new rows.

### Out-of-order event

Persist the event, mark the session for timeline recomputation, and return accepted.

### Impossible event sequence

Persist the event, flag the session as review-needed or quality-risk, and surface it in review.

### Late annotation

Persist the annotation and attach by timer position, checkpoint, and/or timestamp.

### Client clock drift

Record client and server timestamps. Prefer explicit timer elapsed and sequence when reconstructing session semantics.

## Sync endpoints

The main endpoint-specific mutations are preferred because they preserve intent. A generic sync endpoint can batch replay when the client returns from offline mode:

- `POST /v1/sync/push`: send a top-level batch mutation envelope plus operation
  payloads. Each mutating operation payload still includes its endpoint-level
  mutation envelope.
- `GET /v1/sync/pull`: fetch changes since a sync cursor.

The sync API must use the same validation and idempotency behavior as individual endpoints.

## API surface

The canonical OpenAPI file is:

```text
contracts/openapi/parallax_api_v1_3.yaml
```

Do not build undocumented endpoints during the first implementation unless an ADR explains the addition and updates OpenAPI.

## Error behavior

Use structured errors with:

- `error_code`
- `message`
- `details`
- `request_id`
- `retryable`
- `docs_ref`

Never include raw notes, transcripts, prompts, or sensitive model inputs in error messages.

## Versioning

Use `/v1` for the first production contract. Schema versions are separate from API version and should be included in model invocation and workflow metadata.


## v1.3 capture context API/offline sync additions

All context-capture mutation endpoints use the same mutation envelope as timing events.

Required properties:

- `client_mutation_id`
- `client_device_id`
- `client_timestamp`
- `idempotency_key`
- optional `client_sequence`

Offline replay rules:

- A context snapshot can be replayed without duplicating observations.
- A timing event or annotation can carry `capture_context_snapshot_ref` when the
  related snapshot has not been accepted by the API yet.
- `capture_context_snapshot_id` is the server-resolved direct link after the
  snapshot row exists.
- Snapshot arrival can trigger timeline review flags but not mutate source timing facts.
- Permission-denied, stale, or unsupported sensor states are valid payloads.
- `CreateCaptureContextSnapshotRequest` may include `checkpoint_run_id` and
  `user_place_id` when the client captures context at a checkpoint boundary or
  with an already known/user-selected place.

The backend-authoritative policy endpoint is:

- `GET /v1/privacy/context-capture-policy`
- `PATCH /v1/privacy/context-capture-policy`

The policy row in `context_capture_policy` is the canonical source for whether
optional location/radio/motion/device context capture is enabled and how raw
context may be retained. Mobile OS permission state is necessary but not
sufficient; the API policy must also permit capture.

Review flags are persisted prompts, not timing facts:

- `GET /v1/timing/sessions/{session_id}/review-flags`
- `PATCH /v1/timing/review-flags/{flag_id}`

A review flag can ask the user to inspect a possible forgotten timer, place
transition, or context-quality issue. It must not change event rows, session
totals, model inclusion, or activity statistics unless a user saves an explicit
review decision or correction.

Context-aware deletion scopes are explicit:

- `location_context`: precise/coarse location observations and derived location context.
- `radio_context`: Wi-Fi/BLE/UWB/cell observations, hashes, safe labels, and raw encrypted radio artifacts.
- `place_context`: user places, inferred places, and place-derived retrieval/evidence.
- `context_features`: temporal feature vectors and derived analytics sourced from context.

`raw_context` remains the broad legacy scope and should include all raw notes and
context observations unless a narrower context-specific scope is requested.

Canonical new endpoints are defined in `contracts/openapi/parallax_api_v1_3.yaml`:

- `POST /v1/timing/sessions/{session_id}/capture-context`
- `GET /v1/timing/sessions/{session_id}/capture-context`
- `GET /v1/privacy/context-capture-policy`
- `PATCH /v1/privacy/context-capture-policy`
- `GET /v1/timing/sessions/{session_id}/review-flags`
- `PATCH /v1/timing/review-flags/{flag_id}`
- `POST /v1/places/resolve`
- `POST /v1/places`
- `GET /v1/places`
- `PATCH /v1/places/{place_id}`
- `POST /v1/analytics/feature-vectors/recompute`
