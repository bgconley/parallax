from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingEventSpanRequest,
    CreateTimingSessionRequest,
    ModelUpdateDecision,
    ReviewTimingSessionRequest,
    TimingEvent,
    TimingEventSpan,
    TimingSession,
)
from ..services.timing_service import TimingService

router = APIRouter(prefix="/v1/timing/sessions", tags=["timing"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.post("", response_model=TimingSession, status_code=status.HTTP_201_CREATED)
def create_timing_session(
    payload: CreateTimingSessionRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingSession:
    return TimingService(uow_factory).create_session(auth.user_id, payload)


@router.get("/{session_id}", response_model=TimingSession)
def get_timing_session(
    session_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingSession:
    return TimingService(uow_factory).get_session(auth.user_id, session_id)


@router.post(
    "/{session_id}/events",
    response_model=TimingEvent,
    status_code=status.HTTP_201_CREATED,
)
def append_timing_event(
    session_id: UUID,
    payload: AppendTimingEventRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingEvent:
    return TimingService(uow_factory).append_event(auth.user_id, session_id, payload)


@router.post(
    "/{session_id}/event-spans",
    response_model=TimingEventSpan,
    status_code=status.HTTP_201_CREATED,
)
def create_timing_event_span(
    session_id: UUID,
    payload: CreateTimingEventSpanRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingEventSpan:
    return TimingService(uow_factory).create_or_correct_span(auth.user_id, session_id, payload)


@router.post("/{session_id}/complete", response_model=TimingSession)
def complete_timing_session(
    session_id: UUID,
    payload: CompleteTimingSessionRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingSession:
    return TimingService(uow_factory).complete_session(auth.user_id, session_id, payload)


@router.post("/{session_id}/review", response_model=ModelUpdateDecision)
def review_timing_session(
    session_id: UUID,
    payload: ReviewTimingSessionRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ModelUpdateDecision:
    return TimingService(uow_factory).review_session(auth.user_id, session_id, payload)


@router.post("/{session_id}/discard", response_model=ModelUpdateDecision)
def discard_timing_session(
    session_id: UUID,
    payload: ReviewTimingSessionRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ModelUpdateDecision:
    return TimingService(uow_factory).discard_session(auth.user_id, session_id, payload)
