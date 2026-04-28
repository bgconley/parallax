from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from ..repositories.mutation_log import MutationLogRepository
from ..schemas.common import MutationEnvelope

T = TypeVar("T", bound=BaseModel)


class MutationReplayService:
    def __init__(self, mutation_log: MutationLogRepository) -> None:
        self._mutation_log = mutation_log

    def replay_or_apply(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        result_type: type[T],
        apply: Callable[[], tuple[UUID | None, T]],
    ) -> T:
        self._mutation_log.lock(user_id, mutation)
        existing = self._mutation_log.get(user_id, mutation)
        if existing is not None:
            return result_type.model_validate(existing.result)

        entity_id, result = apply()
        self._mutation_log.save(
            user_id=user_id,
            mutation=mutation,
            mutation_type=mutation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
        )
        return result
