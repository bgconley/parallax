-- Parallax v1.3 migration 9999
-- Development seed data only. Do not apply to production.

BEGIN;

INSERT INTO app_user (id, email, display_name, timezone)
VALUES ('00000000-0000-0000-0000-000000000001', 'demo@example.com', 'Demo User', 'America/New_York')
ON CONFLICT (id) DO NOTHING;

INSERT INTO privacy_settings (user_id)
VALUES ('00000000-0000-0000-0000-000000000001')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO activity (id, user_id, display_name, canonical_key, default_timing_mode)
VALUES (
  '00000000-0000-0000-0000-000000000101',
  '00000000-0000-0000-0000-000000000001',
  'Clean pots and pans',
  'clean_pots_and_pans',
  'whole_task'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO preflight_check (id, user_id, activity_id, check_text, source, confidence)
VALUES (
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000101',
  'Check sponge or scrubber before starting.',
  'user_created',
  1.0
)
ON CONFLICT (id) DO NOTHING;

COMMIT;
