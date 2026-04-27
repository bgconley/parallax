-- Parallax v1.3 migration 0004
-- Timing sessions, source events, spans, checkpoints, start latency, and transitions.

BEGIN;

CREATE TABLE timing_session (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  client_session_id text,
  source_device_id text,
  mode timing_mode NOT NULL DEFAULT 'whole_task',
  status timing_session_status NOT NULL DEFAULT 'draft',
  work_mode work_mode NOT NULL DEFAULT 'unknown',
  actor_mode actor_mode NOT NULL DEFAULT 'unknown',
  intended_start_at timestamptz,
  nudge_shown_at timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  active_seconds integer CHECK (active_seconds IS NULL OR active_seconds >= 0),
  wall_seconds integer CHECK (wall_seconds IS NULL OR wall_seconds >= 0),
  setup_seconds integer CHECK (setup_seconds IS NULL OR setup_seconds >= 0),
  detour_seconds integer CHECK (detour_seconds IS NULL OR detour_seconds >= 0),
  interruption_seconds integer CHECK (interruption_seconds IS NULL OR interruption_seconds >= 0),
  waiting_seconds integer CHECK (waiting_seconds IS NULL OR waiting_seconds >= 0),
  side_quest_seconds integer CHECK (side_quest_seconds IS NULL OR side_quest_seconds >= 0),
  start_latency_seconds integer CHECK (start_latency_seconds IS NULL OR start_latency_seconds >= 0),
  transition_seconds integer CHECK (transition_seconds IS NULL OR transition_seconds >= 0),
  run_quality run_quality NOT NULL DEFAULT 'unknown',
  model_inclusion model_inclusion NOT NULL DEFAULT 'not_reviewed',
  user_pre_estimate_seconds integer CHECK (user_pre_estimate_seconds IS NULL OR user_pre_estimate_seconds >= 0),
  user_felt_duration_seconds integer CHECK (user_felt_duration_seconds IS NULL OR user_felt_duration_seconds >= 0),
  offline_created boolean NOT NULL DEFAULT false,
  needs_timeline_recompute boolean NOT NULL DEFAULT false,
  review_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_session_id)
);

CREATE INDEX idx_timing_session_user_activity_started ON timing_session(user_id, activity_id, started_at DESC);
CREATE INDEX idx_timing_session_user_status ON timing_session(user_id, status);
CREATE INDEX idx_timing_session_user_work_mode ON timing_session(user_id, work_mode);

CREATE TABLE timing_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  event_type timing_event_type NOT NULL,
  client_time timestamptz NOT NULL,
  server_time timestamptz NOT NULL DEFAULT now(),
  timer_elapsed_seconds integer CHECK (timer_elapsed_seconds IS NULL OR timer_elapsed_seconds >= 0),
  timer_active_seconds integer CHECK (timer_active_seconds IS NULL OR timer_active_seconds >= 0),
  client_sequence integer,
  client_mutation_id text NOT NULL,
  client_device_id text NOT NULL,
  idempotency_key text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id, client_mutation_id),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX idx_timing_event_session_time ON timing_event(session_id, client_time, server_time);
CREATE INDEX idx_timing_event_user_type_time ON timing_event(user_id, event_type, client_time DESC);

CREATE TABLE checkpoint_template (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  sequence_order integer NOT NULL CHECK (sequence_order >= 1),
  label text NOT NULL,
  phase_type text,
  optional boolean NOT NULL DEFAULT false,
  usual_active_p50_seconds integer CHECK (usual_active_p50_seconds IS NULL OR usual_active_p50_seconds >= 0),
  usual_active_p80_seconds integer CHECK (usual_active_p80_seconds IS NULL OR usual_active_p80_seconds >= 0),
  usual_wall_p50_seconds integer CHECK (usual_wall_p50_seconds IS NULL OR usual_wall_p50_seconds >= 0),
  usual_wall_p80_seconds integer CHECK (usual_wall_p80_seconds IS NULL OR usual_wall_p80_seconds >= 0),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(activity_id, sequence_order)
);

CREATE INDEX idx_checkpoint_template_activity ON checkpoint_template(user_id, activity_id, sequence_order);

CREATE TABLE checkpoint_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  checkpoint_template_id uuid REFERENCES checkpoint_template(id) ON DELETE SET NULL,
  sequence_order integer NOT NULL CHECK (sequence_order >= 1),
  label text NOT NULL,
  started_at timestamptz,
  completed_at timestamptz,
  active_seconds integer CHECK (active_seconds IS NULL OR active_seconds >= 0),
  wall_seconds integer CHECK (wall_seconds IS NULL OR wall_seconds >= 0),
  friction_seconds integer CHECK (friction_seconds IS NULL OR friction_seconds >= 0),
  status text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','completed','skipped','moved','merged','deleted')),
  user_corrected boolean NOT NULL DEFAULT false,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(session_id, sequence_order)
);

CREATE INDEX idx_checkpoint_run_session ON checkpoint_run(session_id, sequence_order);

CREATE TABLE timing_event_span (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  start_event_id uuid REFERENCES timing_event(id) ON DELETE SET NULL,
  end_event_id uuid REFERENCES timing_event(id) ON DELETE SET NULL,
  span_type temporal_span_type NOT NULL,
  friction_category friction_category NOT NULL DEFAULT 'unknown',
  started_at timestamptz NOT NULL,
  ended_at timestamptz,
  duration_seconds integer CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
  count_policy count_policy NOT NULL DEFAULT 'review_required',
  count_in_wall_time boolean NOT NULL DEFAULT true,
  count_in_active_time boolean NOT NULL DEFAULT false,
  model_update_scopes text[] NOT NULL DEFAULT '{}',
  linked_annotation_id uuid,
  linked_extracted_event_id uuid,
  user_corrected boolean NOT NULL DEFAULT false,
  correction_history jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX idx_timing_span_session_started ON timing_event_span(session_id, started_at);
CREATE INDEX idx_timing_span_user_category ON timing_event_span(user_id, friction_category, started_at DESC);
CREATE INDEX idx_timing_span_user_type ON timing_event_span(user_id, span_type, started_at DESC);

CREATE TABLE start_latency_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  intended_start_at timestamptz,
  nudge_shown_at timestamptz,
  actual_start_at timestamptz NOT NULL,
  latency_seconds integer NOT NULL CHECK (latency_seconds >= 0),
  reason_category friction_category NOT NULL DEFAULT 'unknown',
  evidence_annotation_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_start_latency_activity ON start_latency_observation(user_id, activity_id, actual_start_at DESC);

CREATE TABLE transition_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  from_session_id uuid REFERENCES timing_session(id) ON DELETE SET NULL,
  to_session_id uuid REFERENCES timing_session(id) ON DELETE SET NULL,
  from_checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  to_checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  started_at timestamptz,
  ended_at timestamptz,
  transition_seconds integer CHECK (transition_seconds IS NULL OR transition_seconds >= 0),
  reason_category friction_category NOT NULL DEFAULT 'unknown',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)
);

CREATE INDEX idx_transition_user_time ON transition_observation(user_id, started_at DESC);

COMMIT;
