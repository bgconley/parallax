from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
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
from ..services.activity_identity_service import ActivityIdentityService

router = APIRouter(prefix="/v1/activities", tags=["activity-identity"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.get("/{activity_id}/aliases", response_model=list[ActivityAlias])
def list_activity_aliases(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[ActivityAlias]:
    return ActivityIdentityService(uow_factory).list_aliases(auth.user_id, activity_id)


@router.post(
    "/{activity_id}/aliases",
    response_model=ActivityAlias,
    status_code=status.HTTP_201_CREATED,
)
def add_activity_alias(
    activity_id: UUID,
    payload: AddActivityAliasRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityAlias:
    return ActivityIdentityService(uow_factory).add_alias(auth.user_id, activity_id, payload)


@router.post("/{activity_id}/aliases/{alias_id}/decision", response_model=ActivityAlias)
def decide_activity_alias(
    activity_id: UUID,
    alias_id: UUID,
    payload: DecideActivityAliasRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityAlias:
    return ActivityIdentityService(uow_factory).decide_alias(
        auth.user_id,
        activity_id,
        alias_id,
        payload,
    )


@router.get("/{activity_id}/relationships", response_model=list[ActivityRelationship])
def list_activity_relationships(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[ActivityRelationship]:
    return ActivityIdentityService(uow_factory).list_relationships(auth.user_id, activity_id)


@router.post(
    "/{activity_id}/relationships",
    response_model=ActivityRelationship,
    status_code=status.HTTP_201_CREATED,
)
def create_activity_relationship(
    activity_id: UUID,
    payload: CreateActivityRelationshipRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityRelationship:
    return ActivityIdentityService(uow_factory).create_relationship(
        auth.user_id,
        activity_id,
        payload,
    )


@router.post(
    "/{activity_id}/relationships/{relationship_id}/decision",
    response_model=ActivityRelationship,
)
def decide_activity_relationship(
    activity_id: UUID,
    relationship_id: UUID,
    payload: DecideActivityRelationshipRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityRelationship:
    return ActivityIdentityService(uow_factory).decide_relationship(
        auth.user_id,
        activity_id,
        relationship_id,
        payload,
    )


@router.post("/{activity_id}/merge-preview", response_model=ActivityMergePreview)
def preview_activity_merge(
    activity_id: UUID,
    payload: ActivityMergePreviewRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityMergePreview:
    return ActivityIdentityService(uow_factory).merge_preview(auth.user_id, activity_id, payload)


@router.post("/{activity_id}/merge", response_model=ActivityIdentityChange)
def merge_activity(
    activity_id: UUID,
    payload: ActivityMergeRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityIdentityChange:
    return ActivityIdentityService(uow_factory).merge(auth.user_id, activity_id, payload)


@router.post("/{activity_id}/split-preview", response_model=ActivitySplitPreview)
def preview_activity_split(
    activity_id: UUID,
    payload: ActivitySplitPreviewRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivitySplitPreview:
    return ActivityIdentityService(uow_factory).split_preview(auth.user_id, activity_id, payload)
