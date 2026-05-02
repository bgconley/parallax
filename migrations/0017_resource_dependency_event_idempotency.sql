-- Parallax v1.3 migration 0017
-- Track counted extracted context events for idempotent resource dependency aggregation.

BEGIN;

ALTER TABLE resource_dependency
  ADD COLUMN IF NOT EXISTS counted_event_ids uuid[] NOT NULL DEFAULT '{}'::uuid[];

UPDATE resource_dependency
SET counted_event_ids = ARRAY[created_from_event_id]
WHERE created_from_event_id IS NOT NULL
  AND cardinality(counted_event_ids) = 0;

COMMIT;
