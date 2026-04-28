from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..domain.review_decisions import run_quality_for_decision, status_for_decision
from ..domain.timing_reconstruction import project_timing_session
from ..domain.timing_spans import TimingEventSpanDraft, TimingSpanTotals
from ..schemas.extraction import ExtractedContextEvent
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    ModelUpdateDecision,
    ReviewTimingSessionRequest,
    TimingEvent,
    TimingEventSpan,
    TimingSession,
)
from .postgres_identity import ensure_app_user

_INSERT_SESSION_SQL = """
insert into timing_session (
  user_id, activity_id, client_session_id, source_device_id, mode,
  status, work_mode, actor_mode, intended_start_at,
  user_pre_estimate_seconds, offline_created
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
returning id, user_id, activity_id, client_session_id, source_device_id, mode, status, work_mode,
  actor_mode, intended_start_at, started_at, completed_at, active_seconds, wall_seconds,
  setup_seconds, detour_seconds, interruption_seconds, waiting_seconds, side_quest_seconds,
  start_latency_seconds, transition_seconds, run_quality, model_inclusion,
  needs_timeline_recompute
"""

_INSERT_EVENT_SQL = """
insert into timing_event (
  user_id, session_id, event_type, client_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id,
  client_device_id, idempotency_key, capture_context_snapshot_id,
  capture_context_snapshot_ref, payload
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, event_type, client_time, server_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id, client_device_id,
  idempotency_key, capture_context_snapshot_id, capture_context_snapshot_ref, payload
"""

_LOAD_SESSION_SQL = """
select id, user_id, activity_id, client_session_id, source_device_id, mode, status, work_mode,
  actor_mode, intended_start_at, started_at, completed_at, active_seconds, wall_seconds,
  setup_seconds, detour_seconds, interruption_seconds, waiting_seconds, side_quest_seconds,
  start_latency_seconds, transition_seconds, run_quality, model_inclusion,
  needs_timeline_recompute
from timing_session
where user_id = %s and id = %s
"""

_LOAD_EVENTS_SQL = """
select id, user_id, session_id, event_type, client_time, server_time, timer_elapsed_seconds,
  timer_active_seconds, client_sequence, client_mutation_id, client_device_id,
  idempotency_key, capture_context_snapshot_id, capture_context_snapshot_ref, payload
from timing_event
where user_id = %s and session_id = %s
order by server_time, id
"""

_LOAD_SPANS_SQL = """
select id, user_id, session_id, checkpoint_run_id, span_type, friction_category,
  started_at, ended_at, duration_seconds, count_policy, count_in_wall_time,
  count_in_active_time, model_update_scopes, linked_annotation_id,
  linked_extracted_event_id, user_corrected
from timing_event_span
where user_id = %s and session_id = %s
order by started_at, id
"""

_INSERT_SPAN_SQL = """
insert into timing_event_span (
  user_id, session_id, checkpoint_run_id, start_event_id, end_event_id, span_type,
  friction_category, started_at, ended_at, duration_seconds, count_policy,
  count_in_wall_time, count_in_active_time, model_update_scopes,
  linked_annotation_id, linked_extracted_event_id, user_corrected
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, checkpoint_run_id, span_type, friction_category,
  started_at, ended_at, duration_seconds, count_policy, count_in_wall_time,
  count_in_active_time, model_update_scopes, linked_annotation_id,
  linked_extracted_event_id, user_corrected
"""

_INSERT_REVIEW_SQL = """
insert into model_update_decision (
  user_id, session_id, decision, model_inclusion, scopes, user_note, payload
)
values (%s, %s, %s, %s, %s, %s, %s)
returning id, user_id, session_id, decision, model_inclusion, scopes, reviewed_at,
  user_note, payload
"""


class PostgresTimingRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                _INSERT_SESSION_SQL,
                (
                    user_id,
                    request.activity_id,
                    request.client_session_id,
                    request.mutation.client_device_id,
                    request.mode,
                    "draft" if request.intended_start_at is None else "intent_recorded",
                    request.work_mode,
                    request.actor_mode,
                    request.intended_start_at,
                    request.user_pre_estimate_seconds,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("timing session insert returned no row")
        return _session_from_row(row)

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None:
        session = self._load_session(user_id, session_id)
        if session is None:
            return None
        events = self._load_events(user_id, session_id)
        projection = project_timing_session(session, events)
        session_updates = projection.session_updates
        if session.status in {"reviewed", "discarded"}:
            session_updates = {
                **session_updates,
                "status": session.status,
                "run_quality": session.run_quality,
                "model_inclusion": session.model_inclusion,
                "active_seconds": session.active_seconds,
                "wall_seconds": session.wall_seconds,
                "setup_seconds": session.setup_seconds,
                "detour_seconds": session.detour_seconds,
                "interruption_seconds": session.interruption_seconds,
                "waiting_seconds": session.waiting_seconds,
                "side_quest_seconds": session.side_quest_seconds,
                "start_latency_seconds": session.start_latency_seconds,
                "transition_seconds": session.transition_seconds,
                "needs_timeline_recompute": session.needs_timeline_recompute,
            }
        return session.model_copy(
            update={
                **session_updates,
                "events": projection.ordered_events,
                "spans": self._load_spans(user_id, session_id),
            }
        )

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        session = self._load_session(user_id, session_id)
        if session is None:
            raise KeyError(session_id)

        with self._connection.cursor() as cursor:
            cursor.execute(
                _INSERT_EVENT_SQL,
                (
                    user_id,
                    session_id,
                    request.event_type,
                    request.client_time,
                    request.timer_elapsed_seconds,
                    request.timer_active_seconds,
                    request.mutation.client_sequence,
                    request.mutation.client_mutation_id,
                    request.mutation.client_device_id,
                    request.mutation.idempotency_key,
                    request.capture_context_snapshot_id,
                    request.capture_context_snapshot_ref,
                    Jsonb(request.payload),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("timing event insert returned no row")
        event = _event_from_row(row)
        events = self._load_events(user_id, session_id)
        projection = project_timing_session(session, events)
        self._update_session_projection(user_id, session_id, projection.session_updates)
        return event

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession:
        event_request = AppendTimingEventRequest(
            mutation=request.mutation,
            event_type="session_completed",
            client_time=request.completed_at,
            timer_elapsed_seconds=request.timer_elapsed_seconds,
            timer_active_seconds=request.timer_active_seconds,
            capture_context_snapshot_id=request.capture_context_snapshot_id,
            capture_context_snapshot_ref=request.capture_context_snapshot_ref,
            payload=request.payload,
        )
        self.append_event(user_id, session_id, event_request)
        session = self.get_session(user_id, session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def replace_derived_spans(
        self,
        user_id: UUID,
        session_id: UUID,
        span_drafts: list[TimingEventSpanDraft],
    ) -> list[TimingEventSpan]:
        spans: list[TimingEventSpan] = []
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                delete from timing_event_span
                where user_id = %s and session_id = %s and user_corrected = false
                """,
                (user_id, session_id),
            )
            for draft in span_drafts:
                cursor.execute(
                    _INSERT_SPAN_SQL,
                    (
                        user_id,
                        session_id,
                        draft.checkpoint_run_id,
                        draft.start_event_id,
                        draft.end_event_id,
                        draft.span_type,
                        draft.friction_category,
                        draft.started_at,
                        draft.ended_at,
                        draft.duration_seconds,
                        draft.count_policy,
                        draft.count_in_wall_time,
                        draft.count_in_active_time,
                        draft.model_update_scopes,
                        draft.linked_annotation_id,
                        draft.linked_extracted_event_id,
                        draft.user_corrected,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("timing span insert returned no row")
                spans.append(_span_from_row(row))
        return spans

    def upsert_extracted_event_span(
        self,
        user_id: UUID,
        extracted_event: ExtractedContextEvent,
        *,
        user_corrected: bool,
    ) -> TimingEventSpan:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select occurred_at
                from temporal_context_annotation
                where user_id = %s and id = %s
                """,
                (user_id, extracted_event.annotation_id),
            )
            annotation_row = cursor.fetchone()
            if annotation_row is None:
                raise KeyError(extracted_event.annotation_id)
            started_at = annotation_row["occurred_at"]
            ended_at = (
                started_at + timedelta(seconds=extracted_event.duration_seconds)
                if extracted_event.duration_seconds is not None
                else None
            )
            cursor.execute(
                """
                delete from timing_event_span
                where user_id = %s and linked_extracted_event_id = %s
                """,
                (user_id, extracted_event.id),
            )
            cursor.execute(
                _INSERT_SPAN_SQL,
                (
                    user_id,
                    extracted_event.session_id,
                    extracted_event.checkpoint_run_id,
                    None,
                    None,
                    extracted_event.span_type,
                    extracted_event.friction_category,
                    started_at,
                    ended_at,
                    extracted_event.duration_seconds,
                    extracted_event.count_policy,
                    extracted_event.count_in_wall_time,
                    extracted_event.count_in_active_time,
                    extracted_event.model_update_scopes,
                    extracted_event.annotation_id,
                    extracted_event.id,
                    user_corrected,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("timing span insert returned no row")
            self._update_session_friction_totals(cursor, user_id, extracted_event.session_id)
        return _span_from_row(row)

    def review_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
        span_drafts: list[TimingEventSpanDraft],
        totals: TimingSpanTotals,
    ) -> ModelUpdateDecision:
        if self._load_session(user_id, session_id) is None:
            raise KeyError(session_id)
        self.replace_derived_spans(user_id, session_id, span_drafts)
        payload = {
            "span_overrides": request.span_overrides,
            "reviewed_totals": {
                "wall_seconds": totals.wall_seconds,
                "active_seconds": totals.active_seconds,
                "detour_seconds": totals.detour_seconds,
                "interruption_seconds": totals.interruption_seconds,
            },
        }
        with self._connection.cursor() as cursor:
            cursor.execute(
                _INSERT_REVIEW_SQL,
                (
                    user_id,
                    session_id,
                    request.decision,
                    request.model_inclusion,
                    request.scopes,
                    request.user_note,
                    Jsonb(payload),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("model update decision insert returned no row")
            decision = _decision_from_row(row)
            cursor.execute(
                """
                update timing_session
                set status = %s,
                    run_quality = %s,
                    model_inclusion = %s,
                    active_seconds = %s,
                    wall_seconds = %s,
                    setup_seconds = %s,
                    detour_seconds = %s,
                    interruption_seconds = %s,
                    waiting_seconds = %s,
                    side_quest_seconds = %s,
                    start_latency_seconds = %s,
                    transition_seconds = %s,
                    needs_timeline_recompute = false,
                    review_payload = %s,
                    updated_at = now()
                where user_id = %s and id = %s
                """,
                (
                    status_for_decision(request.decision),
                    run_quality_for_decision(request.decision),
                    request.model_inclusion,
                    totals.active_seconds,
                    totals.wall_seconds,
                    totals.setup_seconds,
                    totals.detour_seconds,
                    totals.interruption_seconds,
                    totals.waiting_seconds,
                    totals.side_quest_seconds,
                    totals.start_latency_seconds,
                    totals.transition_seconds,
                    Jsonb(payload),
                    user_id,
                    session_id,
                ),
            )
            cursor.execute(
                """
                insert into audit_log (
                  user_id, actor_user_id, event_name, entity_type, entity_id, metadata
                )
                values (%s, %s, 'timing.review_saved', 'timing_session', %s, %s)
                """,
                (
                    user_id,
                    user_id,
                    session_id,
                    Jsonb(
                        {
                            "decision": request.decision,
                            "model_inclusion": request.model_inclusion,
                        }
                    ),
                ),
            )
        return decision

    def _load_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                _LOAD_SESSION_SQL,
                (user_id, session_id),
            )
            row = cursor.fetchone()
        return _session_from_row(row) if row is not None else None

    def _load_events(self, user_id: UUID, session_id: UUID) -> list[TimingEvent]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                _LOAD_EVENTS_SQL,
                (user_id, session_id),
            )
            rows = cursor.fetchall()
        return [_event_from_row(row) for row in rows]

    def _load_spans(self, user_id: UUID, session_id: UUID) -> list[TimingEventSpan]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                _LOAD_SPANS_SQL,
                (user_id, session_id),
            )
            rows = cursor.fetchall()
        return [_span_from_row(row) for row in rows]

    def _update_session_projection(
        self,
        user_id: UUID,
        session_id: UUID,
        updates: dict[str, object],
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update timing_session
                set status = %s,
                    started_at = %s,
                    completed_at = %s,
                    wall_seconds = %s,
                    active_seconds = %s,
                    needs_timeline_recompute = %s,
                    updated_at = now()
                where user_id = %s and id = %s
                """,
                (
                    updates["status"],
                    updates["started_at"],
                    updates["completed_at"],
                    updates["wall_seconds"],
                    updates["active_seconds"],
                    updates["needs_timeline_recompute"],
                    user_id,
                    session_id,
                ),
            )

    def _update_session_friction_totals(
        self,
        cursor: psycopg.Cursor[Mapping[str, Any]],
        user_id: UUID,
        session_id: UUID,
    ) -> None:
        cursor.execute(
            """
            select span_type, coalesce(sum(duration_seconds), 0)::integer as seconds
            from timing_event_span
            where user_id = %s and session_id = %s
            group by span_type
            """,
            (user_id, session_id),
        )
        totals = {row["span_type"]: row["seconds"] for row in cursor.fetchall()}
        cursor.execute(
            """
            update timing_session
            set setup_seconds = %s,
                detour_seconds = %s,
                interruption_seconds = %s,
                waiting_seconds = %s,
                side_quest_seconds = %s,
                start_latency_seconds = %s,
                transition_seconds = %s,
                updated_at = now()
            where user_id = %s and id = %s
            """,
            (
                totals.get("setup", 0),
                totals.get("resource_detour", 0),
                totals.get("interruption", 0),
                totals.get("waiting", 0),
                totals.get("side_quest", 0),
                totals.get("start_latency", 0),
                totals.get("transition", 0),
                user_id,
                session_id,
            ),
        )


def _session_from_row(row: Mapping[str, Any]) -> TimingSession:
    data = dict(row)
    data["events"] = []
    data["spans"] = []
    return TimingSession.model_validate(data)


def _event_from_row(row: Mapping[str, Any]) -> TimingEvent:
    data = dict(row)
    data.setdefault("capture_context_snapshot_id", None)
    data.setdefault("capture_context_snapshot_ref", None)
    return TimingEvent.model_validate(data)


def _span_from_row(row: Mapping[str, Any]) -> TimingEventSpan:
    return TimingEventSpan.model_validate(dict(row))


def _decision_from_row(row: Mapping[str, Any]) -> ModelUpdateDecision:
    return ModelUpdateDecision.model_validate(dict(row))
