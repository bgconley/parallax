from __future__ import annotations

from collections.abc import Callable
from typing import Literal
from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
    PrivacyWorkflowResponse,
    UpdatePrivacySettingsRequest,
)
from .mutations import MutationReplayService


class PrivacyService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def get_settings(self, user_id: UUID) -> PrivacySettings:
        with self._uow_factory() as uow:
            return uow.privacy.get_settings(user_id)

    def update_settings(
        self,
        user_id: UUID,
        request: UpdatePrivacySettingsRequest,
    ) -> PrivacySettings:
        with self._uow_factory() as uow:
            return update_privacy_settings_in_uow(uow, user_id, request)

    def request_export(
        self,
        user_id: UUID,
        request: PrivacyExportRequest,
    ) -> PrivacyWorkflowResponse:
        with self._uow_factory() as uow:
            return request_privacy_export_in_uow(uow, user_id, request)

    def request_redact(
        self,
        user_id: UUID,
        request: PrivacyRedactRequest,
    ) -> PrivacyWorkflowResponse:
        with self._uow_factory() as uow:
            return request_privacy_redact_in_uow(uow, user_id, request)

    def request_delete(
        self,
        user_id: UUID,
        request: PrivacyDeleteRequest,
    ) -> PrivacyWorkflowResponse:
        with self._uow_factory() as uow:
            return request_privacy_delete_in_uow(uow, user_id, request)


def update_privacy_settings_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: UpdatePrivacySettingsRequest,
) -> PrivacySettings:
    if request.settings.user_id != user_id:
        raise HTTPException(status_code=400, detail="privacy settings user mismatch")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, PrivacySettings]:
        settings = uow.privacy.update_settings(user_id, request.settings)
        return user_id, settings

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="update_privacy_settings",
        entity_type="privacy_settings",
        result_type=PrivacySettings,
        apply=apply,
    )


def request_privacy_export_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: PrivacyExportRequest,
) -> PrivacyWorkflowResponse:
    return _privacy_workflow_response(
        uow,
        user_id,
        request,
        request_type="export",
        workflow_type="PrivacyExportWorkflow",
        apply=lambda: uow.privacy.request_export(user_id, request),
    )


def request_privacy_redact_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: PrivacyRedactRequest,
) -> PrivacyWorkflowResponse:
    return _privacy_workflow_response(
        uow,
        user_id,
        request,
        request_type="redact",
        workflow_type="PrivacyRedactWorkflow",
        apply=lambda: uow.privacy.request_redact(user_id, request),
    )


def request_privacy_delete_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: PrivacyDeleteRequest,
) -> PrivacyWorkflowResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="privacy delete requires confirm=true")
    return _privacy_workflow_response(
        uow,
        user_id,
        request,
        request_type="delete",
        workflow_type="PrivacyDeleteWorkflow",
        apply=lambda: uow.privacy.request_delete(user_id, request),
    )


def _privacy_workflow_response(
    uow: UnitOfWork,
    user_id: UUID,
    request: PrivacyExportRequest | PrivacyRedactRequest | PrivacyDeleteRequest,
    *,
    request_type: Literal["export", "redact", "delete"],
    workflow_type: str,
    apply: Callable[[], UUID],
) -> PrivacyWorkflowResponse:
    mutations = MutationReplayService(uow.mutations)

    def apply_mutation() -> tuple[UUID, PrivacyWorkflowResponse]:
        request_id = apply()
        workflow = uow.workflows.enqueue(
            user_id,
            workflow_type,
            {"request_id": str(request_id), "request_type": request_type},
        )
        uow.workflows.mark_succeeded(workflow.id, {"request_id": str(request_id)})
        response = PrivacyWorkflowResponse(
            request_id=request_id,
            request_type=request_type,
            status="accepted",
            workflow_run_id=workflow.id,
        )
        return request_id, response

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type=f"privacy_{request_type}",
        entity_type="privacy_request",
        result_type=PrivacyWorkflowResponse,
        apply=apply_mutation,
    )
