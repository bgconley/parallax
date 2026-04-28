from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityRelationship,
    AddActivityAliasRequest,
    CheckpointTemplate,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    PreflightCheck,
    PutCheckpointsRequest,
)
from ..schemas.common import ApiModel
from .mutations import MutationReplayService


class ActivityMetadataService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def add_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: AddActivityAliasRequest,
    ) -> ActivityAlias:
        with self._uow_factory() as uow:
            return add_alias_in_uow(uow, user_id, activity_id, request)

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship:
        with self._uow_factory() as uow:
            return create_relationship_in_uow(uow, user_id, activity_id, request)

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

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_preflight_checks(user_id, activity_id)

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck:
        with self._uow_factory() as uow:
            return create_preflight_check_in_uow(uow, user_id, activity_id, request)


def add_alias_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: AddActivityAliasRequest,
) -> ActivityAlias:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ActivityAlias]:
        alias = uow.activities.add_alias(
            user_id,
            activity_id,
            request.alias_text,
            user_confirmed=request.user_confirmed,
        )
        return alias.id, alias

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="add_activity_alias",
        entity_type="activity_alias",
        result_type=ActivityAlias,
        apply=apply,
    )


def create_relationship_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: CreateActivityRelationshipRequest,
) -> ActivityRelationship:
    _require_activity(uow, user_id, activity_id)
    _require_activity(uow, user_id, request.to_activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ActivityRelationship]:
        relationship = uow.activities.create_relationship(user_id, activity_id, request)
        return relationship.id, relationship

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_activity_relationship",
        entity_type="activity_relationship",
        result_type=ActivityRelationship,
        apply=apply,
    )


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


def create_preflight_check_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: CreatePreflightCheckRequest,
) -> PreflightCheck:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, PreflightCheck]:
        check = uow.activities.create_preflight_check(user_id, activity_id, request)
        return check.id, check

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_preflight_check",
        entity_type="preflight_check",
        result_type=PreflightCheck,
        apply=apply,
    )


class CheckpointTemplateList(ApiModel):
    items: list[CheckpointTemplate]


def _require_activity(uow: UnitOfWork, user_id: UUID, activity_id: UUID) -> None:
    if uow.activities.get(user_id, activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
