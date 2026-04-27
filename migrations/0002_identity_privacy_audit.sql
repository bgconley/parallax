-- Parallax v1.3 migration 0002
-- Users, devices, privacy settings, and audit foundation.

BEGIN;

CREATE TABLE app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext UNIQUE,
  display_name text,
  timezone text NOT NULL DEFAULT 'America/New_York',
  locale text NOT NULL DEFAULT 'en-US',
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_device (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  client_device_id text NOT NULL,
  display_name text,
  platform text NOT NULL DEFAULT 'unknown',
  last_seen_at timestamptz,
  sync_cursor text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id)
);

CREATE INDEX idx_user_device_user_seen ON user_device(user_id, last_seen_at DESC);

CREATE TABLE privacy_settings (
  user_id uuid PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  retain_raw_context boolean NOT NULL DEFAULT true,
  retain_transcripts boolean NOT NULL DEFAULT true,
  retain_audio boolean NOT NULL DEFAULT false,
  allow_cloud_llm_fallback boolean NOT NULL DEFAULT false,
  allow_raw_notes_in_query_answers boolean NOT NULL DEFAULT false,
  allow_embedding_of_sensitive_notes boolean NOT NULL DEFAULT false,
  community_aggregation_opt_in boolean NOT NULL DEFAULT false,
  raw_context_retention_days integer CHECK (raw_context_retention_days IS NULL OR raw_context_retention_days >= 0),
  audio_retention_days integer CHECK (audio_retention_days IS NULL OR audio_retention_days >= 0),
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES app_user(id) ON DELETE SET NULL,
  actor_user_id uuid REFERENCES app_user(id) ON DELETE SET NULL,
  event_name text NOT NULL,
  entity_type text,
  entity_id uuid,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_user_time ON audit_log(user_id, occurred_at DESC);
CREATE INDEX idx_audit_event_time ON audit_log(event_name, occurred_at DESC);

COMMIT;
