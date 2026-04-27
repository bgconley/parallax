from __future__ import annotations

from types import TracebackType
from typing import Literal, Protocol
from uuid import UUID

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    TimingEvent,
    TimingSession,
)
from .mutation_log import MutationLogRepository


class ActivityRepositoryProtocol(Protocol):
    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity: ...

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]: ...

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None: ...

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]: ...


class TimingRepositoryProtocol(Protocol):
    def create_session(
        self,
        user_id: UUID,
        request: CreateTimingSessionRequest,
    ) -> TimingSession: ...

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None: ...

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent: ...

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession: ...


class UnitOfWork(Protocol):
    activities: ActivityRepositoryProtocol
    timing: TimingRepositoryProtocol
    mutations: MutationLogRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
