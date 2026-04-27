-- Parallax v1.3 migration 0006
-- Reviews, model-update decisions, predictions, stats snapshots, evidence, and query answers.

BEGIN;

CREATE TABLE model_update_decision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  decision model_update_decision_type NOT NULL,
  model_inclusion model_inclusion NOT NULL DEFAULT 'not_reviewed',
  scopes text[] NOT NULL DEFAULT '{}',
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  user_note text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_model_update_session ON model_update_decision(session_id, reviewed_at DESC);
CREATE INDEX idx_model_update_user_decision ON model_update_decision(user_id, decision, reviewed_at DESC);

CREATE TABLE activity_stats_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  work_mode work_mode NOT NULL DEFAULT 'unknown',
  actor_mode actor_mode NOT NULL DEFAULT 'unknown',
  window_days integer NOT NULL DEFAULT 90 CHECK (window_days > 0),
  useful_run_count integer NOT NULL DEFAULT 0 CHECK (useful_run_count >= 0),
  active_p50_seconds integer CHECK (active_p50_seconds IS NULL OR active_p50_seconds >= 0),
  active_p80_seconds integer CHECK (active_p80_seconds IS NULL OR active_p80_seconds >= 0),
  wall_p50_seconds integer CHECK (wall_p50_seconds IS NULL OR wall_p50_seconds >= 0),
  wall_p80_seconds integer CHECK (wall_p80_seconds IS NULL OR wall_p80_seconds >= 0),
  start_latency_p50_seconds integer CHECK (start_latency_p50_seconds IS NULL OR start_latency_p50_seconds >= 0),
  start_latency_p80_seconds integer CHECK (start_latency_p80_seconds IS NULL OR start_latency_p80_seconds >= 0),
  top_friction jsonb NOT NULL DEFAULT '[]'::jsonb,
  confidence confidence_label NOT NULL DEFAULT 'very_low',
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_activity_stats_latest ON activity_stats_snapshot(user_id, activity_id, work_mode, actor_mode, computed_at DESC);

CREATE TABLE evidence_bundle (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  purpose text NOT NULL CHECK (purpose IN ('activity_profile','temporal_prediction','temporal_query_answer','preflight_suggestion','model_eval')),
  query_text text,
  computed_facts jsonb NOT NULL DEFAULT '{}'::jsonb,
  limitations jsonb NOT NULL DEFAULT '[]'::jsonb,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_evidence_bundle_user_time ON evidence_bundle(user_id, created_at DESC);

CREATE TABLE evidence_item (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id uuid NOT NULL REFERENCES evidence_bundle(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_id uuid NOT NULL,
  summary text NOT NULL,
  occurred_at timestamptz,
  score numeric,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_evidence_item_bundle ON evidence_item(bundle_id);
CREATE INDEX idx_evidence_item_entity ON evidence_item(user_id, entity_type, entity_id);

CREATE TABLE temporal_prediction (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  prediction_type text NOT NULL CHECK (prediction_type IN ('duration_range','temporal_envelope','start_by','checkpoint_range')),
  work_mode work_mode NOT NULL DEFAULT 'unknown',
  actor_mode actor_mode NOT NULL DEFAULT 'unknown',
  active_p50_seconds integer CHECK (active_p50_seconds IS NULL OR active_p50_seconds >= 0),
  active_p80_seconds integer CHECK (active_p80_seconds IS NULL OR active_p80_seconds >= 0),
  wall_p50_seconds integer CHECK (wall_p50_seconds IS NULL OR wall_p50_seconds >= 0),
  wall_p80_seconds integer CHECK (wall_p80_seconds IS NULL OR wall_p80_seconds >= 0),
  setup_risk_seconds_p80 integer CHECK (setup_risk_seconds_p80 IS NULL OR setup_risk_seconds_p80 >= 0),
  start_latency_p80_seconds integer CHECK (start_latency_p80_seconds IS NULL OR start_latency_p80_seconds >= 0),
  deadline timestamptz,
  start_by timestamptz,
  basis prediction_basis NOT NULL,
  sample_size integer NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
  confidence confidence_label NOT NULL DEFAULT 'very_low',
  evidence_bundle_id uuid REFERENCES evidence_bundle(id) ON DELETE SET NULL,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  model_version text NOT NULL DEFAULT 'deterministic-v1',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_temporal_prediction_user_activity ON temporal_prediction(user_id, activity_id, created_at DESC);

CREATE TABLE prediction_outcome (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  prediction_id uuid NOT NULL REFERENCES temporal_prediction(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE SET NULL,
  outcome_type text NOT NULL CHECK (outcome_type IN ('completed','skipped','deferred','abandoned','ignored')),
  actual_active_seconds integer CHECK (actual_active_seconds IS NULL OR actual_active_seconds >= 0),
  actual_wall_seconds integer CHECK (actual_wall_seconds IS NULL OR actual_wall_seconds >= 0),
  started_by_prediction boolean,
  completed_by_deadline boolean,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_prediction_outcome_prediction ON prediction_outcome(prediction_id);

CREATE TABLE temporal_query_answer (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  question text NOT NULL,
  normalized_intent text,
  answer text,
  confidence confidence_label NOT NULL DEFAULT 'very_low',
  sample_size integer NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
  time_window text,
  evidence_bundle_id uuid REFERENCES evidence_bundle(id) ON DELETE SET NULL,
  model_invocation_id uuid,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','complete','failed','corrected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX idx_temporal_query_answer_user_time ON temporal_query_answer(user_id, created_at DESC);

COMMIT;
