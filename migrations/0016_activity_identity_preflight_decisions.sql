-- Parallax v1.3 migration 0016
-- Phase 6 activity identity decisions, soft merges, and preflight decisions.

BEGIN;

ALTER TABLE activity_relationship
  ADD COLUMN IF NOT EXISTS state text NOT NULL DEFAULT 'confirmed';

ALTER TABLE activity_relationship
  DROP CONSTRAINT IF EXISTS activity_relationship_state_check;

ALTER TABLE activity_relationship
  ADD CONSTRAINT activity_relationship_state_check
  CHECK (state IN ('suggested','confirmed','rejected'));

UPDATE activity_relationship
SET state = CASE WHEN user_confirmed THEN 'confirmed' ELSE 'suggested' END
WHERE state IS NULL OR state = 'confirmed';

ALTER TABLE preflight_check
  DROP CONSTRAINT IF EXISTS preflight_check_state_check;

ALTER TABLE preflight_check
  ADD CONSTRAINT preflight_check_state_check
  CHECK (state IN ('suggested','active','snoozed','hidden','retired'));

ALTER TABLE preflight_check
  ADD COLUMN IF NOT EXISTS source_dependency_id uuid REFERENCES resource_dependency(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS snoozed_until timestamptz,
  ADD COLUMN IF NOT EXISTS evidence_count integer NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
  ADD COLUMN IF NOT EXISTS evidence_summary text,
  ADD COLUMN IF NOT EXISTS last_decided_at timestamptz,
  ADD COLUMN IF NOT EXISTS decision_reason text;

CREATE TABLE IF NOT EXISTS activity_identity_change (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  change_type text NOT NULL CHECK (change_type IN ('merge')),
  source_activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE RESTRICT,
  target_activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE RESTRICT,
  affected_session_count integer NOT NULL DEFAULT 0 CHECK (affected_session_count >= 0),
  audit_id uuid NOT NULL REFERENCES audit_log(id) ON DELETE RESTRICT,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (source_activity_id <> target_activity_id)
);

CREATE INDEX IF NOT EXISTS idx_activity_identity_change_user_time
  ON activity_identity_change(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_preflight_source_dependency
  ON preflight_check(source_dependency_id);

COMMIT;
