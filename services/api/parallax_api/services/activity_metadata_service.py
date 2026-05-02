from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity_metadata import (
    CheckpointTemplate,
    PutCheckpointsRequest,
)
from ..schemas.common import ApiModel
from .mutations import MutationReplayService


class ActivityMetadataService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def list_checkpoints(self, user_id: UUID, activity_id: UUID) -> list[CheckpointTemplate]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_checkpoints(user_id, activity_id)

    def replace_checkpoints(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: PutCheckpointsRequest,
    ) -> list[CheckpointTemplate]:
        with self._uow_factory() as uow:
            return replace_checkpoints_in_uow(uow, user_id, activity_id, request)


def replace_checkpoints_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: PutCheckpointsRequest,
) -> list[CheckpointTemplate]:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID | None, CheckpointTemplateList]:
        checkpoints = uow.activities.replace_checkpoints(user_id, activity_id, request)
        return None, CheckpointTemplateList(items=checkpoints)

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="replace_checkpoints",
        entity_type="checkpoint_template",
        result_type=CheckpointTemplateList,
        apply=apply,
    ).items


class CheckpointTemplateList(ApiModel):
    items: list[CheckpointTemplate]


def _require_activity(uow: UnitOfWork, user_id: UUID, activity_id: UUID) -> None:
    if uow.activities.get(user_id, activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
