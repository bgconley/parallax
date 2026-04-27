-- Ask About Time deterministic fact examples.

-- "How long does this activity usually take?"
SELECT
  count(*) AS sample_size,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY active_seconds) AS active_p50_seconds,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY active_seconds) AS active_p80_seconds,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY wall_seconds) AS wall_p50_seconds,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY wall_seconds) AS wall_p80_seconds
FROM timing_session
WHERE user_id = :user_id
  AND activity_id = :activity_id
  AND status = 'reviewed'
  AND model_inclusion IN ('full','active_duration_only','wall_envelope_only')
  AND completed_at >= now() - interval '180 days';

-- "What usually delays it?"
SELECT
  friction_category,
  count(*) AS event_count,
  sum(duration_seconds) AS total_seconds,
  percentile_cont(0.8) WITHIN GROUP (ORDER BY duration_seconds) AS p80_seconds
FROM timing_event_span tes
JOIN timing_session ts ON ts.id = tes.session_id
WHERE tes.user_id = :user_id
  AND ts.activity_id = :activity_id
  AND ts.status = 'reviewed'
  AND tes.friction_category <> 'none'
GROUP BY friction_category
ORDER BY event_count DESC, total_seconds DESC;
