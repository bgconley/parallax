-- Parallax v1.3 migration 0011
-- Capture context snapshots, geospatial/radio/device observations, user places, and temporal feature vectors.

BEGIN;

CREATE TYPE capture_method AS ENUM (
  'manual_timer_button',
  'lock_screen_widget',
  'home_screen_widget',
  'watch',
  'voice',
  'quick_chip',
  'shortcut',
  'nfc_tag',
  'calendar_import',
  'system_detected',
  'review_reconstruction',
  'background_signal',
  'api'
);

CREATE TYPE capture_trigger AS ENUM (
  'user_initiated',
  'timer_event',
  'annotation',
  'checkpoint_event',
  'permission_change',
  'geofence_transition',
  'place_visit',
  'radio_fingerprint_change',
  'motion_change',
  'sync_replay',
  'review'
);

CREATE TYPE geospatial_source_type AS ENUM (
  'fused_location',
  'gps',
  'network_location',
  'wifi_derived',
  'wifi_rtt',
  'ble_beacon',
  'ibeacon',
  'uwb',
  'cell',
  'manual_place',
  'geofence',
  'visit',
  'significant_location_change',
  'none'
);

CREATE TYPE radio_source_type AS ENUM (
  'wifi_connected_network',
  'wifi_scan',
  'wifi_rtt',
  'ble_scan',
  'ibeacon',
  'uwb',
  'cell',
  'unknown'
);

CREATE TYPE motion_state AS ENUM (
  'unknown',
  'stationary',
  'walking',
  'running',
  'cycling',
  'driving',
  'in_vehicle',
  'transit',
  'mixed'
);

CREATE TYPE place_category AS ENUM (
  'unknown',
  'home',
  'work',
  'office',
  'kitchen',
  'garage',
  'yard',
  'store',
  'gym',
  'vehicle',
  'public',
  'client_site',
  'medical',
  'school',
  'religious',
  'other'
);

CREATE TYPE sensor_availability_state AS ENUM (
  'available',
  'permission_denied',
  'disabled_by_user',
  'disabled_by_system',
  'unsupported',
  'unavailable',
  'not_requested',
  'stale'
);

CREATE TYPE sensor_retention_policy AS ENUM (
  'do_not_store',
  'derived_only',
  'short_ttl_raw',
  'store_with_consent'
);

CREATE TABLE context_capture_policy (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  location_enabled boolean NOT NULL DEFAULT false,
  precise_location_enabled boolean NOT NULL DEFAULT false,
  background_location_enabled boolean NOT NULL DEFAULT false,
  radio_context_enabled boolean NOT NULL DEFAULT false,
  motion_context_enabled boolean NOT NULL DEFAULT false,
  device_context_enabled boolean NOT NULL DEFAULT true,
  raw_location_retention_days integer CHECK (raw_location_retention_days IS NULL OR raw_location_retention_days >= 0),
  raw_radio_retention_days integer CHECK (raw_radio_retention_days IS NULL OR raw_radio_retention_days >= 0),
  default_location_retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  default_radio_retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  per_run_context_default boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE user_place (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  category place_category NOT NULL DEFAULT 'unknown',
  latitude numeric(9,6),
  longitude numeric(9,6),
  radius_meters integer CHECK (radius_meters IS NULL OR radius_meters > 0),
  source geospatial_source_type NOT NULL DEFAULT 'manual_place',
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  confirmed_by_user boolean NOT NULL DEFAULT false,
  is_sensitive boolean NOT NULL DEFAULT false,
  aliases text[] NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE INDEX idx_user_place_user_category ON user_place(user_id, category);
CREATE INDEX idx_user_place_user_name ON user_place(user_id, lower(display_name));

CREATE TABLE capture_context_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  checkpoint_run_id uuid REFERENCES checkpoint_run(id) ON DELETE SET NULL,
  user_place_id uuid REFERENCES user_place(id) ON DELETE SET NULL,
  capture_method capture_method NOT NULL,
  capture_trigger capture_trigger NOT NULL,
  client_captured_at timestamptz NOT NULL,
  server_received_at timestamptz NOT NULL DEFAULT now(),
  client_monotonic_millis bigint,
  source_device_id text NOT NULL,
  app_foreground_state text NOT NULL DEFAULT 'unknown' CHECK (app_foreground_state IN ('foreground','background','locked','extension','unknown')),
  location_state sensor_availability_state NOT NULL DEFAULT 'not_requested',
  radio_state sensor_availability_state NOT NULL DEFAULT 'not_requested',
  motion_state_available sensor_availability_state NOT NULL DEFAULT 'not_requested',
  device_context_state sensor_availability_state NOT NULL DEFAULT 'available',
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  context_quality_score numeric(4,3) CHECK (context_quality_score IS NULL OR context_quality_score BETWEEN 0 AND 1),
  permission_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  client_mutation_id text NOT NULL,
  client_device_id text NOT NULL,
  idempotency_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, client_device_id, client_mutation_id),
  UNIQUE(user_id, idempotency_key)
);

