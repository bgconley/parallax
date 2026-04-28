from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.extraction import (
    CorrectExtractedEventRequest,
    ExtractedContextEvent,
    ModelInvocationRecord,
    TemporalCorrection,
)


class PostgresContextExtractionRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def update_annotation_status(
        self,
        user_id: UUID,
        annotation_id: UUID,
        status: str,
        metadata_update: dict[str, object],
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update temporal_context_annotation
                set status = %s,
                    metadata = metadata || %s
                where user_id = %s and id = %s
                """,
                (status, Jsonb(metadata_update), user_id, annotation_id),
            )

    def record_model_invocation(
        self,
        invocation: ModelInvocationRecord,
    ) -> ModelInvocationRecord:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into model_invocation (
                  id, user_id, role, provider, model_name, model_version,
                  prompt_version, schema_version, input_privacy_class,
                  request_hash, output_hash, schema_valid, repair_count,
                  fallback_used, latency_ms, tokens_in, tokens_out, metadata,
                  created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s)
                """,
                (
                    invocation.id,
                    invocation.user_id,
                    invocation.role,
                    invocation.provider,
                    invocation.model_name,
                    invocation.model_version,
                    invocation.prompt_version,
                    invocation.schema_version,
                    invocation.input_privacy_class,
                    invocation.request_hash,
                    invocation.output_hash,
                    invocation.schema_valid,
                    invocation.repair_count,
                    invocation.fallback_used,
                    invocation.latency_ms,
                    invocation.tokens_in,
                    invocation.tokens_out,
                    Jsonb(invocation.metadata),
                    invocation.created_at,
                ),
            )
        return invocation

    def create_extracted_event(self, event: ExtractedContextEvent) -> ExtractedContextEvent:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into temporal_extracted_context_event (
                  id, user_id, annotation_id, session_id, checkpoint_run_id,
                  span_type, friction_category, friction_subtype, resource_name,
                  location_from, location_to, duration_seconds, count_policy,
                  count_in_wall_time, count_in_active_time, model_update_scopes,
                  suggested_preflight_text, confidence, confirmation_state,
                  sensitive_data_detected, model_invocation_id, source_json,
                  user_correction_json
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                _event_params(event),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("extracted context event insert returned no row")
        return _event_from_row(row)

    def get_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> ExtractedContextEvent | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select * from temporal_extracted_context_event
                where user_id = %s and id = %s
                """,
                (user_id, event_id),
            )
            row = cursor.fetchone()
        return _event_from_row(row) if row is not None else None

    def update_extracted_event_confirmation(
        self,
        user_id: UUID,
        event_id: UUID,
        confirmation_state: str,
    ) -> ExtractedContextEvent | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update temporal_extracted_context_event
                set confirmation_state = %s,
                    confirmed_at = case
                      when %s in ('confirmed', 'ignored') then now()
                      else confirmed_at
                    end
                where user_id = %s and id = %s
                returning *
                """,
                (confirmation_state, confirmation_state, user_id, event_id),
            )
            row = cursor.fetchone()
        return _event_from_row(row) if row is not None else None

    def correct_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: CorrectExtractedEventRequest,
    ) -> tuple[ExtractedContextEvent, TemporalCorrection] | None:
        before = self.get_extracted_event(user_id, event_id)
        if before is None:
            return None
        before_json = before.model_dump(mode="json")
        update = request.model_dump(exclude={"mutation", "user_note"})
        user_correction_json = {
            "before": before_json,
            "after": update,
            "user_note": request.user_note,
        }
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update temporal_extracted_context_event
                set span_type = %s,
                    friction_category = %s,
                    friction_subtype = %s,
                    resource_name = %s,
                    location_from = %s,
                    location_to = %s,
                    duration_seconds = %s,
                    count_policy = %s,
                    count_in_wall_time = %s,
                    count_in_active_time = %s,
                    suggested_preflight_text = %s,
                    confirmation_state = 'corrected',
                    user_correction_json = %s,
                    confirmed_at = now()
                where user_id = %s and id = %s
                returning *
                """,
                (
                    request.span_type,
                    request.friction_category,
                    request.friction_subtype,
                    request.resource_name,
                    request.location_from,
                    request.location_to,
                    request.duration_seconds,
                    request.count_policy,
                    request.count_in_wall_time,
                    request.count_in_active_time,
                    request.suggested_preflight_text,
                    Jsonb(user_correction_json),
                    user_id,
                    event_id,
                ),
            )
            updated_row = cursor.fetchone()
            if updated_row is None:
                return None
            updated = _event_from_row(updated_row)
            after_json = updated.model_dump(mode="json")
            cursor.execute(
                """
                insert into temporal_correction (
                  user_id, session_id, entity_type, entity_id, correction_type,
                  before_json, after_json, user_note
                )
                values (%s, %s, 'temporal_extracted_context_event', %s,
                  'correct_extracted_event', %s, %s, %s)
                returning *
                """,
                (
                    user_id,
                    updated.session_id,
                    updated.id,
                    Jsonb(before_json),
                    Jsonb(after_json),
                    request.user_note,
                ),
            )
            correction_row = cursor.fetchone()
        if correction_row is None:
            raise RuntimeError("temporal correction insert returned no row")
        return updated, TemporalCorrection.model_validate(dict(correction_row))

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        source_event: ExtractedContextEvent,
    ) -> None:
        if not source_event.suggested_preflight_text:
            return
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into preflight_check (
                  user_id, activity_id, check_text, source, confidence,
                  source_event_id, metadata
                )
                values (%s, %s, %s, 'model_suggested', %s, %s, %s)
                """,
                (
                    user_id,
                    activity_id,
                    source_event.suggested_preflight_text,
                    source_event.confidence,
                    source_event.id,
                    Jsonb({"span_type": source_event.span_type}),
                ),
            )


def _event_params(event: ExtractedContextEvent) -> tuple[object, ...]:
    return (
        event.id,
        event.user_id,
        event.annotation_id,
        event.session_id,
        event.checkpoint_run_id,
        event.span_type,
        event.friction_category,
        event.friction_subtype,
        event.resource_name,
        event.location_from,
        event.location_to,
        event.duration_seconds,
        event.count_policy,
        event.count_in_wall_time,
        event.count_in_active_time,
        event.model_update_scopes,
        event.suggested_preflight_text,
        event.confidence,
        event.confirmation_state,
        event.sensitive_data_detected,
        event.model_invocation_id,
        Jsonb(event.source_json),
        Jsonb(event.user_correction_json),
    )


def _event_from_row(row: Mapping[str, Any]) -> ExtractedContextEvent:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("confirmed_at", None)
    return ExtractedContextEvent.model_validate(data)
