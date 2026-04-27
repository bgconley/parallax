-- Timing semantics examples.

-- Resource detour should count as wall only by default.
INSERT INTO timing_event_span (
  user_id, session_id, span_type, friction_category, started_at, ended_at,
  duration_seconds, count_policy, count_in_wall_time, count_in_active_time
)
VALUES (
  :user_id, :session_id, 'resource_detour', 'resource',
  :started_at, :ended_at, :duration_seconds,
  'wall_only', true, false
);

-- Aggregate active and wall seconds from spans.
SELECT
  coalesce(sum(duration_seconds) FILTER (WHERE count_in_wall_time), 0) AS wall_seconds,
  coalesce(sum(duration_seconds) FILTER (WHERE count_in_active_time), 0) AS active_seconds,
  coalesce(sum(duration_seconds) FILTER (WHERE friction_category <> 'none'), 0) AS friction_seconds
FROM timing_event_span
WHERE user_id = :user_id
  AND session_id = :session_id;