CREATE INDEX idx_capture_context_session_time ON capture_context_snapshot(session_id, client_captured_at);
CREATE INDEX idx_capture_context_user_time ON capture_context_snapshot(user_id, client_captured_at DESC);
CREATE INDEX idx_capture_context_user_method ON capture_context_snapshot(user_id, capture_method, client_captured_at DESC);

CREATE TABLE geospatial_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  snapshot_id uuid NOT NULL REFERENCES capture_context_snapshot(id) ON DELETE CASCADE,
  source geospatial_source_type NOT NULL,
  observed_at timestamptz NOT NULL,
  latitude numeric(9,6),
  longitude numeric(9,6),
  altitude_meters numeric,
  horizontal_accuracy_meters numeric CHECK (horizontal_accuracy_meters IS NULL OR horizontal_accuracy_meters >= 0),
  vertical_accuracy_meters numeric CHECK (vertical_accuracy_meters IS NULL OR vertical_accuracy_meters >= 0),
  speed_mps numeric,
  course_degrees numeric CHECK (course_degrees IS NULL OR course_degrees BETWEEN 0 AND 360),
  is_precise boolean NOT NULL DEFAULT false,
  is_stale boolean NOT NULL DEFAULT false,
  staleness_seconds integer CHECK (staleness_seconds IS NULL OR staleness_seconds >= 0),
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE INDEX idx_geospatial_observation_snapshot ON geospatial_observation(snapshot_id);
CREATE INDEX idx_geospatial_observation_user_time ON geospatial_observation(user_id, observed_at DESC);
CREATE INDEX idx_geospatial_observation_lat_lon ON geospatial_observation(user_id, latitude, longitude);

CREATE TABLE radio_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  snapshot_id uuid NOT NULL REFERENCES capture_context_snapshot(id) ON DELETE CASCADE,
  source radio_source_type NOT NULL,
  observed_at timestamptz NOT NULL,
  identifier_hash text,
  label_hash text,
  redacted_display_label text,
  rssi_dbm integer,
  tx_power_dbm integer,
  distance_meters numeric CHECK (distance_meters IS NULL OR distance_meters >= 0),
  distance_accuracy_meters numeric CHECK (distance_accuracy_meters IS NULL OR distance_accuracy_meters >= 0),
  frequency_mhz integer,
  channel text,
  is_connected boolean,
  raw_encrypted_object_ref text,
  privacy_class privacy_class NOT NULL DEFAULT 'sensitive',
  retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_radio_observation_snapshot ON radio_observation(snapshot_id);
CREATE INDEX idx_radio_observation_user_time ON radio_observation(user_id, observed_at DESC);
CREATE INDEX idx_radio_observation_identifier_hash ON radio_observation(user_id, source, identifier_hash);

