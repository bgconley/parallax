from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.activity import (
    Activity,
    CreateActivityRequest,
    ResolveActivityRequest,
    ResolveActivityResponse,
)
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
from ..schemas.profile import ActivityProfile
from ..services.activity_metadata_service import ActivityMetadataService
from ..services.activity_service import ActivityService
from ..services.profile_service import ProfileService

router = APIRouter(prefix="/v1/activities", tags=["activities"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.post("", response_model=Activity, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: CreateActivityRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> Activity:
    return ActivityService(uow_factory).create_activity(auth.user_id, payload)


@router.get("", response_model=list[Activity])
def list_activities(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[Activity]:
    return ActivityService(uow_factory).list_activities(auth.user_id, q, limit)


@router.post("/resolve", response_model=ResolveActivityResponse)
def resolve_activity(
    payload: ResolveActivityRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ResolveActivityResponse:
    return ActivityService(uow_factory).resolve_activity(auth.user_id, payload)


@router.get("/{activity_id}", response_model=Activity)
def get_activity(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> Activity:
    return ActivityService(uow_factory).get_activity(auth.user_id, activity_id)


@router.get("/{activity_id}/profile", response_model=ActivityProfile)
def get_activity_profile(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ActivityProfile:
    return ProfileService(uow_factory).get_activity_profile(auth.user_id, activity_id)


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
    return ActivityMetadataService(uow_factory).add_alias(auth.user_id, activity_id, payload)


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
    return ActivityMetadataService(uow_factory).create_relationship(
        auth.user_id,
        activity_id,
        payload,
    )


@router.get("/{activity_id}/checkpoints", response_model=list[CheckpointTemplate])
def list_activity_checkpoints(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[CheckpointTemplate]:
    return ActivityMetadataService(uow_factory).list_checkpoints(auth.user_id, activity_id)


@router.put("/{activity_id}/checkpoints", response_model=list[CheckpointTemplate])
def replace_activity_checkpoints(
    activity_id: UUID,
    payload: PutCheckpointsRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[CheckpointTemplate]:
    return ActivityMetadataService(uow_factory).replace_checkpoints(
        auth.user_id,
        activity_id,
        payload,
    )


@router.get("/{activity_id}/preflight-checks", response_model=list[PreflightCheck])
def list_activity_preflight_checks(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[PreflightCheck]:
    return ActivityMetadataService(uow_factory).list_preflight_checks(auth.user_id, activity_id)


@router.post(
    "/{activity_id}/preflight-checks",
    response_model=PreflightCheck,
    status_code=status.HTTP_201_CREATED,
)
def create_activity_preflight_check(
    activity_id: UUID,
    payload: CreatePreflightCheckRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PreflightCheck:
    return ActivityMetadataService(uow_factory).create_preflight_check(
        auth.user_id,
        activity_id,
        payload,
    )
