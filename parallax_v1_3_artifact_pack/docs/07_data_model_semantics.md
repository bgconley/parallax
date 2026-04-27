# 07 — Data Model and Temporal Semantics

## Design intent

The Parallax data model is event-first but not event-only. It stores source timing actions as append-safe events, stores user review decisions as first-class facts, and uses derived tables for spans, summaries, predictions, evidence, retrieval, and query answers.

This gives Parallax three properties that are critical for trust:

1. The system can reconstruct what happened.
2. The user can correct the interpretation.
3. Derived insights can be explained with evidence.

## Source-of-truth tables

The following tables contain source truth or user-confirmed truth:

- `app_user`
- `user_device`
- `privacy_settings`
- `activity`
- `activity_alias`
- `activity_relationship`
- `timing_session`
- `timing_event`
- `temporal_context_annotation`
- `checkpoint_template`
- `checkpoint_run`
- `model_update_decision`
- `temporal_correction`
- `client_mutation_log`
- `audit_log`

## Derived or auditable projection tables

The following tables are derived, correctable, or workflow-generated:

- `timing_event_span`
- `temporal_extracted_context_event`
- `resource_dependency`
- `preflight_check`
- `start_latency_observation`
- `transition_observation`
- `activity_stats_snapshot`
- `temporal_prediction`
- `prediction_outcome`
- `evidence_bundle`
- `evidence_item`
- `temporal_query_answer`
- `retrieval_document`
- `retrieval_embedding_1024`
- `retrieval_embedding_1536`
- `model_invocation`
- `workflow_run`
- `outbox_event`

## Why source events and spans are separate

A user may say "I had to go downstairs for a sponge" after the detour already happened. The source event is an annotation at a timer position. The derived span may be a five-minute resource detour. Later the user may correct the duration or mark the detour as part of setup. If source events and spans were collapsed into one row, the correction story would be lossy.

## Timing reconstruction

The reconstruction service should:

1. Load session source events ordered by client sequence, client timestamp, and server receipt time.
2. Estimate client clock drift when available.
3. Derive open/closed intervals for active work, pause, checkpoint, waiting, detour, interruption, and side quest states.
4. Attach annotations and extracted events by timer position and timestamp.
5. Apply user corrections.
6. Produce spans with count policies.
7. Calculate wall, active, setup, detour, interruption, waiting, side quest, start latency, and transition totals.
8. Flag impossible or suspicious sequences for review.

## Idempotency

Every mutating API request includes:

- `client_mutation_id`
- `client_device_id`
- `client_timestamp`
- `idempotency_key`
- optional `client_sequence`

The database enforces uniqueness on `(user_id, client_device_id, client_mutation_id)`. The API returns the previous result for duplicate mutations.

## Offline replay

Offline replay must not double-count. The client may send delayed events. The backend must persist them and recompute affected projections. If an event sequence is impossible, it should not be dropped. It should be retained and flagged.

## Privacy classification

Canonical privacy classes:

- `normal`: ordinary timing data and non-sensitive notes.
- `sensitive`: personal content that can be processed only under stricter settings.
- `private`: raw content should be excluded from model calls, embeddings, and query quotes unless explicitly allowed.

Embeddings can leak semantic content. Sensitive/private raw notes should not be embedded by default. Derived summaries may be embedded when they remove sensitive detail.

## Activity identity

An activity may have aliases and relationships. Activity identity operations are auditable because they affect historical interpretation. A merge must preserve source activity IDs and should set merged activities to `status = 'merged'` with `merged_into_activity_id`.

## Review and model inclusion

A session can be completed but not reviewed. The estimator must only use reviewed data according to `model_inclusion` and detailed `model_update_decision.scopes`.

Example:

- A sponge detour should update resource/preflight patterns.
- It should not update active washing baseline unless the user says it should.
- It may update wall envelope if the user chooses a full or unusual-but-useful inclusion.

## Statistics

Activity stats should use robust distributions. For early phases, exact SQL percentile calculations are acceptable. Later phases may use more robust estimators that handle small samples, work mode, actor mode, checkpoints, and start latency.

Minimum display policy:

- 0 reviewed runs: show empty/sparse state.
- 1–2 reviewed runs: show "early signal" with very low confidence.
- 3–4 reviewed runs: show low confidence.
- 5–9 reviewed runs: show medium confidence if variance is not extreme.
- 10+ reviewed runs: high confidence only if calibration metrics support it.

## Optional extension posture

### pgvector

Use pgvector when retrieval documents and embeddings are needed. Keep embedding dimensions in separate indexed tables to avoid mixing vector dimensions.

### ParadeDB

Use ParadeDB/`pg_search` only after baseline FTS exists and compatibility is validated. It is a richer lexical/hybrid search profile, not required for source truth.

### TimescaleDB

Use TimescaleDB for analytics acceleration, not source truth. The optional profile creates a shadow metric table and continuous aggregates so core event constraints remain simple.


## v1.3 context data model semantics

The context tables are evidence and features, not primary timing facts.

- `capture_context_snapshot` is the root for context captured around a user/system action.
- `capture_context_snapshot_ref` is a client-side pending reference used only to
  reconcile out-of-order offline replay; `capture_context_snapshot_id` is the
  resolved server-side link.
- `geospatial_observation` stores location-like data with source, accuracy, precision, and retention policy.
- `radio_observation` stores Wi-Fi/BLE/UWB/cell context using hashed identifiers by default. `redacted_display_label` is a safe user-visible label only and must not contain raw SSID, BSSID, MAC, beacon, UWB peer, or cell identifiers.
- `device_context_observation` stores coarse app/device/motion state.
- `inferred_place_observation` stores candidate place inference.
- `user_place` stores user-confirmed or manually created places.
- `context_capture_policy` is the server-authoritative opt-in and retention policy
  for optional context capture. App permission state cannot override a disabled
  backend policy.
- `timing_review_flag` stores review prompts and evidence for anomalies such as
  possible forgotten timers. It is not source timing truth.
- `temporal_feature_vector` stores privacy-filtered analytics inputs.

If privacy policy changes, downstream feature vectors, retrieval documents, evidence bundles, and analytics snapshots must be recomputed or invalidated.
