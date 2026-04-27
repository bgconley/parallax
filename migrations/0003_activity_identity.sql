-- Parallax v1.3 migration 0003
-- Activity identity, aliases, and relationships.

BEGIN;

CREATE TABLE activity (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  canonical_key text,
  description text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived','merged')),
  merged_into_activity_id uuid REFERENCES activity(id) ON DELETE SET NULL,
  default_timing_mode timing_mode NOT NULL DEFAULT 'whole_task',
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, canonical_key)
);

CREATE INDEX idx_activity_user_status ON activity(user_id, status);
CREATE INDEX idx_activity_user_display_lower ON activity(user_id, lower(display_name));

CREATE TABLE activity_alias (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  alias_text text NOT NULL,
  normalized_alias text NOT NULL,
  source text NOT NULL DEFAULT 'user' CHECK (source IN ('user','system_suggested','imported')),
  confidence numeric(4,3) NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
  user_confirmed boolean NOT NULL DEFAULT true,
  rejected boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, normalized_alias, activity_id)
);

CREATE INDEX idx_activity_alias_user_norm ON activity_alias(user_id, normalized_alias);

CREATE TABLE activity_relationship (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  from_activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  to_activity_id uuid NOT NULL REFERENCES activity(id) ON DELETE CASCADE,
  kind relationship_kind NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  user_confirmed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (from_activity_id <> to_activity_id),
  UNIQUE(from_activity_id, to_activity_id, kind)
);

CREATE INDEX idx_activity_relationship_user_from ON activity_relationship(user_id, from_activity_id, kind);
CREATE INDEX idx_activity_relationship_user_to ON activity_relationship(user_id, to_activity_id, kind);

COMMIT;
