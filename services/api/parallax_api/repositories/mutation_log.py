from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from ..schemas.common import MutationEnvelope


@dataclass(frozen=True)
class StoredMutation:
    mutation_type: str
    entity_type: str
    entity_id: UUID | None
    result: object


class MutationLogRepository(Protocol):
    def lock(self, user_id: UUID, mutation: MutationEnvelope) -> None: ...

    def get(self, user_id: UUID, mutation: MutationEnvelope) -> StoredMutation | None: ...

    def save(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        entity_id: UUID | None,
        result: BaseModel,
    ) -> None: ...
