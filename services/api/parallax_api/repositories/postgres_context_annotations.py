from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.context import CreateAnnotationRequest, TemporalContextAnnotation
from ..schemas.timing import AppendTimingEventRequest
from .postgres_context_common import initial_annotation_status
from .postgres_context_snapshots import PostgresContextSnapshotRepository
from .postgres_identity import ensure_app_user


class PostgresContextAnnotationRepository:
    def __init__(
        self,
        connection: psycopg.Connection[Any],
        snapshots: PostgresContextSnapshotRepository,
    ) -> None:
        self._connection = connection
        self._snapshots = snapshots

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
        snapshot_id = (
            request.capture_context_snapshot_id
            or self._snapshots.snapshot_id_for_reference(
                user_id,
                request.capture_context_snapshot_ref,
            )
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
                    initial_annotation_status(request),
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
