# 02 — Temporal Domain Model

This file is the canonical semantic reference for Parallax v1.3. Database enums, JSON schemas, OpenAPI contracts, UI view models, tests, and workflow payloads should conform to these definitions.

## Canonical identity field

Use `user_id` throughout backend, database, events, and schemas. UI copy may say "account" where friendlier, but implementation contracts must not introduce `account_id`.

## Canonical nouns

| User-facing noun | Canonical implementation object | Notes |
|---|---|---|
| Activity | `activity` | A recurring or one-off thing the user can time, estimate, or query. |
| Run | `timing_session` | One observed instance of an activity. |
| Step / checkpoint | `checkpoint_template`, `checkpoint_run` | A measurable phase inside an activity or run. |
| Say what happened | `temporal_context_annotation` | Raw user context attached to a run and timer position. |
| Interpreted event | `temporal_extracted_context_event` | Structured candidate interpretation of an annotation. |
| Timeline item | `timing_event` or `timing_event_span` | Source event or derived/corrected span. |
| Useful run | `model_update_decision` + `model_inclusion` | Review controls model learning. |
| Personal range | `activity_stats_snapshot` / `temporal_prediction` | Computed distribution summary, not an LLM fact. |
| Evidence | `evidence_bundle`, `evidence_item` | Audit trail behind predictions and answers. |

## Activity

An activity is the anchor for repeated observations. Examples include "Clean kitchen", "Clean pots and pans", "Get out the door", "Dog walk", and "Send follow-up email".

Activities may have aliases and relationships. For example, "Wash pots" may be an alias of "Clean pots and pans"; "Clean pots and pans" may be a checkpoint or component of "Clean kitchen".

Activity identity is intentionally correctable. Alias suggestions must not merge histories silently.

## Timing session

A timing session is one run of an activity. A run can be complete, partial, abandoned, corrupted, unreviewed, reviewed, or discarded.

A completed run is not automatically a training datapoint. The review decision determines model inclusion.

### Canonical session statuses

- `draft`: session shell created but not started.
- `intent_recorded`: intended start exists before actual start.
- `running`: active timing is in progress.
- `paused`: user paused the run or a pause-like state is active.
- `completed_unreviewed`: user finished timing but has not saved review.
- `reviewed`: user completed review and model inclusion has been decided.
- `discarded`: user discarded timing data.
- `abandoned`: user abandoned the run without completion.

The UI may show states such as "waiting active" or "detour active". These are projections from spans/events, not `timing_session.status` values.

## Timing event

A timing event is an append-safe source action. It is usually created by the client and must support offline replay.

Canonical `timing_event_type` values are:

- `intent_recorded`
- `session_started`
- `session_paused`
- `session_resumed`
- `session_completed`
- `session_abandoned`
- `checkpoint_started`
- `checkpoint_completed`
- `checkpoint_skipped`
- `annotation_captured`
- `extracted_event_created`
- `active_work_started`
- `active_work_completed`
- `setup_started`
- `setup_completed`
- `resource_detour_started`
- `resource_detour_completed`
- `interruption_started`
- `interruption_completed`
- `waiting_started`
- `waiting_completed`
- `side_quest_started`
- `side_quest_completed`
- `transition_started`
- `transition_completed`
- `bad_timer_marked`
- `scope_changed`
- `user_correction_applied`
- `review_saved`
- `sync_reconciled`

Do not use older alternatives such as `timer_started`, `phase_started`, or `activity_completed` in new implementation. Map them at import boundaries only if legacy data ever exists.

## Timing event span

A timing event span is a duration interval used for counting and explanation. Spans can be derived from source events, extracted events, manual corrections, or review decisions.

Canonical `temporal_span_type` values are:

- `active_work`
- `setup`
- `resource_detour`
- `interruption`
- `waiting`
- `side_quest`
- `start_latency`
- `transition`
- `body_energy`
- `decision_loop`
- `attention_drift`
- `environment_friction`
- `bad_timer`
- `scope_change`
- `other`

Every span has a count policy and explicit booleans for active/wall treatment. This redundancy is deliberate: the enum communicates policy, while booleans make aggregation unambiguous.

