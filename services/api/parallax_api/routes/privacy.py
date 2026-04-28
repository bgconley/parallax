from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
    PrivacyWorkflowResponse,
    UpdatePrivacySettingsRequest,
)
from ..services.privacy_service import PrivacyService

router = APIRouter(prefix="/v1/privacy", tags=["privacy"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.get("/settings", response_model=PrivacySettings)
def get_privacy_settings(
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PrivacySettings:
    return PrivacyService(uow_factory).get_settings(auth.user_id)


@router.put("/settings", response_model=PrivacySettings)
def update_privacy_settings(
    payload: UpdatePrivacySettingsRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PrivacySettings:
    return PrivacyService(uow_factory).update_settings(auth.user_id, payload)


@router.post(
    "/redact",
    response_model=PrivacyWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_privacy_redaction(
    payload: PrivacyRedactRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PrivacyWorkflowResponse:
    return PrivacyService(uow_factory).request_redact(auth.user_id, payload)


@router.post(
    "/export",
    response_model=PrivacyWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_privacy_export(
    payload: PrivacyExportRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PrivacyWorkflowResponse:
    return PrivacyService(uow_factory).request_export(auth.user_id, payload)


@router.post(
    "/delete",
    response_model=PrivacyWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_privacy_delete(
    payload: PrivacyDeleteRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PrivacyWorkflowResponse:
    return PrivacyService(uow_factory).request_delete(auth.user_id, payload)
