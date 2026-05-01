from __future__ import annotations

from collections.abc import Callable
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
    PrivacyWorkflowResponse,
    UpdatePrivacySettingsRequest,
)
from ..settings import get_settings
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
        workflow_type="DataExportDeletionWorkflow",
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
        workflow_type="DataExportDeletionWorkflow",
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
        workflow_type="DataExportDeletionWorkflow",
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
            {
                "request_id": str(request_id),
                "request_type": request_type,
                "request": request.model_dump(mode="json"),
            },
        )
        response = PrivacyWorkflowResponse(
            request_id=request_id,
            request_type=request_type,
            status="queued",
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


def process_privacy_workflow_in_uow(
    uow: UnitOfWork,
    workflow_id: UUID,
) -> dict[str, object]:
    workflow = uow.workflows.mark_running(workflow_id)
    try:
        if workflow.user_id is None:
            raise HTTPException(status_code=400, detail="privacy workflow missing user scope")
        request_type = str(workflow.input_ref.get("request_type", ""))
        request_payload = workflow.input_ref.get("request")
        if not isinstance(request_payload, dict):
            raise HTTPException(status_code=400, detail="privacy workflow missing request payload")
        request_id = UUID(str(workflow.input_ref["request_id"]))
        request = _privacy_request_from_payload(request_type, request_payload)
        result = _complete_privacy_request(uow, workflow.user_id, request)
        if isinstance(request, PrivacyDeleteRequest) and request.delete_scope == "account":
            tombstoned = uow.identities.tombstone_external_identities_for_user(
                workflow.user_id,
                get_settings().auth_identity_tombstone_secret,
            )
            result = {**result, "external_identities_tombstoned": tombstoned}
    except Exception as exc:
        uow.workflows.mark_failed(workflow_id, exc.__class__.__name__, str(exc))
        raise
    result_ref = {"request_id": str(request_id), "request_type": request_type, **result}
    uow.workflows.mark_succeeded(workflow_id, result_ref)
    return result_ref


def _privacy_request_from_payload(
    request_type: str,
    payload: dict[str, object],
) -> PrivacyExportRequest | PrivacyRedactRequest | PrivacyDeleteRequest:
    if request_type == "export":
        return PrivacyExportRequest.model_validate(payload)
    if request_type == "redact":
        return PrivacyRedactRequest.model_validate(payload)
    if request_type == "delete":
        return PrivacyDeleteRequest.model_validate(payload)
    raise HTTPException(status_code=400, detail="unsupported privacy workflow type")


def _complete_privacy_request(
    uow: UnitOfWork,
    user_id: UUID,
    request: BaseModel,
) -> dict[str, object]:
    if isinstance(request, PrivacyExportRequest):
        return uow.privacy.complete_export(user_id, request)
    if isinstance(request, PrivacyRedactRequest):
        return uow.privacy.complete_redact(user_id, request)
    if isinstance(request, PrivacyDeleteRequest):
        return uow.privacy.complete_delete(user_id, request)
    raise HTTPException(status_code=400, detail="unsupported privacy request model")
