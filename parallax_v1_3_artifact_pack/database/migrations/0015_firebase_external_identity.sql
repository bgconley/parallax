-- Parallax v1.3 migration 0015
-- Firebase external identity mapping and private-alpha provisioning support.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE external_identity (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL
    REFERENCES app_user(id)
    ON DELETE CASCADE,
  provider text NOT NULL,
  issuer text NOT NULL,
  subject text NOT NULL,
  firebase_tenant_id text NOT NULL DEFAULT '',
  firebase_project_id text NOT NULL,
  sign_in_provider text,
  email citext,
  email_verified boolean,
  display_name text,
  photo_url text,
  auth_time timestamptz,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CHECK (provider <> ''),
  CHECK (issuer <> ''),
  CHECK (subject <> ''),
  CHECK (firebase_project_id <> ''),
  UNIQUE(provider, issuer, subject, firebase_tenant_id)
);

CREATE INDEX idx_external_identity_user_id
  ON external_identity(user_id);

CREATE TABLE alpha_invite (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext UNIQUE,
  firebase_uid text UNIQUE,
  status text NOT NULL DEFAULT 'active',
  invited_by uuid REFERENCES app_user(id),
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  accepted_at timestamptz
);

CREATE TABLE deleted_external_identity_tombstone (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  issuer text NOT NULL,
  subject_hmac bytea NOT NULL,
  firebase_tenant_id text NOT NULL DEFAULT '',
  deleted_at timestamptz NOT NULL DEFAULT now(),
  reason text,
  UNIQUE(provider, issuer, subject_hmac, firebase_tenant_id)
);

CREATE INDEX idx_alpha_invite_status_expires
  ON alpha_invite(status, expires_at);

COMMIT;
