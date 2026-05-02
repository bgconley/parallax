from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.activity_metadata import (
    CreatePreflightCheckRequest,
    DecidePreflightCheckRequest,
    PreflightCheck,
    ResourceDependency,
)
from ..services.preflight_learning_service import PreflightLearningService

router = APIRouter(prefix="/v1/activities", tags=["activity-preflight"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.get("/{activity_id}/resource-dependencies", response_model=list[ResourceDependency])
def list_activity_resource_dependencies(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[ResourceDependency]:
    return PreflightLearningService(uow_factory).list_resource_dependencies(
        auth.user_id,
        activity_id,
    )


@router.get("/{activity_id}/preflight-checks", response_model=list[PreflightCheck])
def list_activity_preflight_checks(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[PreflightCheck]:
    return PreflightLearningService(uow_factory).list_preflight_checks(auth.user_id, activity_id)


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
    return PreflightLearningService(uow_factory).create_preflight_check(
        auth.user_id,
        activity_id,
        payload,
    )


@router.post(
    "/{activity_id}/preflight-checks/{check_id}/decision",
    response_model=PreflightCheck,
)
def decide_activity_preflight_check(
    activity_id: UUID,
    check_id: UUID,
    payload: DecidePreflightCheckRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PreflightCheck:
    return PreflightLearningService(uow_factory).decide_preflight_check(
        auth.user_id,
        activity_id,
        check_id,
        payload,
    )
