from __future__ import annotations

import logging
from uuid import UUID

from parallax_api.adapters.context_extractor import ContextExtractor, DeterministicContextExtractor
from parallax_api.repositories.unit_of_work import UnitOfWorkFactory
from parallax_api.services.extraction_service import process_context_annotation_workflow_in_uow

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
            if workflow.workflow_type == "ProcessContextAnnotationWorkflow":
                process_context_annotation_workflow_in_uow(uow, workflow.id, self._extractor)
            elif workflow.workflow_type == "InferPlaceFromContextWorkflow":
                uow.workflows.mark_succeeded(
                    workflow.id,
                    {
                        "status": "already_materialized",
                        "snapshot_id": _input_id(workflow, "snapshot_id"),
                    },
                )
            elif workflow.workflow_type in {
                "PrivacyExportWorkflow",
                "PrivacyRedactWorkflow",
                "PrivacyDeleteWorkflow",
                "FeatureVectorRecomputeWorkflow",
            }:
                uow.workflows.mark_succeeded(workflow.id, {"status": "accepted"})
            else:
                uow.workflows.mark_failed(
                    workflow.id,
                    "unsupported_workflow_type",
                    str(workflow.workflow_type),
                )
        return 1


def _input_id(workflow: object, key: str) -> str | None:
    input_ref = getattr(workflow, "input_ref", {})
    value = input_ref.get(key) if isinstance(input_ref, dict) else None
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except ValueError:
        LOGGER.warning("invalid workflow input id", extra={"key": key})
        return None
