from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException
from parallax_api.adapters.context_extractor import ContextExtractor, DeterministicContextExtractor
from parallax_api.repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from parallax_api.services.extraction_service import process_context_annotation_workflow_in_uow
from parallax_api.services.privacy_service import process_privacy_workflow_in_uow
from pydantic import ValidationError

LOGGER = logging.getLogger(__name__)


class WorkflowWorker:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        extractor: ContextExtractor | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._extractor = extractor or DeterministicContextExtractor()

    def drain_once(self) -> int:
        with self._uow_factory() as uow:
            workflow = uow.workflows.get_next_queued()
            if workflow is None:
                return 0
            try:
                if workflow.workflow_type == "ProcessContextAnnotationWorkflow":
                    process_context_annotation_workflow_in_uow(uow, workflow.id, self._extractor)
                elif workflow.workflow_type == "InferPlaceFromContextWorkflow":
                    _process_place_inference_workflow(uow, workflow.id)
                elif workflow.workflow_type == "DataExportDeletionWorkflow":
                    process_privacy_workflow_in_uow(uow, workflow.id)
                elif workflow.workflow_type == "GenerateTemporalFeatureVectorWorkflow":
                    _process_feature_vector_workflow(uow, workflow.id)
                else:
                    uow.workflows.mark_failed(
                        workflow.id,
                        "unsupported_workflow_type",
                        str(workflow.workflow_type),
                        retryable=False,
                    )
            except Exception as exc:
                LOGGER.exception(
                    "workflow failed",
                    extra={
                        "workflow_id": str(workflow.id),
                        "workflow_type": workflow.workflow_type,
                    },
                )
                uow.workflows.mark_failed(
                    workflow.id,
                    exc.__class__.__name__,
                    str(exc),
                    retryable=not isinstance(
                        exc,
                        (HTTPException, KeyError, ValueError, ValidationError),
                    ),
                )
        return 1


def _process_place_inference_workflow(uow: UnitOfWork, workflow_id: UUID) -> None:
    workflow = uow.workflows.mark_running(workflow_id)
    try:
        if workflow.user_id is None:
            raise ValueError("place inference workflow missing user scope")
        snapshot_id = _input_uuid(workflow, "snapshot_id")
        if snapshot_id is None:
            raise ValueError("place inference workflow missing snapshot_id")
        inferred = uow.contexts.infer_places_for_snapshot(workflow.user_id, snapshot_id)
    except Exception as exc:
        uow.workflows.mark_failed(
            workflow_id,
            exc.__class__.__name__,
            str(exc),
            retryable=not isinstance(exc, ValueError),
        )
        raise
    uow.workflows.mark_succeeded(
        workflow_id,
        {
            "status": "completed",
            "snapshot_id": str(snapshot_id),
            "candidate_count": len(inferred),
            "inferred_place_ids": [str(item.id) for item in inferred],
        },
    )


def _process_feature_vector_workflow(uow: UnitOfWork, workflow_id: UUID) -> None:
    workflow = uow.workflows.mark_running(workflow_id)
    if workflow.user_id is None:
        uow.workflows.mark_failed(
            workflow_id,
            "missing_user_scope",
            "workflow missing user scope",
            retryable=False,
        )
        return
    input_ref = workflow.input_ref
    if not isinstance(input_ref, dict):
        uow.workflows.mark_failed(
            workflow_id,
            "invalid_input_ref",
            "workflow input_ref is invalid",
            retryable=False,
        )
        return
    activity_id = _input_uuid(workflow, "activity_id")
    session_id = _input_uuid(workflow, "session_id")
    raw_feature_families = input_ref.get("feature_families", [])
    feature_families = (
        [family for family in raw_feature_families if isinstance(family, str)]
        if isinstance(raw_feature_families, list)
        else []
    )
    vectors = uow.temporal.generate_feature_vectors(
        workflow.user_id,
        activity_id=activity_id,
        session_id=session_id,
        feature_families=feature_families,
    )
    uow.workflows.mark_succeeded(
        workflow.id,
        {
            "status": "completed",
            "generated_vectors": len(vectors),
            "generated_vector_ids": [str(vector.id) for vector in vectors],
        },
    )


def _input_uuid(workflow: object, key: str) -> UUID | None:
    input_ref = getattr(workflow, "input_ref", {})
    value = input_ref.get(key) if isinstance(input_ref, dict) else None
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        LOGGER.warning("invalid workflow input id", extra={"key": key})
        return None
