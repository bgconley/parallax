from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from ..repositories.memory import InMemoryStore, MutationKey, MutationRecord
from ..schemas.common import MutationEnvelope

T = TypeVar("T")


class MutationReplayService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def replay_or_apply(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        apply: Callable[[], tuple[UUID, T]],
    ) -> T:
        key = self._key(user_id, mutation)
        if key in self._store.mutation_records:
            return self._store.mutation_records[key].result  # type: ignore[return-value]

        entity_id, result = apply()
        self._store.mutation_records[key] = MutationRecord(
            mutation_type=mutation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
        )
        return result

    @staticmethod
    def _key(user_id: UUID, mutation: MutationEnvelope) -> MutationKey:
        return (user_id, mutation.client_device_id, mutation.client_mutation_id)
