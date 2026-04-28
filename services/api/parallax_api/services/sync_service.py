from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

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
        return SyncPullResponse(
            cursor=cursor or datetime.now(UTC).isoformat(),
            changes=[],
            server_time=datetime.now(UTC),
        )
