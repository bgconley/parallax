from datetime import datetime
from uuid import UUID

from parallax_api.repositories.mutation_log import StoredMutation
from parallax_api.schemas.common import MutationEnvelope
from parallax_api.services.mutations import MutationReplayService
from pydantic import BaseModel


class ResultModel(BaseModel):
    value: str


class RecordingMutationLog:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def lock(self, user_id: UUID, mutation: MutationEnvelope) -> None:
        self.calls.append("lock")

    def get(self, user_id: UUID, mutation: MutationEnvelope) -> StoredMutation | None:
        self.calls.append("get")
        return None

    def save(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        entity_id: UUID | None,
        result: BaseModel,
    ) -> None:
        self.calls.append("save")


def test_mutation_replay_locks_before_lookup_and_apply() -> None:
    mutation = MutationEnvelope(
        client_mutation_id="mut-1",
        client_device_id="device-1",
        client_timestamp=datetime.fromisoformat("2026-04-27T12:00:00+00:00"),
        idempotency_key="device-1:mut-1",
    )
    repository = RecordingMutationLog()

    result = MutationReplayService(repository).replay_or_apply(
        user_id=UUID("00000000-0000-0000-0000-0000000000d1"),
        mutation=mutation,
        mutation_type="test",
        entity_type="test_entity",
        result_type=ResultModel,
        apply=lambda: (None, ResultModel(value="created")),
    )

    assert result == ResultModel(value="created")
    assert repository.calls == ["lock", "get", "save"]
