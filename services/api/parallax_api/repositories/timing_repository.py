from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ..domain.latency_observations import (
    StartLatencyObservationDraft,
    TransitionObservationDraft,
)
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
from .checkpoint_run_state import (
    apply_checkpoint_event,
    checkpoint_event_payload,
    create_checkpoint_runs_for_session,
)
from .latency_observation_state import (
    replace_latency_observations as replace_memory_latency_observations,
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
        self._store.session_spans[session.id] = []
        create_checkpoint_runs_for_session(self._store, user_id, session)
        return session

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None:
        session = self._store.sessions.get(session_id)
        if session is None or session.user_id != user_id:
            return None
        events = list(self._store.session_events.get(session_id, []))
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
                "spans": list(self._store.session_spans.get(session_id, [])),
            }
        )

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        session = self._store.sessions[session_id]
        payload = checkpoint_event_payload(self._store, user_id, session, request)
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
            payload=payload,
        )
        self._store.session_events[session_id].append(event)
        apply_checkpoint_event(self._store, event)
        events = list(self._store.session_events[session_id])
        projection = project_timing_session(session, events)
        self._store.sessions[session_id] = session.model_copy(update=projection.session_updates)
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
        updated = self.get_session(user_id, session_id)
        if updated is None:
            raise KeyError(session_id)
        self._store.sessions[session_id] = updated.model_copy(update={"events": []})
        return updated

    def replace_derived_spans(
        self,
        user_id: UUID,
        session_id: UUID,
        span_drafts: list[TimingEventSpanDraft],
    ) -> list[TimingEventSpan]:
        spans = [
            TimingEventSpan(
                id=uuid4(),
                user_id=user_id,
                session_id=session_id,
                checkpoint_run_id=draft.checkpoint_run_id,
                span_type=draft.span_type,
                friction_category=draft.friction_category,
                started_at=draft.started_at,
                ended_at=draft.ended_at,
                duration_seconds=draft.duration_seconds,
                count_policy=draft.count_policy,
                count_in_wall_time=draft.count_in_wall_time,
                count_in_active_time=draft.count_in_active_time,
                model_update_scopes=draft.model_update_scopes,
                linked_annotation_id=draft.linked_annotation_id,
                linked_extracted_event_id=draft.linked_extracted_event_id,
                user_corrected=draft.user_corrected,
            )
            for draft in span_drafts
        ]
        self._store.session_spans[session_id] = spans
        return spans

    def upsert_extracted_event_span(
        self,
        user_id: UUID,
        extracted_event: ExtractedContextEvent,
        *,
        user_corrected: bool,
    ) -> TimingEventSpan:
        annotation = self._store.annotations[extracted_event.annotation_id]
        started_at = annotation.occurred_at
        ended_at = (
            started_at + timedelta(seconds=extracted_event.duration_seconds)
            if extracted_event.duration_seconds is not None
            else None
        )
        span = TimingEventSpan(
            id=uuid4(),
            user_id=user_id,
            session_id=extracted_event.session_id,
            checkpoint_run_id=extracted_event.checkpoint_run_id,
            span_type=extracted_event.span_type,
            friction_category=extracted_event.friction_category,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=extracted_event.duration_seconds,
            count_policy=extracted_event.count_policy,
            count_in_wall_time=extracted_event.count_in_wall_time,
            count_in_active_time=extracted_event.count_in_active_time,
            model_update_scopes=extracted_event.model_update_scopes,
            linked_annotation_id=extracted_event.annotation_id,
            linked_extracted_event_id=extracted_event.id,
            user_corrected=user_corrected,
        )
        existing_spans = self._store.session_spans.get(extracted_event.session_id, [])
        self._store.session_spans[extracted_event.session_id] = [
            existing
            for existing in existing_spans
            if existing.linked_extracted_event_id != extracted_event.id
        ] + [span]
        _update_session_friction_totals(self._store, user_id, extracted_event.session_id)
        return span

    def create_or_correct_span(
        self,
        user_id: UUID,
        session_id: UUID,
        span: TimingEventSpan,
    ) -> TimingEventSpan:
        stored = span.model_copy(
            update={
                "user_id": user_id,
                "session_id": session_id,
                "user_corrected": True,
            }
        )
        existing_spans = self._store.session_spans.get(session_id, [])
        self._store.session_spans[session_id] = [
            existing for existing in existing_spans if existing.id != stored.id
        ] + [stored]
        _update_session_friction_totals(self._store, user_id, session_id)
        return stored

    def review_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
        span_drafts: list[TimingEventSpanDraft],
        totals: TimingSpanTotals,
    ) -> ModelUpdateDecision:
        session = self.get_session(user_id, session_id)
        if session is None:
            raise KeyError(session_id)
        self.replace_derived_spans(user_id, session_id, span_drafts)
        reviewed_at = datetime.now(UTC)
        decision = ModelUpdateDecision(
            id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            decision=request.decision,
            model_inclusion=request.model_inclusion,
            scopes=request.scopes,
            reviewed_at=reviewed_at,
            user_note=request.user_note,
            payload={
                "span_overrides": request.span_overrides,
                "reviewed_totals": {
                    "wall_seconds": totals.wall_seconds,
                    "active_seconds": totals.active_seconds,
                    "detour_seconds": totals.detour_seconds,
                    "interruption_seconds": totals.interruption_seconds,
                },
            },
        )
        self._store.session_events.setdefault(session_id, []).append(
            TimingEvent(
                id=uuid4(),
                user_id=user_id,
                session_id=session_id,
                event_type="review_saved",
                client_time=reviewed_at,
                server_time=reviewed_at,
                timer_elapsed_seconds=totals.wall_seconds,
                timer_active_seconds=totals.active_seconds,
                client_sequence=request.mutation.client_sequence,
                client_mutation_id=request.mutation.client_mutation_id,
                client_device_id=request.mutation.client_device_id,
                idempotency_key=request.mutation.idempotency_key,
                capture_context_snapshot_id=None,
                capture_context_snapshot_ref=None,
                payload={
                    "model_update_decision_id": str(decision.id),
                    "decision": request.decision,
                    "model_inclusion": request.model_inclusion,
                    "scopes": request.scopes,
                },
            )
        )
        self._store.review_decisions.setdefault(session_id, []).append(decision)
        self._store.sessions[session_id] = session.model_copy(
            update={
                "status": status_for_decision(request.decision),
                "run_quality": run_quality_for_decision(request.decision),
                "model_inclusion": request.model_inclusion,
                "active_seconds": totals.active_seconds,
                "wall_seconds": totals.wall_seconds,
                "setup_seconds": totals.setup_seconds,
                "detour_seconds": totals.detour_seconds,
                "interruption_seconds": totals.interruption_seconds,
                "waiting_seconds": totals.waiting_seconds,
                "side_quest_seconds": totals.side_quest_seconds,
                "start_latency_seconds": totals.start_latency_seconds,
                "transition_seconds": totals.transition_seconds,
                "needs_timeline_recompute": False,
                "events": [],
                "spans": [],
            }
        )
        return decision

    def replace_latency_observations(
        self,
        user_id: UUID,
        session: TimingSession,
        start_latency: StartLatencyObservationDraft | None,
        transitions: list[TransitionObservationDraft],
    ) -> None:
        replace_memory_latency_observations(
            self._store,
            user_id,
            session,
            start_latency,
            transitions,
        )


def _update_session_friction_totals(
    store: InMemoryStore,
    user_id: UUID,
    session_id: UUID,
) -> None:
    session = store.sessions.get(session_id)
    if session is None or session.user_id != user_id:
        return
    spans = store.session_spans.get(session_id, [])
    totals = {
        "setup_seconds": 0,
        "detour_seconds": 0,
        "interruption_seconds": 0,
        "waiting_seconds": 0,
        "side_quest_seconds": 0,
        "start_latency_seconds": 0,
        "transition_seconds": 0,
    }
    span_to_total = {
        "setup": "setup_seconds",
        "resource_detour": "detour_seconds",
        "interruption": "interruption_seconds",
        "waiting": "waiting_seconds",
        "side_quest": "side_quest_seconds",
        "start_latency": "start_latency_seconds",
        "transition": "transition_seconds",
    }
    for span in spans:
        total_name = span_to_total.get(span.span_type)
        if total_name is not None:
            totals[total_name] += span.duration_seconds or 0
    store.sessions[session_id] = session.model_copy(update=totals)
