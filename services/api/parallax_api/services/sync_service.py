from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

from ..repositories.mutation_log import StoredSyncChange
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse
from .mutations import MutationReplayService
from .sync_operations import apply_sync_operations, parse_sync_operations


class SyncService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def push(self, user_id: UUID, request: SyncPushRequest) -> SyncPushResponse:
        operations = parse_sync_operations(request)

        with self._uow_factory() as uow:
            mutations = MutationReplayService(uow.mutations)

            def apply() -> tuple[UUID | None, SyncPushResponse]:
                apply_sync_operations(uow, user_id, operations)
                return None, SyncPushResponse(
                    accepted=True,
                    operation_count=len(operations),
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

    def pull(self, user_id: UUID, cursor: str | None, limit: int) -> SyncPullResponse:
        try:
            with self._uow_factory() as uow:
                changes = uow.mutations.list_changes(user_id, cursor=cursor, limit=limit)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "invalid_sync_cursor",
                    "message": "sync cursor is invalid",
                    "details": {},
                    "retryable": False,
                },
            ) from exc
        server_time = datetime.now(UTC)
        return SyncPullResponse(
            cursor=changes[-1].cursor if changes else (cursor or _empty_pull_cursor(server_time)),
            changes=[_change_payload(change) for change in changes],
            server_time=server_time,
        )


def _change_payload(change: StoredSyncChange) -> dict[str, object]:
    result = (
        change.result.model_dump(mode="json")
        if isinstance(change.result, BaseModel)
        else change.result
    )
    payload: dict[str, object] = {
        "cursor": change.cursor,
        "mutation_type": change.mutation_type,
        "entity_type": change.entity_type,
        "entity_id": str(change.entity_id) if change.entity_id else None,
        "received_at": change.received_at.isoformat(),
        "result": result if isinstance(result, dict) else {"value": result},
    }
    return payload


def _empty_pull_cursor(server_time: datetime) -> str:
    return f"{server_time.isoformat()}|{UUID(int=0)}"
