-- Parallax v1.3 migration 0001
-- Extensions and canonical enums.
-- Required baseline extensions: pgcrypto and citext.
-- Optional extensions are installed in later feature-profile migrations.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TYPE timing_mode AS ENUM (
  'estimate_only',
  'whole_task',
  'checkpointed',
  'routine',
  'calibration',
  'passive'
);

CREATE TYPE timing_session_status AS ENUM (
  'draft',
  'intent_recorded',
  'running',
  'paused',
  'completed_unreviewed',
  'reviewed',
  'discarded',
  'abandoned'
);

CREATE TYPE work_mode AS ENUM (
  'unknown',
  'home',
  'wfh',
  'office',
  'travel',
  'weekend',
  'errand',
  'hybrid'
);

CREATE TYPE actor_mode AS ENUM (
  'solo',
  'assisted',
  'delegated',
  'unknown'
);

CREATE TYPE privacy_class AS ENUM (
  'normal',
  'sensitive',
  'private'
);

CREATE TYPE run_quality AS ENUM (
  'unknown',
  'typical',
  'useful_unusual',
  'assisted',
  'partial',
  'bad_timer',
  'corrupted',
  'do_not_train'
);

CREATE TYPE model_inclusion AS ENUM (
  'not_reviewed',
  'full',
  'active_duration_only',
  'wall_envelope_only',
  'friction_patterns_only',
  'query_evidence_only',
  'exclude'
);

CREATE TYPE annotation_input_mode AS ENUM (
  'text',
  'voice',
  'quick_chip',
  'system_detected',
  'review_note'
);

CREATE TYPE annotation_status AS ENUM (
  'captured',
  'transcription_pending',
  'transcribed',
  'extraction_pending',
  'extracted',
  'needs_confirmation',
  'confirmed',
  'corrected',
  'ignored',
  'redacted',
  'deleted'
);

CREATE TYPE timing_event_type AS ENUM (
  'intent_recorded',
  'session_started',
  'session_paused',
  'session_resumed',
  'session_completed',
  'session_abandoned',
  'checkpoint_started',
  'checkpoint_completed',
  'checkpoint_skipped',
  'annotation_captured',
  'extracted_event_created',
  'active_work_started',
  'active_work_completed',
  'setup_started',
  'setup_completed',
  'resource_detour_started',
  'resource_detour_completed',
  'interruption_started',
  'interruption_completed',
  'waiting_started',
  'waiting_completed',
  'side_quest_started',
  'side_quest_completed',
  'transition_started',
  'transition_completed',
  'bad_timer_marked',
  'scope_changed',
  'user_correction_applied',
  'review_saved',
  'sync_reconciled'
);

CREATE TYPE temporal_span_type AS ENUM (
  'active_work',
  'setup',
  'resource_detour',
  'interruption',
  'waiting',
  'side_quest',
  'start_latency',
  'transition',
  'body_energy',
  'decision_loop',
  'attention_drift',
  'environment_friction',
  'bad_timer',
  'scope_change',
  'other'
);

CREATE TYPE friction_category AS ENUM (
  'none',
  'resource',
  'setup',
  'transition',
  'interruption',
  'waiting',
  'side_quest',
  'decision',
  'attention',
  'body_energy',
  'environment',
  'timer_quality',
  'scope',
  'unknown'
);

CREATE TYPE count_policy AS ENUM (
  'wall_and_active',
  'wall_only',
  'active_only',
  'separate_start_latency',
  'separate_transition',
  'do_not_count',
  'review_required'
);

CREATE TYPE confirmation_state AS ENUM (
  'auto_logged',
  'needs_confirmation',
  'confirmed',
  'corrected',
  'ignored',
  'deferred_to_review'
);

CREATE TYPE relationship_kind AS ENUM (
  'same_as',
  'alias_of',
  'part_of',
  'has_checkpoint',
  'variant_of',
  'related_to',
  'usually_before',
  'usually_after'
);

CREATE TYPE model_update_decision_type AS ENUM (
  'save_useful_run',
  'mark_unusual',
  'save_partial',
  'active_only',
  'friction_only',
  'query_evidence_only',
  'discard_timing_keep_note',
  'discard_all'
);

CREATE TYPE prediction_basis AS ENUM (
  'generic_prior',
  'personal_last_time',
  'personal_rolling_stats',
  'personal_model',
  'hybrid',
  'insufficient_data'
);

CREATE TYPE confidence_label AS ENUM (
  'very_low',
  'low',
  'medium',
  'high'
);

CREATE TYPE job_status AS ENUM (
  'queued',
  'running',
  'succeeded',
  'failed',
  'cancelled',
  'waiting_for_user'
);

CREATE TYPE model_role AS ENUM (
  'context_extractor',
  'query_intent_classifier',
  'query_narrator',
  'preflight_suggester',
  'embedding',
  'reranker',
  'evaluator'
);

COMMIT;
