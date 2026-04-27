# 00 — Pack Summary

This v1.3 bundle exists to remove the ambiguity found across the earlier artifacts and produce one implementation-ready Parallax source of truth, now including timing analytics, capture workflows, and geospatial/radio context readiness.

## Alignment decisions made in v1.3

### Canonical name

The canonical product/app name is **Parallax**. All implementation artifacts use `Parallax`, `parallax`, or `PARALLAX_` naming. The earlier placeholders and retired names are not part of this handoff.

### Canonical data model

The backend/domain model is canonical. UI state is a projection. The previous split between UI-specific `account_id` objects and backend `user_id` objects is resolved in favor of `user_id`.

### Canonical API surface

The OpenAPI contract in `contracts/openapi/parallax_api_v1_3.yaml` includes the full P0 surface: activities, timing sessions, events, annotations, extraction, review, checkpoints, preflight, predictions, grounded queries, privacy, export/delete, sync, health, and version.

### Canonical event semantics

The pack separates four related but distinct concepts:

1. `timing_event_type`: append-safe source events emitted by the client or system.
2. `temporal_span_type`: derived or corrected spans used for active/wall/friction counting.
3. `friction_category`: analytic grouping for friction, preflight, and Ask.
4. `model_update_decision_type`: human review decision that controls what the model learns.

### Canonical temporal storage posture

Postgres is the source of truth. Timing events are relational source events. Spans, stats snapshots, retrieval documents, evidence bundles, and query answers are derived or auditable projections. TimescaleDB can accelerate analytics later, but it must not become the sole keeper of timing truth.

### Canonical AI posture

LLMs interpret context and narrate evidence-backed answers. They do not own numeric facts. They do not update baselines directly. Every model output has schema validation, confidence, versioning, evidence, and correction paths.

## What an agent can implement from this pack

An implementation agent can create:

- the monorepo structure;
- database migrations;
- FastAPI service;
- Pydantic request/response models;
- idempotent mutation handling;
- timing event append/replay;
- review and stats computations;
- context annotation capture and extraction workflows;
- Activity Profile endpoints;
- grounded Ask About Time endpoints;
- privacy/export/delete workflows;
- object storage integration;
- Compose-first runtime;
- evaluation harnesses and acceptance checks;
- Figma/iOS design execution guidance.

## What remains intentionally open

Open questions are limited to choices that can be deferred without blocking implementation, such as exact alpha auth provider, exact local model selection, final mobile local-store choice, and whether optional extension profiles are enabled in early alpha.

### v1.3 timing/context additions

v1.3 adds:

- `capture_context_snapshot` as the canonical context root;
- server-authoritative `context_capture_policy`;
- geospatial, radio, device, inferred-place, user-place, timing-review-flag, and temporal-feature-vector contracts;
- real-world capture workflows for voice, quick chip, widget, watch, shortcut, background signal, and post-hoc reconstruction;
- privacy defaults for GPS, Wi-Fi, BLE, UWB, motion, and device context;
- optional PostGIS and Timescale context analytics profiles under `database/optional_profiles/`;
- user stories and acceptance gates for context-aware estimates and capture burden.
