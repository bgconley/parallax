from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.common import MutationEnvelope
from ..schemas.sync import SyncPushRequest, SyncPushResponse
from .mutations import MutationReplayService

_PHASE1_MUTATING_OPERATIONS = {
    "create_activity": ("/v1/activities",),
    "createActivity": ("/v1/activities",),
    "create_timing_session": ("/v1/timing/sessions",),
    "createTimingSession": ("/v1/timing/sessions",),
    "append_timing_event": ("/v1/timing/sessions/", "/events"),
    "appendTimingEvent": ("/v1/timing/sessions/", "/events"),
    "complete_timing_session": ("/v1/timing/sessions/", "/complete"),
    "completeTimingSession": ("/v1/timing/sessions/", "/complete"),
}


class SyncService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def push(self, user_id: UUID, request: SyncPushRequest) -> SyncPushResponse:
        self._validate_nested_mutations(request)

        with self._uow_factory() as uow:
            mutations = MutationReplayService(uow.mutations)

            def apply() -> tuple[UUID | None, SyncPushResponse]:
                return None, SyncPushResponse(
                    accepted=True,
                    operation_count=len(request.mutations),
                    server_time=datetime.now(UTC),
                )

            return mutations.replay_or_apply(
                user_id=user_id,
                mutation=request.mutation,
                mutation_type="sync_push",
                entity_type="sync_batch",
                result_type=SyncPushResponse,
                apply=apply,
            )

    @staticmethod
    def _validate_nested_mutations(request: SyncPushRequest) -> None:
        for index, operation in enumerate(request.mutations):
            path_parts = _PHASE1_MUTATING_OPERATIONS.get(operation.operation)
            if path_parts is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "unsupported_sync_operation",
                        "message": "sync operation is not supported in Phase 1",
                        "details": {"operation_index": index, "operation": operation.operation},
                        "retryable": False,
                    },
                )
            if not _path_matches(operation.path, path_parts):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation path does not match operation type",
                        "details": {"operation_index": index, "operation": operation.operation},
                        "retryable": False,
                    },
                )
            nested_mutation = operation.body.get("mutation")
            if nested_mutation is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation is missing its mutation envelope",
                        "details": {"operation_index": index},
                        "retryable": False,
                    },
                )
            try:
                MutationEnvelope.model_validate(nested_mutation)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation has invalid mutation envelope",
                        "details": {"operation_index": index},
                        "retryable": False,
                    },
                ) from exc


def _path_matches(path: str, expected_parts: tuple[str, ...]) -> bool:
    if len(expected_parts) == 1:
        return path == expected_parts[0]
    return path.startswith(expected_parts[0]) and path.endswith(expected_parts[1])
