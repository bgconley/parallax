-- Activity Profile query examples.

-- Latest stats snapshot for one activity.
SELECT *
FROM activity_stats_snapshot
WHERE user_id = :user_id
  AND activity_id = :activity_id
ORDER BY computed_at DESC
LIMIT 1;

-- Reviewed sessions that can update full duration model.
SELECT *
FROM timing_session
WHERE user_id = :user_id
  AND activity_id = :activity_id
  AND status = 'reviewed'
  AND model_inclusion IN ('full','active_duration_only','wall_envelope_only')
ORDER BY completed_at DESC
LIMIT 25;

-- Common friction for an activity over the last 90 days.
SELECT
  tes.friction_category,
  count(*) AS event_count,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY tes.duration_seconds) AS p50_seconds,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY tes.duration_seconds) AS p80_seconds
FROM timing_event_span tes
JOIN timing_session ts ON ts.id = tes.session_id
WHERE tes.user_id = :user_id
  AND ts.activity_id = :activity_id
  AND tes.started_at >= now() - interval '90 days'
  AND tes.friction_category <> 'none'
GROUP BY tes.friction_category
ORDER BY event_count DESC;
