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
        if not source_event.suggested_preflight_text and not source_event.resource_name:
            return
        with self._connection.cursor() as cursor:
            if source_event.suggested_preflight_text:
                cursor.execute(
                    """
                    insert into preflight_check (
                      user_id, activity_id, check_text, state, source, confidence,
                      source_event_id, evidence_count, evidence_summary, metadata
                    )
                    select %s, %s, %s, 'suggested', 'model_suggested', %s, %s, 1,
                      '1 confirmed extracted context event', %s
                    where not exists (
                      select 1
                      from preflight_check
                      where user_id = %s
                        and activity_id = %s
                        and lower(check_text) = lower(%s)
                        and state <> 'retired'
                    )
                    """,
                    (
                        user_id,
                        activity_id,
                        source_event.suggested_preflight_text,
                        source_event.confidence,
                        source_event.id,
                        Jsonb({"span_type": source_event.span_type}),
                        user_id,
                        activity_id,
                        source_event.suggested_preflight_text,
                    ),
                )
            if not source_event.resource_name:
                return
            cursor.execute(
                """
                insert into resource_dependency (
                  user_id, activity_id, resource_name, failure_count,
                  median_delay_seconds, p80_delay_seconds, suggest_precheck,
                  last_failed_at, created_from_event_id, counted_event_ids
                )
                values (%s, %s, %s, 1, %s, %s, false, now(), %s, ARRAY[%s::uuid])
                on conflict (activity_id, (lower(resource_name)))
                do update set
                  failure_count = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.failure_count
                    ELSE resource_dependency.failure_count + 1
                  END,
                  median_delay_seconds = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.median_delay_seconds
                    ELSE excluded.median_delay_seconds
                  END,
                  p80_delay_seconds = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.p80_delay_seconds
                    ELSE greatest(
                      coalesce(resource_dependency.p80_delay_seconds, 0),
                      coalesce(excluded.p80_delay_seconds, 0)
                    )
                  END,
                  suggest_precheck = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.suggest_precheck
                    ELSE resource_dependency.failure_count + 1 >= 2
                  END,
                  last_failed_at = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.last_failed_at
                    ELSE now()
                  END,
                  counted_event_ids = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.counted_event_ids
                    ELSE array_append(
                      resource_dependency.counted_event_ids,
                      excluded.created_from_event_id
                    )
                  END,
                  updated_at = CASE
                    WHEN excluded.created_from_event_id = ANY(resource_dependency.counted_event_ids)
                      THEN resource_dependency.updated_at
                    ELSE now()
                  END
                returning *
                """,
                (
                    user_id,
                    activity_id,
                    source_event.resource_name,
                    source_event.duration_seconds,
                    source_event.duration_seconds,
                    source_event.id,
                    source_event.id,
                ),
            )
            dependency = cursor.fetchone()
            if dependency is None or int(dependency["failure_count"]) < 2:
                return
            check_text = _preflight_text(cursor, activity_id, source_event)
            cursor.execute(
                """
                select 1
                from preflight_check
                where user_id = %s
                  and activity_id = %s
                  and lower(check_text) = lower(%s)
                  and state <> 'retired'
                limit 1
                """,
                (user_id, activity_id, check_text),
            )
            if cursor.fetchone() is not None:
                return
            cursor.execute(
                """
                insert into preflight_check (
                  user_id, activity_id, check_text, state, source, confidence,
                  failure_count, source_event_id, source_dependency_id,
                  evidence_count, evidence_summary, metadata
                )
                values (%s, %s, %s, 'suggested', 'resource_dependency', %s,
                  %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    activity_id,
                    check_text,
                    source_event.confidence,
                    dependency["failure_count"],
                    source_event.id,
                    dependency["id"],
                    dependency["failure_count"],
                    (
                        f"{dependency['failure_count']} confirmed detours for "
                        f"{dependency['resource_name']}"
                    ),
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


def _preflight_text(
    cursor: psycopg.Cursor[Any],
    activity_id: UUID,
    source_event: ExtractedContextEvent,
) -> str:
    cursor.execute("select display_name from activity where id = %s", (activity_id,))
    row = cursor.fetchone()
    activity_name = str(row["display_name"]).casefold() if row is not None else "the activity"
    if activity_name.startswith("wash "):
        activity_name = f"washing {activity_name.removeprefix('wash ')}"
    if source_event.resource_name and source_event.resource_name.casefold() == "sponge":
        return f"Check sponge/scrubber before {activity_name}."
    return source_event.suggested_preflight_text or f"Check resources before {activity_name}."


def _event_from_row(row: Mapping[str, Any]) -> ExtractedContextEvent:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("confirmed_at", None)
    return ExtractedContextEvent.model_validate(data)