## Count policy

Canonical `count_policy` values are:

- `wall_and_active`: counts toward wall and active duration.
- `wall_only`: counts toward wall duration but not active work.
- `active_only`: counts toward active duration but is outside session wall boundary or separately corrected.
- `separate_start_latency`: tracked as start latency, not task duration.
- `separate_transition`: tracked as transition latency, not task duration.
- `do_not_count`: retained for audit/evidence but excluded from timing aggregates.
- `review_required`: ambiguous until user review.

## Default counting rules

| Span type | Wall time | Active time | Baseline update | Friction/preflight update |
|---|---:|---:|---|---|
| `active_work` | yes | yes | yes | maybe |
| `setup` | yes | maybe | review-dependent | yes |
| `resource_detour` | yes | no | no | yes |
| `interruption` | yes | no | no | yes |
| `waiting` | yes | maybe | review-dependent | yes |
| `side_quest` | yes until boundary corrected | no | no | yes |
| `start_latency` | separate | no | start model only | yes |
| `transition` | separate | no | transition model only | yes |
| `bad_timer` | review-dependent | no | no | no |
| `scope_change` | yes | review-dependent | review-dependent | yes |

## Context annotation

A context annotation is raw user-provided context. It can come from text, voice, a quick chip, system detection, or review.

Canonical `annotation_input_mode` values are:

- `text`
- `voice`
- `quick_chip`
- `system_detected`
- `review_note`

Canonical `annotation_status` values are:

- `captured`
- `transcription_pending`
- `transcribed`
- `extraction_pending`
- `extracted`
- `needs_confirmation`
- `confirmed`
- `corrected`
- `ignored`
- `redacted`
- `deleted`

Annotations are privacy-sensitive. Raw text and audio must not appear in normal logs.

## Extracted context event

An extracted context event is a schema-bound candidate interpretation of one or more annotations. It can suggest spans, friction categories, resources, locations, count policy, and preflight checks. It must include confidence and confirmation state.

Canonical `confirmation_state` values are:

- `auto_logged`
- `needs_confirmation`
- `confirmed`
- `corrected`
- `ignored`
- `deferred_to_review`

High-confidence, low-risk events may be auto-logged with visible undo/edit. Medium-confidence or count-affecting events require lightweight confirmation. Low-confidence or sensitive events must defer to review.

## Model update decision

The model update decision is the user's final say about what a run teaches. Canonical values are:

- `save_useful_run`: update active duration, wall envelope, and relevant friction patterns.
- `mark_unusual`: retain evidence and update friction patterns; duration baseline depends on selected scopes.
- `save_partial`: useful partial data; do not treat as complete whole-task duration.
- `active_only`: update active baseline only.
- `friction_only`: update friction/preflight patterns only.
- `query_evidence_only`: retain for evidence but do not update predictions.
- `discard_timing_keep_note`: discard timing but keep raw/derived context subject to privacy settings.
- `discard_all`: remove timing and context from normal learning paths, retaining only required audit tombstones.

## Model inclusion

`model_inclusion` is a compact session-level summary of review outcome:

- `not_reviewed`
- `full`
- `active_duration_only`
- `wall_envelope_only`
- `friction_patterns_only`
- `query_evidence_only`
- `exclude`

Use this for fast filtering. Preserve the full `model_update_decision` row for audit and detailed scopes.

## Prediction and stats semantics

A prediction is a distribution summary plus evidence, not a promise. Activity Profile should show p50/p80 or similar range values with sample size and confidence. Do not display confident estimates before enough reviewed data exists.

Canonical confidence labels:

- `very_low`
- `low`
- `medium`
- `high`

## Natural-language query semantics

Ask About Time has two layers:

1. Deterministic computation over scoped user data.
2. LLM narration over computed facts and selected evidence.

The LLM may not create analytics facts. If the fact is not in the evidence payload, it cannot appear as a claim.

## UI projection rules

UI view models can rename concepts for humans, but they must map cleanly back to canonical objects:

