-- Parallax v1.3 migration 0008
-- Workflow/job state, model invocation audit, client mutation log, sync cursor, and outbox events.

BEGIN;

CREATE TABLE model_invocation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES app_user(id) ON DELETE SET NULL,
  role model_role NOT NULL,
  provider text NOT NULL,
  model_name text NOT NULL,
  model_version text,
  prompt_version text NOT NULL,
  schema_version text,
  input_privacy_class privacy_class NOT NULL DEFAULT 'normal',
  request_hash text,
  output_hash text,
  schema_valid boolean,
  repair_count integer NOT NULL DEFAULT 0 CHECK (repair_count >= 0),
  fallback_used boolean NOT NULL DEFAULT false,
  latency_ms integer CHECK (latency_ms IS NULL OR latency_ms >= 0),
  tokens_in integer CHECK (tokens_in IS NULL OR tokens_in >= 0),
  tokens_out integer CHECK (tokens_out IS NULL OR tokens_out >= 0),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_model_invocation_user_role_time ON model_invocation(user_id, role, created_at DESC);
CREATE INDEX idx_model_invocation_role_valid ON model_invocation(role, schema_valid, created_at DESC);

ALTER TABLE temporal_extracted_context_event
  ADD CONSTRAINT fk_extracted_event_model_invocation
  FOREIGN KEY (model_invocation_id) REFERENCES model_invocation(id) ON DELETE SET NULL;

ALTER TABLE temporal_query_answer
  ADD CONSTRAINT fk_query_answer_model_invocation
  FOREIGN KEY (model_invocation_id) REFERENCES model_invocation(id) ON DELETE SET NULL;

CREATE TABLE workflow_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES app_user(id) ON DELETE SET NULL,
  workflow_type text NOT NULL,
  temporal_workflow_id text,
  status job_status NOT NULL DEFAULT 'queued',
  input_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_run_status_type ON workflow_run(status, workflow_type, created_at);
CREATE INDEX idx_workflow_run_user_time ON workflow_run(user_id, created_at DESC);

CREATE TABLE client_mutation_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  client_device_id text NOT NULL,
  client_mutation_id text NOT NULL,
  idempotency_key text NOT NULL,
  mutation_type text NOT NULL,
  entity_type text,
  entity_id uuid,
  request_hash text,
  result_hash text,
  result_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id, client_mutation_id),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX idx_client_mutation_user_received ON client_mutation_log(user_id, received_at DESC);

CREATE TABLE sync_cursor (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  client_device_id text NOT NULL,
  cursor_value text NOT NULL,
  last_pulled_at timestamptz,
  last_pushed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id)
);

CREATE TABLE outbox_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES app_user(id) ON DELETE CASCADE,
  event_name text NOT NULL,
  aggregate_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status job_status NOT NULL DEFAULT 'queued',
  available_at timestamptz NOT NULL DEFAULT now(),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  dispatched_at timestamptz
);

CREATE INDEX idx_outbox_status_available ON outbox_event(status, available_at);
CREATE INDEX idx_outbox_user_time ON outbox_event(user_id, created_at DESC);

COMMIT;
