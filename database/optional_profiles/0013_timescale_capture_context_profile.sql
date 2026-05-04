-- Parallax v1.3 migration 0013
-- OPTIONAL TimescaleDB capture-context analytics profile.
-- This profile creates shadow analytics tables only. It does not replace
-- source-of-truth timing, context, or observation tables.
-- Compatibility note: this prototype profile uses exact PostgreSQL
-- percentile_cont ordered-set aggregates inside a Timescale continuous
-- aggregate. Live-test this against the selected Timescale/Tiger image before
-- enabling. If unsupported or too costly, use Timescale Toolkit approximate
-- percentile aggregates such as percentile_agg/approx_percentile or tdigest for
-- the continuous aggregate path, and keep exact percentiles in ordinary batch SQL.

BEGIN;

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS capture_context_metric_point (
  observed_at timestamptz NOT NULL,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  snapshot_id uuid REFERENCES capture_context_snapshot(id) ON DELETE CASCADE,
  metric_name text NOT NULL,
  metric_value_numeric numeric,
  metric_value_seconds integer CHECK (metric_value_seconds IS NULL OR metric_value_seconds >= 0),
  dimensions jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_table text NOT NULL,
  source_id uuid NOT NULL
);

SELECT create_hypertable(
  'capture_context_metric_point',
  by_range('observed_at', INTERVAL '7 days'),
  if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_capture_context_metric_user_metric_time
  ON capture_context_metric_point(user_id, metric_name, observed_at DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS capture_context_daily
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', observed_at) AS bucket,
  user_id,
  metric_name,
  count(*) AS sample_count,
  avg(metric_value_numeric) AS avg_value,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY metric_value_numeric) AS p50_value,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY metric_value_numeric) AS p80_value
FROM capture_context_metric_point
WHERE metric_value_numeric IS NOT NULL
GROUP BY bucket, user_id, metric_name
WITH NO DATA;

COMMIT;
