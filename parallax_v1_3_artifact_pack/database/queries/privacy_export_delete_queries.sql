-- Privacy export/redaction/delete examples.
--
-- These examples are implementation guidance, not a complete stored procedure.
-- Every query is user-scoped. Context-specific deletion must also invalidate
-- retrieval documents, evidence items, and feature vectors derived from the
-- affected context source.

-- PrivacyDeleteRequest.delete_scope mapping:
--   raw_context       -> annotations plus all raw/derived context observations
--   location_context  -> geospatial observations and location-derived artifacts
--   radio_context     -> radio observations, radio hashes, safe labels, and raw encrypted refs
--   place_context     -> user places, inferred places, and place-derived artifacts
--   context_features  -> temporal feature vectors sourced from context
--   audio             -> audio object refs and derived transcript artifacts
--   activity          -> activity-scoped data after export/reassignment checks
--   account           -> full user/account deletion after export and backup policy review

-- Find raw annotations for export.
SELECT id, session_id, checkpoint_run_id, input_mode, raw_text, redacted_text,
       occurred_at, privacy_class, status, capture_context_snapshot_id,
       capture_context_snapshot_ref, created_at
FROM temporal_context_annotation
WHERE user_id = :user_id
ORDER BY occurred_at DESC;

-- Export context snapshots and observation summaries.
SELECT id, session_id, checkpoint_run_id, user_place_id, capture_method,
       capture_trigger, client_captured_at, server_received_at, source_device_id,
       app_foreground_state, location_state, radio_state, motion_state_available,
       device_context_state, privacy_class, retention_policy, context_quality_score,
       permission_summary, metadata, created_at
FROM capture_context_snapshot
WHERE user_id = :user_id
ORDER BY client_captured_at DESC;

SELECT id, snapshot_id, source, observed_at, latitude, longitude,
       horizontal_accuracy_meters, is_precise, is_stale, staleness_seconds,
       privacy_class, retention_policy, metadata, created_at
FROM geospatial_observation
WHERE user_id = :user_id
ORDER BY observed_at DESC;

SELECT id, snapshot_id, source, observed_at, identifier_hash, label_hash,
       redacted_display_label, rssi_dbm, distance_meters, is_connected,
       raw_encrypted_object_ref, privacy_class, retention_policy, metadata, created_at
FROM radio_observation
WHERE user_id = :user_id
ORDER BY observed_at DESC;

SELECT id, snapshot_id, observed_at, motion_state, battery_percent,
       charging_state, network_state, device_type, app_foreground_state,
       privacy_class, retention_policy, metadata, created_at
FROM device_context_observation
WHERE user_id = :user_id
ORDER BY observed_at DESC;

SELECT id, display_name, category, latitude, longitude, radius_meters, source,
       privacy_class, confirmed_by_user, is_sensitive, aliases, metadata,
       created_at, updated_at
FROM user_place
WHERE user_id = :user_id
ORDER BY updated_at DESC;

SELECT id, snapshot_id, user_place_id, candidate_label, candidate_category,
       confidence, confirmation_state, evidence, sensitive_label_detected,
       confirmed_at, created_at
FROM inferred_place_observation
WHERE user_id = :user_id
ORDER BY created_at DESC;

SELECT id, activity_id, session_id, snapshot_id, feature_schema_version,
       feature_family, features, source_entity_refs, privacy_class,
       model_eligible, exclusion_reason, generated_at
FROM temporal_feature_vector
WHERE user_id = :user_id
ORDER BY generated_at DESC;

-- Redact raw text while preserving timing facts.
UPDATE temporal_context_annotation
SET raw_text = NULL,
    redacted_text = '[redacted]',
    status = 'redacted',
    metadata = metadata || jsonb_build_object('redacted_at', now())
WHERE user_id = :user_id
  AND id = :annotation_id;

-- Redact location context for one snapshot while preserving the snapshot shell.
UPDATE geospatial_observation
SET latitude = NULL,
    longitude = NULL,
    altitude_meters = NULL,
    speed_mps = NULL,
    course_degrees = NULL,
    is_precise = false,
    retention_policy = 'do_not_store',
    metadata = metadata || jsonb_build_object('redacted_at', now(), 'redaction_scope', 'location_context')
