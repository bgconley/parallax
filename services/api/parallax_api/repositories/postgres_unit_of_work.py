from __future__ import annotations

from types import TracebackType
from typing import Any, Literal

import psycopg
from psycopg.rows import dict_row

from .postgres_activity_repository import PostgresActivityRepository
from .postgres_context_repository import PostgresContextRepository
from .postgres_mutation_log import PostgresMutationLogRepository
from .postgres_profile_repository import PostgresProfileRepository
from .postgres_timing_repository import PostgresTimingRepository
from .unit_of_work import (
    ActivityRepositoryProtocol,
    ContextRepositoryProtocol,
    ProfileRepositoryProtocol,
    TimingRepositoryProtocol,
)


class PostgresUnitOfWork:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._connection: psycopg.Connection[Any] | None = None
        self.activities: ActivityRepositoryProtocol
        self.timing: TimingRepositoryProtocol
        self.profiles: ProfileRepositoryProtocol
        self.contexts: ContextRepositoryProtocol
        self.mutations: PostgresMutationLogRepository

    def __enter__(self) -> PostgresUnitOfWork:
        self._connection = psycopg.connect(self._database_url, row_factory=dict_row)
        self.activities = PostgresActivityRepository(self._connection)
        self.timing = PostgresTimingRepository(self._connection)
        self.profiles = PostgresProfileRepository(self._connection)
        self.contexts = PostgresContextRepository(self._connection)
        self.mutations = PostgresMutationLogRepository(self._connection)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if self._connection is None:
            return False
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False


class PostgresUnitOfWorkFactory:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._database_url)
