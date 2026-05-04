from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

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
            if existing.mutation_type != mutation_type or existing.entity_type != entity_type:
                raise _idempotency_conflict(
                    expected_mutation_type=mutation_type,
                    expected_entity_type=entity_type,
                    existing_mutation_type=existing.mutation_type,
                    existing_entity_type=existing.entity_type,
                )
            try:
                return result_type.model_validate(existing.result)
            except ValidationError as exc:
                raise _idempotency_conflict(
                    expected_mutation_type=mutation_type,
                    expected_entity_type=entity_type,
                    existing_mutation_type=existing.mutation_type,
                    existing_entity_type=existing.entity_type,
                ) from exc

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


def _idempotency_conflict(
    *,
    expected_mutation_type: str,
    expected_entity_type: str,
    existing_mutation_type: str,
    existing_entity_type: str,
) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error_code": "idempotency_key_conflict",
            "message": "idempotency key was already used for a different mutation result",
            "details": {
                "expected_mutation_type": expected_mutation_type,
                "expected_entity_type": expected_entity_type,
                "existing_mutation_type": existing_mutation_type,
                "existing_entity_type": existing_entity_type,
            },
            "retryable": False,
        },
    )
