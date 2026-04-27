from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    TimingEvent,
    TimingSession,
)
from .mutations import MutationReplayService


class TimingService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        with self._uow_factory() as uow:
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
            if uow.timing.get_session(user_id, session_id) is None:
                raise HTTPException(status_code=404, detail="timing session not found")
            mutations = MutationReplayService(uow.mutations)

            def apply() -> tuple[UUID, TimingEvent]:
                event = uow.timing.append_event(user_id, session_id, request)
                return event.id, event

            return mutations.replay_or_apply(
                user_id=user_id,
                mutation=request.mutation,
                mutation_type="append_timing_event",
                entity_type="timing_event",
                result_type=TimingEvent,
                apply=apply,
            )

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession:
        with self._uow_factory() as uow:
            if uow.timing.get_session(user_id, session_id) is None:
                raise HTTPException(status_code=404, detail="timing session not found")
            mutations = MutationReplayService(uow.mutations)

            def apply() -> tuple[UUID, TimingSession]:
                session = uow.timing.complete_session(user_id, session_id, request)
                return session.id, session

            return mutations.replay_or_apply(
                user_id=user_id,
                mutation=request.mutation,
                mutation_type="complete_timing_session",
                entity_type="timing_session",
                result_type=TimingSession,
                apply=apply,
            )
