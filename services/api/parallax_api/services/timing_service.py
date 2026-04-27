from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.activity_repository import ActivityRepository
from ..repositories.memory import InMemoryStore
from ..repositories.timing_repository import TimingRepository
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    TimingEvent,
    TimingSession,
)
from .mutations import MutationReplayService


class TimingService:
    def __init__(self, store: InMemoryStore) -> None:
        self._activities = ActivityRepository(store)
        self._timing = TimingRepository(store)
        self._mutations = MutationReplayService(store)

    def create_session(self, user_id: UUID, request: CreateTimingSessionRequest) -> TimingSession:
        if self._activities.get(user_id, request.activity_id) is None:
            raise HTTPException(status_code=404, detail="activity not found")

        def apply() -> tuple[UUID, TimingSession]:
            session = self._timing.create_session(user_id, request)
            return session.id, session

        return self._mutations.replay_or_apply(
            user_id=user_id,
            mutation=request.mutation,
            mutation_type="create_timing_session",
            entity_type="timing_session",
            apply=apply,
        )

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession:
        session = self._timing.get_session(user_id, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="timing session not found")
        return session

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent:
        self.get_session(user_id, session_id)

        def apply() -> tuple[UUID, TimingEvent]:
            event = self._timing.append_event(user_id, session_id, request)
            return event.id, event

        return self._mutations.replay_or_apply(
            user_id=user_id,
            mutation=request.mutation,
            mutation_type="append_timing_event",
            entity_type="timing_event",
            apply=apply,
        )

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession:
        self.get_session(user_id, session_id)

        def apply() -> tuple[UUID, TimingSession]:
            session = self._timing.complete_session(user_id, session_id, request)
            return session.id, session

        return self._mutations.replay_or_apply(
            user_id=user_id,
            mutation=request.mutation,
            mutation_type="complete_timing_session",
            entity_type="timing_session",
            apply=apply,
        )
