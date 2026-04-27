# 22 — v1.3 Gap Closure Summary

This document summarizes the v1.3 update that closes the timing analytics, capture workflow, geospatial/radio context, and user-story gaps identified after the v1.2 handoff pack.

## Summary answer

v1.2 had a coherent temporal-first application model, but it was still under-specified in four areas:

1. context-aware timing analytics;
2. real-world capture workflows across device surfaces and user circumstances;
3. geospatial, Wi-Fi, BLE, beacon, motion, and device-context handling;
4. user stories that force the UI/UX to support messy real-world timing rather than only ideal timer sessions.

v1.3 addresses those gaps with new docs, schemas, migrations, OpenAPI paths, events, workflows, examples, and eval matrices.

## What changed

### Timing analytics

v1.3 adds explicit support for:

- contextual timing feature vectors;
- start latency, transition latency, recovery latency, and setup/cleanup time;
- forgotten timer detection signals;
- place-aware timing estimates;
- context-aware anomaly detection;
- confidence and uncertainty decomposition;
- ambient context as evidence, not truth;
- privacy-preserving aggregation and retention.

### Capture workflows

v1.3 defines canonical capture methods and scenarios for:

- manual timer buttons;
- quick chips;
- voice capture;
- lock-screen widgets;
- home-screen widgets;
- watch capture;
- shortcuts;
- NFC tags;
- calendar import;
- background signals;
- review reconstruction;
- API capture.

The implementation direction is clear: every capture path must create append-safe source events or append-safe context snapshots, and the system must continue to work when all optional sensors are disabled.

### Geospatial and radio context

v1.3 adds a permission-gated context model for:

- fused location / GPS / network location;
- manual place selection;
- geofences and visit-like signals;
- Wi-Fi connected network;
- Wi-Fi scan fingerprints;
- BLE / iBeacon / UWB proximity signals;
- cell coarse context;
- motion/activity state;
- device foreground/background/locked state;
- permission state and sensor availability.

The model deliberately avoids making location or radio context mandatory. Raw context must have a retention policy, privacy class, and provenance. Radio observation labels are explicitly safe display text only: `redacted_display_label` must not contain raw SSID, BSSID, MAC, beacon, UWB peer, or cell identifiers.

### Data model

v1.3 adds the following canonical tables and schema objects:

- `context_capture_policy`;
- `user_place`;
- `capture_context_snapshot`;
- `geospatial_observation`;
- `radio_observation`;
- `device_context_observation`;
- `inferred_place_observation`;
- `timing_review_flag`;
- `temporal_feature_vector`.

These objects connect temporal events to real-world circumstances without allowing ambient context to silently rewrite source timing truth.

### API and workflow contracts

v1.3 adds API paths for:

- session-scoped capture-context snapshots;
- server-authoritative context capture policy;
- checkpoint/place-linked capture snapshot creation;
- creating and updating user-confirmed places;
- listing user places;
- read-only place resolution from a context snapshot;
- updating place metadata;
- listing and resolving timing review flags;
- recomputing temporal feature vectors.
- explicit context-specific privacy export/redaction/delete scopes.

v1.3 adds event and workflow contracts for:

- context snapshot capture;
- context normalization;
- place inference;
- feature vector generation;
- possible forgotten timer detection.

### User stories

v1.3 adds user stories for:

- real-world capture surfaces;
- context snapshots at timing boundaries;
- user-controlled place context;
- forgotten timer detection;
- post-hoc run reconstruction;
- context-aware estimates;
- radio/sensor privacy;
- reducing prompt burden over time.

These stories should directly inform UI and UX design. The UI should not simply show a timer; it should make capture feel possible during interruptions, movement, hands-busy moments, recovery periods, and post-hoc correction.

## Files added or materially updated

New documents:

- `docs/18_timing_analytics_and_context_intelligence.md`
- `docs/19_capture_workflows_and_sensor_fusion.md`
- `docs/20_mobile_location_radio_privacy_reference.md`
- `docs/21_current_platform_and_extension_references.md`
- `docs/22_v1_3_gap_closure_summary.md`

New migrations:

- `database/migrations/0011_capture_context_geospatial_sensor_fusion.sql`
- `database/migrations/0014_timing_review_flags.sql`
- `database/optional_profiles/0012_postgis_optional_geospatial_profile.sql`
- `database/optional_profiles/0013_timescale_capture_context_profile.sql`

New query examples:

- `database/queries/context_geospatial_queries.sql`
- `database/queries/privacy_export_delete_queries.sql`

New schemas:

- `contracts/json_schema/user_place.schema.json`
- `contracts/json_schema/capture_context_snapshot.schema.json`
- `contracts/json_schema/geospatial_observation.schema.json`
- `contracts/json_schema/radio_observation.schema.json`
- `contracts/json_schema/device_context_observation.schema.json`
- `contracts/json_schema/inferred_place_observation.schema.json`
- `contracts/json_schema/temporal_feature_vector.schema.json`

New examples and evals:

- `examples/payloads/sample_capture_context_snapshot.json`
- `examples/payloads/sample_temporal_feature_vector.json`
- `examples/payloads/sample_place_change_forgotten_timer_scenario.json`
- `tests_or_eval/capture_workflow_scenario_matrix.csv`
- `tests_or_eval/geospatial_context_eval_cases.jsonl`
- `tests_or_eval/sensor_privacy_test_matrix.csv`
- `tests_or_eval/timing_analytics_feature_tests.csv`

## Implementation priority

Do not implement passive tracking first. The correct sequence is:

1. baseline timer and review loop;
2. explicit capture methods with all sensors denied;
3. context snapshot creation at timer boundaries;
4. optional coarse place/manual place support;
5. optional radio/BLE/geofence context behind permissions and retention controls;
6. feature vectors and forgotten-timer detection;
7. contextual estimates and contextual Ask About Time answers.

This preserves trust while giving the system enough contextual intelligence to become useful over time.