CREATE TABLE device_context_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  snapshot_id uuid NOT NULL REFERENCES capture_context_snapshot(id) ON DELETE CASCADE,
  observed_at timestamptz NOT NULL,
  motion_state motion_state NOT NULL DEFAULT 'unknown',
  battery_percent integer CHECK (battery_percent IS NULL OR battery_percent BETWEEN 0 AND 100),
  charging_state text NOT NULL DEFAULT 'unknown' CHECK (charging_state IN ('charging','discharging','full','unknown')),
  network_state text NOT NULL DEFAULT 'unknown' CHECK (network_state IN ('offline','wifi','cellular','ethernet','mixed','unknown')),
  device_type text NOT NULL DEFAULT 'unknown' CHECK (device_type IN ('phone','tablet','watch','desktop','browser','unknown')),
  app_foreground_state text NOT NULL DEFAULT 'unknown' CHECK (app_foreground_state IN ('foreground','background','locked','extension','unknown')),
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  retention_policy sensor_retention_policy NOT NULL DEFAULT 'derived_only',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_device_context_snapshot ON device_context_observation(snapshot_id);
CREATE INDEX idx_device_context_user_motion ON device_context_observation(user_id, motion_state, observed_at DESC);

CREATE TABLE inferred_place_observation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  snapshot_id uuid NOT NULL REFERENCES capture_context_snapshot(id) ON DELETE CASCADE,
  user_place_id uuid REFERENCES user_place(id) ON DELETE SET NULL,
  candidate_label text,
  candidate_category place_category NOT NULL DEFAULT 'unknown',
  confidence numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  confirmation_state confirmation_state NOT NULL DEFAULT 'needs_confirmation',
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  sensitive_label_detected boolean NOT NULL DEFAULT false,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_inferred_place_snapshot ON inferred_place_observation(snapshot_id);
CREATE INDEX idx_inferred_place_user_state ON inferred_place_observation(user_id, confirmation_state, created_at DESC);
CREATE INDEX idx_inferred_place_user_place ON inferred_place_observation(user_id, user_place_id, created_at DESC);

CREATE TABLE temporal_feature_vector (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  activity_id uuid REFERENCES activity(id) ON DELETE CASCADE,
  session_id uuid REFERENCES timing_session(id) ON DELETE CASCADE,
  snapshot_id uuid REFERENCES capture_context_snapshot(id) ON DELETE SET NULL,
  feature_schema_version text NOT NULL DEFAULT '1.3.0',
  feature_family text NOT NULL CHECK (feature_family IN ('duration_prediction','start_latency','transition_latency','friction','place_inference','prompt_policy','anomaly_detection')),
  features jsonb NOT NULL,
  source_entity_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  model_eligible boolean NOT NULL DEFAULT false,
  exclusion_reason text,
  generated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_temporal_feature_user_activity_family ON temporal_feature_vector(user_id, activity_id, feature_family, generated_at DESC);
CREATE INDEX idx_temporal_feature_session ON temporal_feature_vector(session_id, feature_family);

ALTER TABLE timing_event
  ADD COLUMN capture_context_snapshot_id uuid REFERENCES capture_context_snapshot(id) ON DELETE SET NULL,
  ADD COLUMN capture_context_snapshot_ref text;

ALTER TABLE temporal_context_annotation
  ADD COLUMN capture_context_snapshot_id uuid REFERENCES capture_context_snapshot(id) ON DELETE SET NULL,
  ADD COLUMN capture_context_snapshot_ref text;

CREATE INDEX idx_timing_event_context_snapshot ON timing_event(capture_context_snapshot_id);
CREATE INDEX idx_annotation_context_snapshot ON temporal_context_annotation(capture_context_snapshot_id);
CREATE INDEX idx_timing_event_context_snapshot_ref
  ON timing_event(user_id, capture_context_snapshot_ref)
  WHERE capture_context_snapshot_ref IS NOT NULL;
CREATE INDEX idx_annotation_context_snapshot_ref
  ON temporal_context_annotation(user_id, capture_context_snapshot_ref)
  WHERE capture_context_snapshot_ref IS NOT NULL;

COMMIT;
