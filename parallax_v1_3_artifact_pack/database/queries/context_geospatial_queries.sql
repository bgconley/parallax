-- Parallax v1.3 context/geospatial query examples.

-- Recent capture context for a session.
SELECT
  ccs.id,
  ccs.capture_method,
  ccs.capture_trigger,
  ccs.client_captured_at,
  ccs.location_state,
  ccs.radio_state,
  ccs.context_quality_score,
  up.display_name AS confirmed_place
FROM capture_context_snapshot ccs
LEFT JOIN user_place up ON up.id = ccs.user_place_id
WHERE ccs.user_id = :user_id
  AND ccs.session_id = :session_id
ORDER BY ccs.client_captured_at;

-- Possible forgotten-timer evidence: run completed far after the last high-quality
-- context snapshot or after a place transition.
SELECT
  ts.id AS session_id,
  ts.started_at,
  ts.completed_at,
  ts.wall_seconds,
  count(DISTINCT ipo.id) FILTER (WHERE ipo.confirmation_state = 'needs_confirmation') AS unconfirmed_place_candidates,
  max(ccs.client_captured_at) AS last_context_at
FROM timing_session ts
LEFT JOIN capture_context_snapshot ccs ON ccs.session_id = ts.id
LEFT JOIN inferred_place_observation ipo ON ipo.snapshot_id = ccs.id
WHERE ts.user_id = :user_id
  AND ts.id = :session_id
GROUP BY ts.id;

-- Baseline numeric-radius fallback without PostGIS.
SELECT id, display_name, category, latitude, longitude, radius_meters
FROM user_place
WHERE user_id = :user_id
  AND latitude BETWEEN (:lat - :degree_window) AND (:lat + :degree_window)
  AND longitude BETWEEN (:lon - :degree_window) AND (:lon + :degree_window);

-- Optional PostGIS version, enabled only after 0012.
-- SELECT id, display_name, category
-- FROM user_place
-- WHERE user_id = :user_id
--   AND geog IS NOT NULL
--   AND ST_DWithin(geog, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters);

-- Contextual feature vectors eligible for model training.
SELECT id, activity_id, session_id, feature_family, features, generated_at
FROM temporal_feature_vector
WHERE user_id = :user_id
  AND feature_family = 'duration_prediction'
  AND model_eligible = true
ORDER BY generated_at DESC
LIMIT 100;
