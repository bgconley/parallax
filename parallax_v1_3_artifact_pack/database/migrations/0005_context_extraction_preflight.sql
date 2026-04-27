-- Parallax v1.3 migration 0005
-- Context annotations, extracted events, corrections, resource dependencies, and preflight checks.

BEGIN;

CREATE TABLE temporal_context_annotation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  input_mode annotation_input_mode NOT NULL,
  raw_text text,
  redacted_text text,
  transcript_confidence numeric(4,3) CHECK (transcript_confidence IS NULL OR transcript_confidence BETWEEN 0 AND 1),
  audio_object_ref text,
  timer_elapsed_seconds integer CHECK (timer_elapsed_seconds IS NULL OR timer_elapsed_seconds >= 0),
  timer_active_seconds integer CHECK (timer_active_seconds IS NULL OR timer_active_seconds >= 0),
  occurred_at timestamptz NOT NULL,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  status annotation_status NOT NULL DEFAULT 'captured',
  client_mutation_id text NOT NULL,
  client_device_id text NOT NULL,
  idempotency_key text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id, client_mutation_id),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX idx_annotation_session_time ON temporal_context_annotation(session_id, occurred_at);
CREATE INDEX idx_annotation_user_status ON temporal_context_annotation(user_id, status, occurred_at DESC);
CREATE INDEX idx_annotation_user_privacy ON temporal_context_annotation(user_id, privacy_class, occurred_at DESC);

CREATE TABLE temporal_extracted_context_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  annotation_id uuid NOT NULL REFERENCES temporal_context_annotation(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  span_type temporal_span_type NOT NULL,
  friction_category friction_category NOT NULL DEFAULT 'unknown',
  friction_subtype text,
  resource_name text,
  location_from text,
  location_to text,
  duration_seconds integer CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
  count_policy count_policy NOT NULL DEFAULT 'review_required',
  count_in_wall_time boolean NOT NULL DEFAULT true,
  count_in_active_time boolean NOT NULL DEFAULT false,
  model_update_scopes text[] NOT NULL DEFAULT '{}',
  suggested_preflight_text text,
  confidence numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  confirmation_state confirmation_state NOT NULL DEFAULT 'needs_confirmation',
  sensitive_data_detected boolean NOT NULL DEFAULT false,
  model_invocation_id uuid,
  source_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  user_correction_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  confirmed_at timestamptz
);

CREATE INDEX idx_extracted_event_session ON temporal_extracted_context_event(session_id, created_at DESC);
CREATE INDEX idx_extracted_event_user_category ON temporal_extracted_context_event(user_id, friction_category, created_at DESC);
CREATE INDEX idx_extracted_event_user_state ON temporal_extracted_context_event(user_id, confirmation_state, created_at DESC);

CREATE TABLE temporal_correction (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  entity_type text NOT NULL CHECK (entity_type IN ('timing_event','timing_event_span','temporal_extracted_context_event','checkpoint_run','activity','activity_alias')),
  entity_id uuid NOT NULL,
  correction_type text NOT NULL,
  before_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  after_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  user_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_temporal_correction_user_time ON temporal_correction(user_id, created_at DESC);
CREATE INDEX idx_temporal_correction_entity ON temporal_correction(entity_type, entity_id);

ALTER TABLE timing_event_span
  ADD CONSTRAINT fk_timing_span_annotation
  FOREIGN KEY (linked_annotation_id) REFERENCES temporal_context_annotation(id) ON DELETE SET NULL;

ALTER TABLE timing_event_span
  ADD CONSTRAINT fk_timing_span_extracted_event
  FOREIGN KEY (linked_extracted_event_id) REFERENCES temporal_extracted_context_event(id) ON DELETE SET NULL;

ALTER TABLE start_latency_observation
  ADD CONSTRAINT fk_start_latency_annotation
  FOREIGN KEY (evidence_annotation_id) REFERENCES temporal_context_annotation(id) ON DELETE SET NULL;

CREATE TABLE resource_dependency (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  resource_name text NOT NULL,
  required_state text,
  usual_location text,
  failure_count integer NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
  median_delay_seconds integer CHECK (median_delay_seconds IS NULL OR median_delay_seconds >= 0),
  p80_delay_seconds integer CHECK (p80_delay_seconds IS NULL OR p80_delay_seconds >= 0),
  suggest_precheck boolean NOT NULL DEFAULT false,
  last_failed_at timestamptz,
  created_from_event_id uuid REFERENCES temporal_extracted_context_event(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(activity_id, lower(resource_name))
);

CREATE INDEX idx_resource_dependency_activity ON resource_dependency(user_id, activity_id, failure_count DESC);

CREATE TABLE preflight_check (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  check_text text NOT NULL,
  state text NOT NULL DEFAULT 'active' CHECK (state IN ('active','snoozed','hidden','retired')),
  source text NOT NULL CHECK (source IN ('user_created','model_suggested','resource_dependency','checkpoint_pattern')),
  confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  failure_count integer NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
  last_triggered_at timestamptz,
  source_event_id uuid REFERENCES temporal_extracted_context_event(id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_preflight_activity_state ON preflight_check(user_id, activity_id, state);

COMMIT;
