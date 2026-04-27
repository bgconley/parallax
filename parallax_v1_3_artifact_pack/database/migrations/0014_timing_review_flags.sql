-- Parallax v1.3 migration 0014
-- Timing review flags for context/anomaly review prompts.

BEGIN;

CREATE TYPE timing_review_flag_type AS ENUM (
  'possible_forgotten_timer',
  'place_transition',
  'long_idle_gap',
  'impossible_sequence',
  'low_context_quality',
  'privacy_review_required',
  'manual_review_requested',
  'other'
);

CREATE TYPE timing_review_flag_status AS ENUM (
  'open',
  'snoozed',
  'resolved',
  'dismissed'
);

CREATE TABLE timing_review_flag (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES timing_session(id) ON DELETE CASCADE,
  snapshot_id uuid REFERENCES capture_context_snapshot(id) ON DELETE SET NULL,
  flag_type timing_review_flag_type NOT NULL,
  status timing_review_flag_status NOT NULL DEFAULT 'open',
  severity text NOT NULL DEFAULT 'medium' CHECK (severity IN ('low','medium','high')),
  confidence numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  reason_code text NOT NULL,
  user_message text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  resolution_note text,
  CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);

CREATE INDEX idx_timing_review_flag_user_status ON timing_review_flag(user_id, status, created_at DESC);
CREATE INDEX idx_timing_review_flag_session_status ON timing_review_flag(session_id, status, created_at DESC);
CREATE INDEX idx_timing_review_flag_snapshot ON timing_review_flag(snapshot_id);

COMMIT;
