from __future__ import annotations

from typing import overload
from uuid import UUID

from fastapi import HTTPException

from ..domain.review_decisions import is_discard_decision, is_model_inclusion_allowed
from ..domain.timing_spans import derive_timing_spans, summarize_timing_spans
from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    ModelUpdateDecision,
    ReviewTimingSessionRequest,
    TimingEvent,
    TimingSession,
)
from .mutations import MutationReplayService


class TimingService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        with self._uow_factory() as uow:
            return create_session_in_uow(uow, user_id, request)

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession:
        with self._uow_factory() as uow:
            session = uow.timing.get_session(user_id, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="timing session not found")
        return session

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        with self._uow_factory() as uow:
            return append_event_in_uow(uow, user_id, session_id, request)

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession:
        with self._uow_factory() as uow:
            return complete_session_in_uow(uow, user_id, session_id, request)

    def review_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
    ) -> ModelUpdateDecision:
        return self._save_review_decision(user_id, session_id, request, discard_endpoint=False)

    def discard_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
    ) -> ModelUpdateDecision:
        return self._save_review_decision(user_id, session_id, request, discard_endpoint=True)

    def _save_review_decision(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
        *,
        discard_endpoint: bool,
    ) -> ModelUpdateDecision:
        if not is_model_inclusion_allowed(request):
            raise HTTPException(
                status_code=400,
                detail="model_inclusion is not valid for review decision",
            )
        if discard_endpoint and not is_discard_decision(request.decision):
            raise HTTPException(
                status_code=400,
                detail="discard endpoint requires discard decision",
            )
        if not discard_endpoint and is_discard_decision(request.decision):
            raise HTTPException(status_code=400, detail="discard decisions use discard endpoint")

        with self._uow_factory() as uow:
            return save_review_decision_in_uow(
                uow,
                user_id,
                session_id,
                request,
                discard_endpoint=discard_endpoint,
            )


def create_session_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: CreateTimingSessionRequest,
) -> TimingSession:
    if uow.activities.get(user_id, request.activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingSession]:
        session = uow.timing.create_session(user_id, request)
        return session.id, session

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_timing_session",
        entity_type="timing_session",
        result_type=TimingSession,
        apply=apply,
    )


def append_event_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: AppendTimingEventRequest,
) -> TimingEvent:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    resolved_request = _with_resolved_context_snapshot(uow, user_id, request)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingEvent]:
        event = uow.timing.append_event(user_id, session_id, resolved_request)
        return event.id, event

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=resolved_request.mutation,
        mutation_type="append_timing_event",
        entity_type="timing_event",
        result_type=TimingEvent,
        apply=apply,
    )


def complete_session_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: CompleteTimingSessionRequest,
) -> TimingSession:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    resolved_request = _with_resolved_context_snapshot(uow, user_id, request)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingSession]:
        session = uow.timing.complete_session(user_id, session_id, resolved_request)
        return session.id, session

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=resolved_request.mutation,
        mutation_type="complete_timing_session",
        entity_type="timing_session",
        result_type=TimingSession,
        apply=apply,
    )


def save_review_decision_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: ReviewTimingSessionRequest,
    *,
    discard_endpoint: bool,
) -> ModelUpdateDecision:
    if not is_model_inclusion_allowed(request):
        raise HTTPException(
            status_code=400,
            detail="model_inclusion is not valid for review decision",
        )
    if discard_endpoint and not is_discard_decision(request.decision):
        raise HTTPException(
            status_code=400,
            detail="discard endpoint requires discard decision",
        )
    if not discard_endpoint and is_discard_decision(request.decision):
        raise HTTPException(status_code=400, detail="discard decisions use discard endpoint")

    session = uow.timing.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    if session.completed_at is None:
        raise HTTPException(status_code=400, detail="timing session is not complete")

    span_drafts = derive_timing_spans(session, session.events)
    totals = summarize_timing_spans(session, span_drafts)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ModelUpdateDecision]:
        decision = uow.timing.review_session(
            user_id,
            session_id,
            request,
            span_drafts,
            totals,
        )
        uow.profiles.recompute_activity_stats(user_id, session.activity_id)
        return decision.id, decision

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="discard_timing_session" if discard_endpoint else "review_timing_session",
        entity_type="model_update_decision",
        result_type=ModelUpdateDecision,
        apply=apply,
    )


@overload
def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: AppendTimingEventRequest,
) -> AppendTimingEventRequest: ...


@overload
def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: CompleteTimingSessionRequest,
) -> CompleteTimingSessionRequest: ...


def _with_resolved_context_snapshot(
    uow: UnitOfWork,
    user_id: UUID,
    request: AppendTimingEventRequest | CompleteTimingSessionRequest,
) -> AppendTimingEventRequest | CompleteTimingSessionRequest:
    if (
        request.capture_context_snapshot_id is not None
        or request.capture_context_snapshot_ref is None
    ):
        return request
    snapshot_id = uow.contexts.snapshot_id_for_reference(
        user_id,
        request.capture_context_snapshot_ref,
    )
    if snapshot_id is None:
        return request
    return request.model_copy(update={"capture_context_snapshot_id": snapshot_id})
