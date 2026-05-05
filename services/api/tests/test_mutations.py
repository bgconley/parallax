from datetime import datetime
from uuid import UUID

import pytest
from fastapi import HTTPException
from parallax_api.repositories.mutation_log import StoredMutation, StoredSyncChange
from parallax_api.schemas.common import MutationEnvelope
from parallax_api.services.mutations import MutationReplayService
from pydantic import BaseModel


class ResultModel(BaseModel):
    value: str


class RecordingMutationLog:
    def __init__(self, existing: StoredMutation | None = None) -> None:
        self.calls: list[str] = []
        self.existing = existing

    def lock(self, user_id: UUID, mutation: MutationEnvelope) -> None:
        self.calls.append("lock")

    def get(self, user_id: UUID, mutation: MutationEnvelope) -> StoredMutation | None:
        self.calls.append("get")
        return self.existing

    def list_changes(
        self,
        user_id: UUID,
        *,
        cursor: str | None,
        limit: int,
    ) -> list[StoredSyncChange]:
        return []

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


def test_mutation_replay_returns_existing_matching_result() -> None:
    mutation = MutationEnvelope(
        client_mutation_id="mut-1",
        client_device_id="device-1",
        client_timestamp=datetime.fromisoformat("2026-04-27T12:00:00+00:00"),
        idempotency_key="device-1:mut-1",
    )
    repository = RecordingMutationLog(
        existing=StoredMutation(
            mutation_type="test",
            entity_type="test_entity",
            entity_id=None,
            result={"value": "existing"},
        )
    )

    result = MutationReplayService(repository).replay_or_apply(
        user_id=UUID("00000000-0000-0000-0000-0000000000d1"),
        mutation=mutation,
        mutation_type="test",
        entity_type="test_entity",
        result_type=ResultModel,
        apply=lambda: (None, ResultModel(value="created")),
    )

    assert result == ResultModel(value="existing")
    assert repository.calls == ["lock", "get"]


def test_mutation_replay_rejects_idempotency_key_reused_for_different_mutation() -> None:
    mutation = MutationEnvelope(
        client_mutation_id="mut-1",
        client_device_id="device-1",
        client_timestamp=datetime.fromisoformat("2026-04-27T12:00:00+00:00"),
        idempotency_key="device-1:mut-1",
    )
    repository = RecordingMutationLog(
        existing=StoredMutation(
            mutation_type="append_timing_event",
            entity_type="timing_event",
            entity_id=None,
            result={"event_type": "session_started"},
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        MutationReplayService(repository).replay_or_apply(
            user_id=UUID("00000000-0000-0000-0000-0000000000d1"),
            mutation=mutation,
            mutation_type="decide_preflight_check",
            entity_type="preflight_check",
            result_type=ResultModel,
            apply=lambda: (None, ResultModel(value="created")),
        )

    assert exc_info.value.status_code == 409
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["error_code"] == "idempotency_key_conflict"
    assert detail["details"] == {
        "expected_mutation_type": "decide_preflight_check",
        "expected_entity_type": "preflight_check",
        "existing_mutation_type": "append_timing_event",
        "existing_entity_type": "timing_event",
    }
    assert repository.calls == ["lock", "get"]
