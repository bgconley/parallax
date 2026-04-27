from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    TimingEvent,
    TimingSession,
)
from .memory import InMemoryStore


class TimingRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        session = TimingSession(
            id=uuid4(),
            user_id=user_id,
            activity_id=request.activity_id,
            client_session_id=request.client_session_id,
            source_device_id=request.mutation.client_device_id,
            mode=request.mode,
            status="draft" if request.intended_start_at is None else "intent_recorded",
            work_mode=request.work_mode,
            actor_mode=request.actor_mode,
            intended_start_at=request.intended_start_at,
            started_at=None,
            completed_at=None,
            run_quality="unknown",
            model_inclusion="not_reviewed",
            needs_timeline_recompute=False,
        )
        self._store.sessions[session.id] = session
        self._store.session_events[session.id] = []
        return session

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None:
        session = self._store.sessions.get(session_id)
        if session is None or session.user_id != user_id:
            return None
        events = list(self._store.session_events.get(session_id, []))
        return session.model_copy(update={"events": events})

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        session = self._store.sessions[session_id]
        event = TimingEvent(
            id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            event_type=request.event_type,
            client_time=request.client_time,
            server_time=datetime.now(UTC),
            timer_elapsed_seconds=request.timer_elapsed_seconds,
            timer_active_seconds=request.timer_active_seconds,
            client_sequence=request.mutation.client_sequence,
            client_mutation_id=request.mutation.client_mutation_id,
            client_device_id=request.mutation.client_device_id,
            idempotency_key=request.mutation.idempotency_key,
            capture_context_snapshot_id=request.capture_context_snapshot_id,
            capture_context_snapshot_ref=request.capture_context_snapshot_ref,
            payload=request.payload,
        )
        self._store.session_events[session_id].append(event)
        self._store.sessions[session_id] = _session_after_event(session, event)
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
        updated = self._store.sessions[session_id].model_copy(
            update={
                "status": "completed_unreviewed",
                "completed_at": request.completed_at,
                "wall_seconds": request.timer_elapsed_seconds,
                "active_seconds": request.timer_active_seconds,
            }
        )
        self._store.sessions[session_id] = updated
        return self.get_session(user_id, session_id) or updated


def _session_after_event(session: TimingSession, event: TimingEvent) -> TimingSession:
    updates: dict[str, object] = {"needs_timeline_recompute": True}
    if event.event_type == "session_started":
        updates["status"] = "running"
        updates["started_at"] = event.client_time
    elif event.event_type == "session_paused":
        updates["status"] = "paused"
    elif event.event_type == "session_resumed":
        updates["status"] = "running"
    elif event.event_type == "session_abandoned":
        updates["status"] = "abandoned"
    return session.model_copy(update=updates)
