from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from types import TracebackType
from typing import Literal

from .activity_repository import ActivityRepository
from .context_repository import ContextRepository
from .memory import InMemoryMutationLogRepository, InMemoryStore
from .mutation_log import MutationLogRepository
from .profile_repository import ProfileRepository
from .timing_repository import TimingRepository
from .unit_of_work import (
    ActivityRepositoryProtocol,
    ContextRepositoryProtocol,
    ProfileRepositoryProtocol,
    TimingRepositoryProtocol,
)


class InMemoryUnitOfWork:
    activities: ActivityRepositoryProtocol
    timing: TimingRepositoryProtocol
    profiles: ProfileRepositoryProtocol
    contexts: ContextRepositoryProtocol
    mutations: MutationLogRepository

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self._rollback_snapshot: InMemoryStore | None = None
        self.activities = ActivityRepository(store)
        self.timing = TimingRepository(store)
        self.profiles = ProfileRepository(store)
        self.contexts = ContextRepository(store)
        self.mutations = InMemoryMutationLogRepository(store)

    def __enter__(self) -> InMemoryUnitOfWork:
        self._rollback_snapshot = deepcopy(self._store)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None and self._rollback_snapshot is not None:
            for field in fields(InMemoryStore):
                setattr(self._store, field.name, getattr(self._rollback_snapshot, field.name))
        self._rollback_snapshot = None
        return False


class InMemoryUnitOfWorkFactory:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store or InMemoryStore()

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.store)
