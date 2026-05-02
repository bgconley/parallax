from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityIdentityChange,
    ActivityMergePreview,
    ActivityMergePreviewRequest,
    ActivityMergeRequest,
    ActivityRelationship,
    ActivitySplitPreview,
    ActivitySplitPreviewRequest,
    AddActivityAliasRequest,
    CreateActivityRelationshipRequest,
    DecideActivityAliasRequest,
    DecideActivityRelationshipRequest,
)
from .mutations import MutationReplayService


class ActivityIdentityService:
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

    def list_aliases(self, user_id: UUID, activity_id: UUID) -> list[ActivityAlias]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_aliases(user_id, activity_id)

    def decide_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_id: UUID,
        request: DecideActivityAliasRequest,
    ) -> ActivityAlias:
        with self._uow_factory() as uow:
            return decide_alias_in_uow(uow, user_id, activity_id, alias_id, request)

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship:
        with self._uow_factory() as uow:
            return create_relationship_in_uow(uow, user_id, activity_id, request)

    def list_relationships(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ActivityRelationship]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_relationships(user_id, activity_id)

    def decide_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        relationship_id: UUID,
        request: DecideActivityRelationshipRequest,
    ) -> ActivityRelationship:
        with self._uow_factory() as uow:
            return decide_relationship_in_uow(
                uow,
                user_id,
                activity_id,
                relationship_id,
                request,
            )

    def merge_preview(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: ActivityMergePreviewRequest,
    ) -> ActivityMergePreview:
        with self._uow_factory() as uow:
            _require_merge_pair(uow, user_id, activity_id, request.target_activity_id)
            return uow.activities.merge_preview(user_id, activity_id, request.target_activity_id)

    def merge(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: ActivityMergeRequest,
    ) -> ActivityIdentityChange:
        with self._uow_factory() as uow:
            return merge_activities_in_uow(uow, user_id, activity_id, request)

    def split_preview(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: ActivitySplitPreviewRequest,
    ) -> ActivitySplitPreview:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.split_preview(
                user_id,
                activity_id,
                request.proposed_display_name,
                request.session_ids,
            )


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


def decide_alias_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    alias_id: UUID,
    request: DecideActivityAliasRequest,
) -> ActivityAlias:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ActivityAlias]:
        alias = uow.activities.decide_alias(user_id, activity_id, alias_id, request.decision)
        if alias is None:
            raise HTTPException(status_code=404, detail="activity alias not found")
        return alias.id, alias

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="decide_activity_alias",
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


def decide_relationship_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    relationship_id: UUID,
    request: DecideActivityRelationshipRequest,
) -> ActivityRelationship:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ActivityRelationship]:
        relationship = uow.activities.decide_relationship(
            user_id,
            activity_id,
            relationship_id,
            request.decision,
        )
        if relationship is None:
            raise HTTPException(status_code=404, detail="activity relationship not found")
        return relationship.id, relationship

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="decide_activity_relationship",
        entity_type="activity_relationship",
        result_type=ActivityRelationship,
        apply=apply,
    )


def merge_activities_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: ActivityMergeRequest,
) -> ActivityIdentityChange:
    _require_merge_pair(uow, user_id, activity_id, request.target_activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ActivityIdentityChange]:
        change = uow.activities.merge_activities(
            user_id,
            activity_id,
            request.target_activity_id,
            request.reason,
        )
        return change.id, change

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="merge_activities",
        entity_type="activity_identity_change",
        result_type=ActivityIdentityChange,
        apply=apply,
    )


def _require_merge_pair(
    uow: UnitOfWork,
    user_id: UUID,
    source_activity_id: UUID,
    target_activity_id: UUID,
) -> None:
    if source_activity_id == target_activity_id:
        raise HTTPException(status_code=400, detail="source and target activity must differ")
    _require_activity(uow, user_id, source_activity_id)
    _require_activity(uow, user_id, target_activity_id)


def _require_activity(uow: UnitOfWork, user_id: UUID, activity_id: UUID) -> None:
    if uow.activities.get(user_id, activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
