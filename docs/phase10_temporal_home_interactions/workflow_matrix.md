# Phase 10 Workflow Matrix

| UI workflow | Canonical local/API behavior |
| --- | --- |
| Timing-run evidence | Opens the expanded timing-run state and can route to review, ask-time, or timing launcher. No source timing fact changes until the nested action is chosen. |
| Quick capture | Queues `annotation_captured` with `CaptureMethod.quickChip`; connected mode syncs through `/v1/timing/sessions/{session_id}/annotations`. |
| Review decision | Queues `review_saved`; connected mode syncs through `/v1/timing/sessions/{session_id}/review` or `/discard`. |
| Forgotten timer trim | Queues `user_correction_applied`; review flag source facts remain unchanged until explicit correction. |
| Forgotten timer kept running | Queues `review_saved` with a human explanation and no duration correction. |
| Preflight decision | Persists `PendingPreflightDecision`; connected mode syncs through `/v1/activities/{activity_id}/preflight-checks/{check_id}/decision`. |
| Sync retry | Calls local pending sync; failures preserve queued mutations and show recoverable pending state. |
| Ask About Time | Builds `TemporalQueryRequest` for `POST /v1/temporal/query`; `include_raw_quotes` remains false by default. |
| Review flags | Uses `/v1/timing/sessions/{session_id}/review-flags` and `/v1/timing/review-flags/{flag_id}`. Updating a flag never mutates timing facts by itself. |
| Extracted-event confirm/correct | Uses `/v1/timing/extracted-events/{event_id}/confirm` and `/correct`; local drawer actions queue equivalent correction/evidence events until backend IDs exist. |