WHERE user_id = :user_id
  AND (:snapshot_id IS NULL OR snapshot_id = :snapshot_id);

-- Redact radio context and collect raw encrypted object refs for object-storage deletion.
SELECT raw_encrypted_object_ref
FROM radio_observation
WHERE user_id = :user_id
  AND raw_encrypted_object_ref IS NOT NULL
  AND (:snapshot_id IS NULL OR snapshot_id = :snapshot_id);

UPDATE radio_observation
SET identifier_hash = NULL,
    label_hash = NULL,
    redacted_display_label = NULL,
    raw_encrypted_object_ref = NULL,
    retention_policy = 'do_not_store',
    metadata = metadata || jsonb_build_object('redacted_at', now(), 'redaction_scope', 'radio_context')
WHERE user_id = :user_id
  AND (:snapshot_id IS NULL OR snapshot_id = :snapshot_id);

-- Redact a user place while preserving historical timing facts.
UPDATE user_place
SET display_name = 'Redacted place',
    latitude = NULL,
    longitude = NULL,
    radius_meters = NULL,
    aliases = '{}',
    privacy_class = 'private',
    is_sensitive = true,
    metadata = metadata || jsonb_build_object('redacted_at', now(), 'redaction_scope', 'place_context'),
    updated_at = now()
WHERE user_id = :user_id
  AND id = :place_id;

UPDATE inferred_place_observation
SET candidate_label = NULL,
    evidence = evidence || jsonb_build_object('redacted_at', now(), 'redaction_scope', 'place_context'),
    sensitive_label_detected = false
WHERE user_id = :user_id
  AND (:place_id IS NULL OR user_place_id = :place_id);

-- Remove context-derived retrieval docs. Optional embedding tables use
-- ON DELETE CASCADE from retrieval_document when pgvector tables exist.
DELETE FROM retrieval_document
WHERE user_id = :user_id
  AND entity_type IN (
    'temporal_context_annotation',
    'capture_context_snapshot',
    'geospatial_observation',
    'radio_observation',
    'device_context_observation',
    'inferred_place_observation',
    'user_place',
    'temporal_feature_vector'
  )
  AND (:entity_id IS NULL OR entity_id = :entity_id);

-- Invalidate feature vectors sourced from context. Implementations may prefer
-- marking exclusion_reason instead of deleting when audit retention is required.
UPDATE temporal_feature_vector
SET model_eligible = false,
    exclusion_reason = 'privacy_redacted'
WHERE user_id = :user_id
  AND (
    snapshot_id = :snapshot_id
    OR source_entity_refs @> jsonb_build_array(jsonb_build_object('entity_id', :entity_id::text))
  );

-- Mark affected query answers for regeneration before deleting evidence links.
WITH affected_bundles AS (
  SELECT DISTINCT bundle_id
  FROM evidence_item
  WHERE user_id = :user_id
    AND entity_type IN (
      'capture_context_snapshot',
      'geospatial_observation',
      'radio_observation',
      'device_context_observation',
      'inferred_place_observation',
      'user_place',
      'temporal_feature_vector'
    )
    AND (:entity_id IS NULL OR entity_id = :entity_id)
)
UPDATE temporal_query_answer
SET status = 'corrected',
    answer = NULL
WHERE user_id = :user_id
  AND evidence_bundle_id IN (SELECT bundle_id FROM affected_bundles);

-- Remove evidence items that reference redacted context. Bundles can remain if
-- computed_facts/limitations are regenerated or the answer is marked corrected.
DELETE FROM evidence_item
WHERE user_id = :user_id
  AND entity_type IN (
    'capture_context_snapshot',
    'geospatial_observation',
    'radio_observation',
    'device_context_observation',
    'inferred_place_observation',
    'user_place',
    'temporal_feature_vector'
  )
  AND (:entity_id IS NULL OR entity_id = :entity_id);
