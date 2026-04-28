from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.context import (
    AnnotationStatus,
    CaptureContextSnapshot,
    ContextCapturePolicy,
    CreateAnnotationRequest,
    CreateCaptureContextSnapshotRequest,
    CreatePlaceRequest,
    DeviceContextObservation,
    DeviceContextObservationInput,
    GeospatialObservation,
    GeospatialObservationInput,
    RadioObservation,
    RadioObservationInput,
    ResolvePlaceCandidate,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    TemporalContextAnnotation,
    TimingReviewFlag,
    TimingReviewFlagStatus,
    UpdateContextCapturePolicyRequest,
    UpdatePlaceRequest,
    UserPlace,
)
from ..schemas.timing import AppendTimingEventRequest
from .postgres_identity import ensure_app_user


class PostgresContextRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def get_annotation(
        self,
        user_id: UUID,
        annotation_id: UUID,
    ) -> TemporalContextAnnotation | None:
        self._resolve_annotation_snapshot_link(user_id, annotation_id)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, session_id, checkpoint_run_id, input_mode, raw_text,
                  redacted_text, transcript_confidence, audio_object_ref,
                  timer_elapsed_seconds, timer_active_seconds, occurred_at,
                  privacy_class, status, client_mutation_id, client_device_id,
                  idempotency_key, capture_context_snapshot_id,
                  capture_context_snapshot_ref, metadata
                from temporal_context_annotation
                where user_id = %s and id = %s
                """,
                (user_id, annotation_id),
            )
            row = cursor.fetchone()
        return TemporalContextAnnotation.model_validate(dict(row)) if row else None

    def create_annotation(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
    ) -> TemporalContextAnnotation:
        snapshot_id = request.capture_context_snapshot_id or self.snapshot_id_for_reference(
            user_id, request.capture_context_snapshot_ref
        )
        metadata = {
            **request.metadata,
            "retrieval_document": {
                "created": False,
                "reason": "extraction_not_available",
            },
        }
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into temporal_context_annotation (
                  user_id, session_id, checkpoint_run_id, input_mode, raw_text,
                  redacted_text, transcript_confidence, audio_object_ref,
                  timer_elapsed_seconds, timer_active_seconds, occurred_at,
                  privacy_class, status, client_mutation_id, client_device_id,
                  idempotency_key, capture_context_snapshot_id,
                  capture_context_snapshot_ref, metadata
                )
                values (%s, %s, %s, %s, %s, null, null, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s)
                returning id, user_id, session_id, checkpoint_run_id, input_mode, raw_text,
                  redacted_text, transcript_confidence, audio_object_ref,
                  timer_elapsed_seconds, timer_active_seconds, occurred_at,
                  privacy_class, status, client_mutation_id, client_device_id,
                  idempotency_key, capture_context_snapshot_id,
                  capture_context_snapshot_ref, metadata
                """,
                (
                    user_id,
                    session_id,
                    request.checkpoint_run_id,
                    request.input_mode,
                    request.raw_text,
                    request.audio_object_ref,
                    request.timer_elapsed_seconds,
                    request.timer_active_seconds,
                    request.occurred_at,
                    request.privacy_class,
                    _initial_annotation_status(request),
                    request.mutation.client_mutation_id,
                    request.mutation.client_device_id,
                    request.mutation.idempotency_key,
                    snapshot_id,
                    request.capture_context_snapshot_ref,
                    Jsonb(metadata),
                ),
            )
            annotation_row = cursor.fetchone()
            if annotation_row is None:
                raise RuntimeError("annotation insert returned no row")
            annotation = TemporalContextAnnotation.model_validate(dict(annotation_row))
            self._insert_annotation_event(cursor, user_id, session_id, request, annotation)
        return annotation

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into context_capture_policy (user_id)
                values (%s)
                on conflict (user_id) do nothing
                """,
                (user_id,),
            )
            cursor.execute(_POLICY_SELECT_SQL, (user_id,))
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("context capture policy upsert returned no row")
        return ContextCapturePolicy.model_validate(dict(row))

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy:
        current = self.get_context_capture_policy(user_id)
        updates = {
            key: value
            for key, value in request.model_dump(exclude={"mutation"}).items()
            if value is not None
        }
        policy = current.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update context_capture_policy
                set location_enabled = %s,
                    precise_location_enabled = %s,
                    background_location_enabled = %s,
                    radio_context_enabled = %s,
                    motion_context_enabled = %s,
                    device_context_enabled = %s,
                    raw_location_retention_days = %s,
                    raw_radio_retention_days = %s,
                    default_location_retention_policy = %s,
                    default_radio_retention_policy = %s,
                    per_run_context_default = %s,
                    updated_at = %s
                where user_id = %s
                """,
                (
                    policy.location_enabled,
                    policy.precise_location_enabled,
                    policy.background_location_enabled,
                    policy.radio_context_enabled,
                    policy.motion_context_enabled,
                    policy.device_context_enabled,
                    policy.raw_location_retention_days,
                    policy.raw_radio_retention_days,
                    policy.default_location_retention_policy,
                    policy.default_radio_retention_policy,
                    policy.per_run_context_default,
                    policy.updated_at,
                    user_id,
                ),
            )
        return policy

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
        snapshot = self._load_capture_context_snapshot(user_id, snapshot_id)
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
            if (snapshot := self._load_capture_context_snapshot(user_id, row["id"])) is not None
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

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into user_place (
                  user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                """,
                (
                    user_id,
                    request.display_name,
                    request.category,
                    request.latitude,
                    request.longitude,
                    request.radius_meters,
                    request.source,
                    request.privacy_class,
                    request.confirmed_by_user,
                    request.is_sensitive,
                    request.aliases,
                    Jsonb(request.metadata),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("place insert returned no row")
        return _place_from_row(row)

    def list_places(self, user_id: UUID) -> list[UserPlace]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                from user_place
                where user_id = %s
                order by created_at, id
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        return [_place_from_row(row) for row in rows]

    def get_place(self, user_id: UUID, place_id: UUID) -> UserPlace | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                from user_place
                where user_id = %s and id = %s
                """,
                (user_id, place_id),
            )
            row = cursor.fetchone()
        return _place_from_row(row) if row else None

    def update_place(
        self,
        user_id: UUID,
        place_id: UUID,
        request: UpdatePlaceRequest,
    ) -> UserPlace | None:
        place = self.get_place(user_id, place_id)
        if place is None:
            return None
        updates = {
            key: value
            for key, value in request.model_dump(exclude={"mutation"}).items()
            if value is not None
        }
        updated = place.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update user_place
                set display_name = %s,
                    category = %s,
                    radius_meters = %s,
                    privacy_class = %s,
                    confirmed_by_user = %s,
                    is_sensitive = %s,
                    aliases = %s,
                    updated_at = %s
                where user_id = %s and id = %s
                """,
                (
                    updated.display_name,
                    updated.category,
                    updated.radius_meters,
                    updated.privacy_class,
                    updated.confirmed_by_user,
                    updated.is_sensitive,
                    updated.aliases,
                    updated.updated_at,
                    user_id,
                    place_id,
                ),
            )
        return updated

    def resolve_place(self, user_id: UUID, request: ResolvePlaceRequest) -> ResolvePlaceResponse:
        existing = (
            self.get_place(user_id, request.existing_place_id)
            if request.existing_place_id
            else None
        )
        if existing is None and request.candidate_label:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, user_id, display_name, category, latitude, longitude,
                      radius_meters, source, privacy_class, confirmed_by_user,
                      is_sensitive, aliases, metadata, created_at, updated_at
                    from user_place
                    where user_id = %s and lower(display_name) = lower(%s)
                    order by confirmed_by_user desc, created_at desc
                    limit 1
                    """,
                    (user_id, request.candidate_label),
                )
                row = cursor.fetchone()
            existing = _place_from_row(row) if row else None
        if existing is not None:
            return ResolvePlaceResponse(
                candidates=[
                    ResolvePlaceCandidate(
                        place=existing,
                        candidate_label=existing.display_name,
                        candidate_category=existing.category,
                        confidence=1.0,
                        match_type="existing_place",
                        evidence={"reason": "user_confirmed_place_match"},
                    )
                ],
                recommended_place_id=existing.id,
                requires_confirmation=False,
            )
        return ResolvePlaceResponse(
            candidates=[
                ResolvePlaceCandidate(
                    place=None,
                    candidate_label=request.candidate_label,
                    candidate_category=request.candidate_category,
                    confidence=0.0,
                    match_type="manual_candidate" if request.candidate_label else "no_match",
                    evidence={"reason": "resolver_is_read_only"},
                )
            ],
            recommended_place_id=None,
            requires_confirmation=True,
        )

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]:
        with self._connection.cursor() as cursor:
            if status is None:
                cursor.execute(
                    """
                    select id, user_id, session_id, snapshot_id, flag_type, status,
                      severity, confidence, reason_code, user_message, evidence,
                      created_at, resolved_at, resolution_note
                    from timing_review_flag
                    where user_id = %s and session_id = %s
                    order by created_at, id
                    """,
                    (user_id, session_id),
                )
            else:
                cursor.execute(
                    """
                    select id, user_id, session_id, snapshot_id, flag_type, status,
                      severity, confidence, reason_code, user_message, evidence,
                      created_at, resolved_at, resolution_note
                    from timing_review_flag
                    where user_id = %s and session_id = %s and status = %s
                    order by created_at, id
                    """,
                    (user_id, session_id, status),
                )
            rows = cursor.fetchall()
        return [TimingReviewFlag.model_validate(dict(row)) for row in rows]

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        status: TimingReviewFlagStatus,
        resolution_note: str | None,
    ) -> TimingReviewFlag | None:
        resolved_at = datetime.now(UTC) if status in {"resolved", "dismissed"} else None
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update timing_review_flag
                set status = %s,
                    resolved_at = %s,
                    resolution_note = %s
                where user_id = %s and id = %s
                returning id, user_id, session_id, snapshot_id, flag_type, status,
                  severity, confidence, reason_code, user_message, evidence,
                  created_at, resolved_at, resolution_note
                """,
                (status, resolved_at, resolution_note, user_id, flag_id),
            )
            row = cursor.fetchone()
        return TimingReviewFlag.model_validate(dict(row)) if row else None

    def _load_capture_context_snapshot(
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

    def _insert_annotation_event(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
        annotation: TemporalContextAnnotation,
    ) -> None:
        event_request = AppendTimingEventRequest(
            mutation=request.mutation,
            event_type="annotation_captured",
            client_time=request.occurred_at,
            timer_elapsed_seconds=request.timer_elapsed_seconds,
            timer_active_seconds=request.timer_active_seconds,
            capture_context_snapshot_id=annotation.capture_context_snapshot_id,
            capture_context_snapshot_ref=annotation.capture_context_snapshot_ref,
            payload={"annotation_id": str(annotation.id), "input_mode": request.input_mode},
        )
        cursor.execute(
            """
            insert into timing_event (
              user_id, session_id, event_type, client_time, timer_elapsed_seconds,
              timer_active_seconds, client_sequence, client_mutation_id,
              client_device_id, idempotency_key, capture_context_snapshot_id,
              capture_context_snapshot_ref, payload
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                session_id,
                event_request.event_type,
                event_request.client_time,
                event_request.timer_elapsed_seconds,
                event_request.timer_active_seconds,
                event_request.mutation.client_sequence,
                event_request.mutation.client_mutation_id,
                event_request.mutation.client_device_id,
                event_request.mutation.idempotency_key,
                event_request.capture_context_snapshot_id,
                event_request.capture_context_snapshot_ref,
                Jsonb(event_request.payload),
            ),
        )

    def _resolve_annotation_snapshot_link(self, user_id: UUID, annotation_id: UUID) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update temporal_context_annotation annotation
                set capture_context_snapshot_id = snapshot.id
                from capture_context_snapshot snapshot
                where annotation.user_id = %s
                  and annotation.id = %s
                  and annotation.capture_context_snapshot_id is null
                  and annotation.capture_context_snapshot_ref is not null
                  and snapshot.user_id = annotation.user_id
                  and annotation.capture_context_snapshot_ref in (
                    snapshot.client_mutation_id,
                    snapshot.idempotency_key
                  )
                """,
                (user_id, annotation_id),
            )

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


_POLICY_SELECT_SQL = """
select id, user_id, location_enabled, precise_location_enabled,
  background_location_enabled, radio_context_enabled, motion_context_enabled,
  device_context_enabled, raw_location_retention_days, raw_radio_retention_days,
  default_location_retention_policy, default_radio_retention_policy,
  per_run_context_default, updated_at, created_at
from context_capture_policy
where user_id = %s
"""


def _place_from_row(row: Mapping[str, Any]) -> UserPlace:
    data = dict(row)
    data["latitude"] = float(data["latitude"]) if data.get("latitude") is not None else None
    data["longitude"] = float(data["longitude"]) if data.get("longitude") is not None else None
    return UserPlace.model_validate(data)


def _initial_annotation_status(request: CreateAnnotationRequest) -> AnnotationStatus:
    if request.input_mode == "voice" and request.raw_text is None:
        return "transcription_pending"
    if request.raw_text is not None or request.input_mode in {"quick_chip", "review_note"}:
        return "extraction_pending"
    return "captured"
