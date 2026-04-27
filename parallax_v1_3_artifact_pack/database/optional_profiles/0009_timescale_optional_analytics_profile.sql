-- Parallax v1.3 migration 0009
-- OPTIONAL TimescaleDB analytics profile.
-- This script is not required for the core application and must be enabled only
-- after TimescaleDB compatibility is validated in the target database image.
-- It creates analytics shadow tables; it does not replace source-of-truth timing tables.
-- Compatibility note: this prototype profile uses exact PostgreSQL
-- percentile_cont ordered-set aggregates inside a Timescale continuous
-- aggregate. Live-test this against the selected Timescale/Tiger image before
-- enabling. If unsupported or too costly, use Timescale Toolkit approximate
-- percentile aggregates such as percentile_agg/approx_percentile or tdigest for
-- the continuous aggregate path, and keep exact percentiles in ordinary batch SQL.

BEGIN;

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS temporal_metric_point (
  observed_at timestamptz NOT NULL,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid REFERENCES activity(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  metric_name text NOT NULL,
  metric_value_seconds integer CHECK (metric_value_seconds IS NULL OR metric_value_seconds >= 0),
  metric_value_numeric numeric,
  tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_table text NOT NULL,
  source_id uuid NOT NULL
);

SELECT create_hypertable(
  'temporal_metric_point',
  by_range('observed_at', INTERVAL '7 days'),
  if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_temporal_metric_point_user_metric_time
  ON temporal_metric_point(user_id, metric_name, observed_at DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS activity_duration_daily
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', observed_at) AS bucket,
  user_id,
  activity_id,
  metric_name,
  count(*) AS sample_count,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY metric_value_seconds) AS p50_seconds,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY metric_value_seconds) AS p80_seconds
FROM temporal_metric_point
WHERE metric_value_seconds IS NOT NULL
GROUP BY bucket, user_id, activity_id, metric_name
WITH NO DATA;

COMMIT;
