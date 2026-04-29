# Phase 5 Checkpoints, Latency, and Feature Vectors

Phase 5 implements the temporal modeling scope from
`parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md` Phase 5:

- activity checkpoint templates and per-session checkpoint runs
- start-latency spans and observations
- transition-latency spans and observations
- baseline temporal feature-vector generation through the workflow worker

## Architecture

Routes stay thin. Checkpoint template endpoints continue through
`ActivityMetadataService`. Timing event and review routes continue through
`TimingService`; checkpoint-run state is isolated in
`repositories/checkpoint_run_state.py` for the in-memory path and
`repositories/postgres_checkpoint_runs.py` for Postgres. Latency observation
persistence is similarly split into `latency_observation_state.py` and
`postgres_latency_observations.py`.

Span derivation remains pure domain logic in `domain/timing_spans.py`.
Feature-vector payload construction is pure domain logic in
`domain/feature_vectors.py`; repositories only load eligible source data,
apply privacy policy, delete stale vectors for the recompute scope, and persist
new `temporal_feature_vector` rows. The worker drains the canonical
`GenerateTemporalFeatureVectorWorkflow` and marks success only after vectors are
generated.

## Semantics

Checkpointed sessions create planned `checkpoint_run` records from the current
activity templates. `checkpoint_started`, `checkpoint_completed`, and
`checkpoint_skipped` events update run status without corrupting sequence order.
Reviewed checkpoint pairs become `active_work` spans linked to checkpoint runs;
skipped checkpoints do not contribute active or wall statistics.

`intended_start_at` is optional. When present and the actual start is later, the
review path derives a `start_latency` span with `separate_start_latency` policy
and a `start_latency_observation`. That time is not folded into active duration.
Transition events derive `transition` spans with `separate_transition` policy
and `transition_observation` rows, separate from source and target duration.

Temporal feature vectors are generated from reviewed, model-eligible timing
data. Location/radio-derived feature families honor `context_capture_policy`:
when location and radio context are disabled, place-inference vectors are stored
as not model-eligible with `context_disabled_by_policy` rather than smuggling
context into model inputs.

## Verification

Phase 5 is complete only when local unit/static/security/contract checks pass
and the GPU node passes `make schema-smoke`, `make phase1-smoke`,
`make phase2-smoke`, `make phase3-smoke`, `make phase4-smoke`, and
`make phase5-smoke` against the current working tree. Clean-database migration
proof must also apply all baseline migrations and pass current schema smoke.
