-- Parallax v1.3 implementation hardening migration 0018
-- Retry metadata for durable workflow_run processing.

BEGIN;

ALTER TABLE workflow_run
  ADD COLUMN attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  ADD COLUMN max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
  ADD COLUMN next_run_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN last_heartbeat_at timestamptz;

CREATE INDEX idx_workflow_run_retry_queue
  ON workflow_run(status, next_run_at, created_at)
  WHERE status = 'queued';

COMMIT;