- UI "Running" maps to `timing_session.status = running`.
- UI "Waiting active" maps to a current open span with `temporal_span_type = waiting`.
- UI "Say what happened note" maps to `temporal_context_annotation`.
- UI "Interpretation card" maps to `temporal_extracted_context_event`.
- UI "Count this as active?" maps to `count_policy`, `count_in_active_time`, and `count_in_wall_time`.
- UI "Useful run" maps to `model_update_decision`.


## v1.3 context-awareness domain objects

v1.3 adds ambient context as an auxiliary evidence layer. These objects must not be confused with timing truth.

| User-facing noun | Canonical implementation object | Notes |
|---|---|---|
| Capture context | `capture_context_snapshot` | What the client knew around a timing event, annotation, or checkpoint. |
| Place | `user_place` | User-scoped place or place cluster; labels are user-confirmed. |
| Location observation | `geospatial_observation` | GPS/fused/coarse/geofence/visit observation with provenance and accuracy. |
| Radio context | `radio_observation` | Wi-Fi/BLE/UWB/cell-derived hint; raw identifiers are hashed or encrypted by policy. |
| Device context | `device_context_observation` | Motion, foreground/background, connectivity, battery/charging, and device state. |
| Inferred place | `inferred_place_observation` | Candidate place inference with confidence and evidence. |
| Feature vector | `temporal_feature_vector` | Privacy-filtered derived features for analytics/ML; not user-visible truth. |

### Capture context snapshot

A `capture_context_snapshot` is created near important source actions:

- session creation/start/pause/resume/completion;
- checkpoint start/completion;
- annotation or quick-chip capture;
- review correction;
- optional geofence/visit/radio/motion signal when the user has enabled that workflow.

A snapshot records *provenance*, not just values. It must include capture method, capture trigger, client timestamp, server timestamp, source device, permission state, context quality, privacy class, and retention treatment.

A timing event may reference a context snapshot, but the timing event remains valid if no snapshot exists.

### Geospatial observation

A `geospatial_observation` is a location-like observation from GPS, fused location, network location, geofence, visit, significant-change service, Wi-Fi-derived location, BLE/iBeacon, UWB, or manual place selection.

Every geospatial observation must record:

- source type;
- observed timestamp;
- staleness/freshness;
- accuracy when available;
- whether the location is approximate/coarse/precise;
- privacy class and retention policy.

Do not infer a sensitive place label from coordinates alone.

### Radio observation

A `radio_observation` captures nearby or connected radio context, such as Wi-Fi connected network, Wi-Fi scan, Wi-Fi RTT, BLE scan, iBeacon, UWB, or cell-derived hint.

Raw SSIDs, BSSIDs, MAC addresses, beacon IDs, UWB peer identifiers, and cellular identifiers are sensitive. By default, store salted per-user hashes and coarse signal values only. `redacted_display_label` may contain only a user-provided or explicitly redacted safe label; it must not contain raw radio identifiers. Raw identifiers may be stored only as encrypted short-retention artifacts when explicitly enabled.

### Place inference

Place inference is user-scoped. Parallax must not use a global place graph or shared radio fingerprint database in alpha.

A place candidate can become a durable `user_place` only through one of these paths:

- user manually creates or labels it;
- user confirms an inferred candidate;
- user imports/configures it through an explicit integration.

Labels such as `home`, `work`, `medical`, `school`, `client_site`, or other sensitive categories require confirmation. The UI may ask "Was this at Kitchen / Garage / Somewhere else?" but it must not silently label a place.

### Temporal feature vector

A `temporal_feature_vector` is a privacy-filtered derived object used by analytics, evaluation, and future ML. It must include:

- feature schema version;
- source entities;
- included/excluded feature families;
- privacy treatment;
- model eligibility;
- generated timestamp.

Feature vectors are regenerated when relevant review decisions, corrections, privacy settings, or place confirmations change.

### Context does not own duration

Sensor context may explain or flag a run, but it does not own timing facts. A place transition can suggest that the user forgot to stop a timer; it cannot silently trim the timer unless the user explicitly enabled that automation and the decision remains auditable.
