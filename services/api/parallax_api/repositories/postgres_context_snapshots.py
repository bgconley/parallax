from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.context import (
    CaptureContextSnapshot,
    CreateCaptureContextSnapshotRequest,
    DeviceContextObservation,
    DeviceContextObservationInput,
    GeospatialObservation,
    GeospatialObservationInput,
    RadioObservation,
    RadioObservationInput,
)
from .postgres_identity import ensure_app_user


class PostgresContextSnapshotRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create_capture_context_snapshot(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateCaptureContextSnapshotRequest,
        *,
        geospatial_observations: list[GeospatialObservationInput],
        radio_observations: list[RadioObservationInput],
        device_context_observations: list[DeviceContextObservationInput],
    ) -> CaptureContextSnapshot:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into capture_context_snapshot (
                  user_id, session_id, checkpoint_run_id, user_place_id,
                  capture_method, capture_trigger, client_captured_at,
                  client_monotonic_millis, source_device_id, app_foreground_state,
                  location_state, radio_state, motion_state_available,
                  device_context_state, privacy_class, retention_policy,
                  context_quality_score, permission_summary, metadata,
                  client_mutation_id, client_device_id, idempotency_key
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    user_id,
                    session_id,
                    request.checkpoint_run_id,
                    request.user_place_id,
                    request.capture_method,
                    request.capture_trigger,
                    request.client_captured_at,
                    request.client_monotonic_millis,
                    request.source_device_id,
                    request.app_foreground_state,
                    request.location_state,
                    request.radio_state,
                    request.motion_state_available,
                    request.device_context_state,
                    request.privacy_class,
                    request.retention_policy,
                    request.context_quality_score,
                    Jsonb(request.permission_summary),
                    Jsonb(request.metadata),
                    request.mutation.client_mutation_id,
                    request.mutation.client_device_id,
                    request.mutation.idempotency_key,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("capture context snapshot insert returned no row")
            snapshot_id = row["id"]
            self._insert_geospatial_observations(
                cursor,
                user_id,
                snapshot_id,
                geospatial_observations,
            )
            self._insert_radio_observations(cursor, user_id, snapshot_id, radio_observations)
            self._insert_device_context_observations(
                cursor, user_id, snapshot_id, device_context_observations
            )
        snapshot = self.load_capture_context_snapshot(user_id, snapshot_id)
        if snapshot is None:
            raise RuntimeError("capture context snapshot could not be loaded after insert")
        self.resolve_pending_snapshot_references(user_id, snapshot)
        return snapshot

    def list_capture_context_snapshots(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[CaptureContextSnapshot]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id from capture_context_snapshot
                where user_id = %s and session_id = %s
                order by client_captured_at, id
                """,
                (user_id, session_id),
            )
            rows = cursor.fetchall()
        return [
            snapshot
            for row in rows
            if (snapshot := self.load_capture_context_snapshot(user_id, row["id"])) is not None
        ]

    def snapshot_id_for_reference(self, user_id: UUID, snapshot_ref: str | None) -> UUID | None:
        if snapshot_ref is None:
            return None
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id from capture_context_snapshot
                where user_id = %s
                  and (client_mutation_id = %s or idempotency_key = %s)
                order by created_at desc
                limit 1
                """,
                (user_id, snapshot_ref, snapshot_ref),
            )
            row = cursor.fetchone()
        return row["id"] if row else None

    def resolve_pending_snapshot_references(
        self,
        user_id: UUID,
        snapshot: CaptureContextSnapshot,
    ) -> None:
        references = (snapshot.client_mutation_id, snapshot.idempotency_key)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update timing_event
                set capture_context_snapshot_id = %s
                where user_id = %s
                  and capture_context_snapshot_id is null
                  and capture_context_snapshot_ref = any(%s)
                """,
                (snapshot.id, user_id, list(references)),
            )
            cursor.execute(
                """
                update temporal_context_annotation
                set capture_context_snapshot_id = %s
                where user_id = %s
                  and capture_context_snapshot_id is null
                  and capture_context_snapshot_ref = any(%s)
                """,
                (snapshot.id, user_id, list(references)),
            )

    def load_capture_context_snapshot(
        self,
        user_id: UUID,
        snapshot_id: UUID,
    ) -> CaptureContextSnapshot | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, session_id, checkpoint_run_id, user_place_id,
                  capture_method, capture_trigger, client_captured_at,
                  server_received_at, client_monotonic_millis, source_device_id,
                  app_foreground_state, location_state, radio_state,
                  motion_state_available, device_context_state, privacy_class,
                  retention_policy, context_quality_score, permission_summary,
                  metadata, client_mutation_id, client_device_id, idempotency_key,
                  created_at
                from capture_context_snapshot
                where user_id = %s and id = %s
                """,
                (user_id, snapshot_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        data = dict(row)
        data["geospatial_observations"] = self._load_geospatial_observations(user_id, snapshot_id)
        data["radio_observations"] = self._load_radio_observations(user_id, snapshot_id)
        data["device_context_observations"] = self._load_device_context_observations(
            user_id, snapshot_id
        )
        data["inferred_places"] = []
        return CaptureContextSnapshot.model_validate(data)

    def _insert_geospatial_observations(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        snapshot_id: UUID,
        observations: list[GeospatialObservationInput],
    ) -> None:
        for observation in observations:
            cursor.execute(
                """
                insert into geospatial_observation (
                  user_id, snapshot_id, source, observed_at, latitude, longitude,
                  altitude_meters, horizontal_accuracy_meters,
                  vertical_accuracy_meters, speed_mps, course_degrees,
                  is_precise, is_stale, staleness_seconds, privacy_class,
                  retention_policy, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s)
                """,
                (
                    user_id,
                    snapshot_id,
                    observation.source,
                    observation.observed_at,
                    observation.latitude,
                    observation.longitude,
                    observation.altitude_meters,
                    observation.horizontal_accuracy_meters,
                    observation.vertical_accuracy_meters,
                    observation.speed_mps,
                    observation.course_degrees,
                    observation.is_precise,
                    observation.is_stale,
                    observation.staleness_seconds,
                    observation.privacy_class,
                    observation.retention_policy,
                    Jsonb(observation.metadata),
                ),
            )

    def _insert_radio_observations(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        snapshot_id: UUID,
        observations: list[RadioObservationInput],
    ) -> None:
        for observation in observations:
            cursor.execute(
                """
                insert into radio_observation (
                  user_id, snapshot_id, source, observed_at, identifier_hash,
                  label_hash, redacted_display_label, rssi_dbm, tx_power_dbm,
                  distance_meters, distance_accuracy_meters, frequency_mhz,
                  channel, is_connected, raw_encrypted_object_ref, privacy_class,
                  retention_policy, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s)
                """,
                (
                    user_id,
                    snapshot_id,
                    observation.source,
                    observation.observed_at,
                    observation.identifier_hash,
                    observation.label_hash,
                    observation.redacted_display_label,
                    observation.rssi_dbm,
                    observation.tx_power_dbm,
                    observation.distance_meters,
                    observation.distance_accuracy_meters,
                    observation.frequency_mhz,
                    observation.channel,
                    observation.is_connected,
                    observation.raw_encrypted_object_ref,
                    observation.privacy_class,
                    observation.retention_policy,
                    Jsonb(observation.metadata),
                ),
            )

    def _insert_device_context_observations(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        snapshot_id: UUID,
        observations: list[DeviceContextObservationInput],
    ) -> None:
        for observation in observations:
            cursor.execute(
                """
                insert into device_context_observation (
                  user_id, snapshot_id, observed_at, motion_state, battery_percent,
                  charging_state, network_state, device_type, app_foreground_state,
                  privacy_class, retention_policy, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    snapshot_id,
                    observation.observed_at,
                    observation.motion_state,
                    observation.battery_percent,
                    observation.charging_state,
                    observation.network_state,
                    observation.device_type,
                    observation.app_foreground_state,
                    observation.privacy_class,
                    observation.retention_policy,
                    Jsonb(observation.metadata),
                ),
            )

    def _load_geospatial_observations(
        self,
        user_id: UUID,
        snapshot_id: UUID,
    ) -> list[GeospatialObservation]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, snapshot_id, source, observed_at, latitude,
                  longitude, altitude_meters, horizontal_accuracy_meters,
                  vertical_accuracy_meters, speed_mps, course_degrees, is_precise,
                  is_stale, staleness_seconds, privacy_class, retention_policy,
                  metadata, created_at
                from geospatial_observation
                where user_id = %s and snapshot_id = %s
                order by observed_at, id
                """,
                (user_id, snapshot_id),
            )
            rows = cursor.fetchall()
        return [GeospatialObservation.model_validate(dict(row)) for row in rows]

    def _load_radio_observations(
        self,
        user_id: UUID,
        snapshot_id: UUID,
    ) -> list[RadioObservation]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, snapshot_id, source, observed_at, identifier_hash,
                  label_hash, redacted_display_label, rssi_dbm, tx_power_dbm,
                  distance_meters, distance_accuracy_meters, frequency_mhz, channel,
                  is_connected, raw_encrypted_object_ref, privacy_class,
                  retention_policy, metadata, created_at
                from radio_observation
                where user_id = %s and snapshot_id = %s
                order by observed_at, id
                """,
                (user_id, snapshot_id),
            )
            rows = cursor.fetchall()
        return [RadioObservation.model_validate(dict(row)) for row in rows]

    def _load_device_context_observations(
        self,
        user_id: UUID,
        snapshot_id: UUID,
    ) -> list[DeviceContextObservation]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, snapshot_id, observed_at, motion_state,
                  battery_percent, charging_state, network_state, device_type,
                  app_foreground_state, privacy_class, retention_policy, metadata,
                  created_at
                from device_context_observation
                where user_id = %s and snapshot_id = %s
                order by observed_at, id
                """,
                (user_id, snapshot_id),
            )
            rows = cursor.fetchall()
        return [DeviceContextObservation.model_validate(dict(row)) for row in rows]
