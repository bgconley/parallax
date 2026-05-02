from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from ..adapters.context_extractor import (
    ContextExtractor,
    DeterministicContextExtractor,
    ExtractionModelUnavailable,
    ExtractorCandidate,
    ExtractorOutput,
    annotation_request_hash,
    content_hash,
)
from ..domain.extraction_registry import CONTEXT_EXTRACTOR_V1
from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.common import MutationEnvelope
from ..schemas.context import TemporalContextAnnotation
from ..schemas.extraction import (
    ConfirmExtractedEventRequest,
    CorrectExtractedEventRequest,
    ExtractAnnotationRequest,
    ExtractAnnotationResponse,
    ExtractedContextEvent,
    ExtractionStatus,
    ModelInvocationRecord,
)
from .mutations import MutationReplayService


class ExtractionService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        extractor: ContextExtractor | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._extractor = extractor or DeterministicContextExtractor()

    def extract_annotation(
        self,
        user_id: UUID,
        annotation_id: UUID,
        request: ExtractAnnotationRequest,
    ) -> ExtractAnnotationResponse:
        with self._uow_factory() as uow:
            return enqueue_context_annotation_workflow_in_uow(
                uow,
                user_id,
                annotation_id,
                request,
            )

    def confirm_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: ConfirmExtractedEventRequest,
    ) -> ExtractedContextEvent:
        with self._uow_factory() as uow:
            return confirm_extracted_event_in_uow(uow, user_id, event_id, request)

    def correct_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: CorrectExtractedEventRequest,
    ) -> ExtractedContextEvent:
        with self._uow_factory() as uow:
            return correct_extracted_event_in_uow(uow, user_id, event_id, request)


def extract_annotation_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    annotation_id: UUID,
    request: ExtractAnnotationRequest,
    extractor: ContextExtractor,
) -> ExtractAnnotationResponse:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ExtractAnnotationResponse]:
        response = _extract_annotation_once(
            uow,
            user_id,
            annotation_id,
            request,
            extractor,
        )
        return annotation_id, response

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="extract_context_annotation",
        entity_type="temporal_context_annotation",
        result_type=ExtractAnnotationResponse,
        apply=apply,
    )


def _extract_annotation_once(
    uow: UnitOfWork,
    user_id: UUID,
    annotation_id: UUID,
    request: ExtractAnnotationRequest,
    extractor: ContextExtractor,
) -> ExtractAnnotationResponse:
    annotation = _load_annotation(uow, user_id, annotation_id)
    if _blocked_by_privacy(annotation, request):
        uow.contexts.update_annotation_status(
            user_id,
            annotation_id,
            "extraction_pending",
            {"extraction": {"status": "blocked_by_privacy"}},
        )
        return ExtractAnnotationResponse(
            annotation_id=annotation_id,
            status="blocked_by_privacy",
            model_invocation_id=None,
            extracted_events=[],
        )

    try:
        raw_output = extractor.extract(annotation)
    except ExtractionModelUnavailable:
        invocation = _record_invocation(
            uow,
            user_id,
            annotation,
            output=None,
            schema_valid=None,
            metadata={"status": "model_unavailable"},
        )
        uow.contexts.update_annotation_status(
            user_id,
            annotation_id,
            "extraction_pending",
            {"extraction": {"status": "model_unavailable"}},
        )
        return ExtractAnnotationResponse(
            annotation_id=annotation_id,
            status="model_unavailable",
            model_invocation_id=invocation.id,
            extracted_events=[],
        )

    try:
        output = ExtractorOutput.model_validate(raw_output)
    except ValidationError:
        invocation = _record_invocation(
            uow,
            user_id,
            annotation,
            output=raw_output,
            schema_valid=False,
            metadata={"status": "model_output_invalid"},
        )
        uow.contexts.update_annotation_status(
            user_id,
            annotation_id,
            "extraction_pending",
            {"extraction": {"status": "model_output_invalid"}},
        )
        return ExtractAnnotationResponse(
            annotation_id=annotation_id,
            status="model_output_invalid",
            model_invocation_id=invocation.id,
            extracted_events=[],
        )

    invocation = _record_invocation(
        uow,
        user_id,
        annotation,
        output=output.model_dump(mode="json"),
        schema_valid=True,
        metadata={"candidate_count": len(output.candidates)},
    )
    events = [
        uow.contexts.create_extracted_event(
            _event_from_candidate(user_id, annotation, invocation.id, candidate)
        )
        for candidate in output.candidates
    ]
    status = _response_status(events)
    uow.contexts.update_annotation_status(
        user_id,
        annotation_id,
        "needs_confirmation" if events else "extraction_pending",
        {"extraction": {"status": status, "candidate_count": len(events)}},
    )
    return ExtractAnnotationResponse(
        annotation_id=annotation_id,
        status=status,
        model_invocation_id=invocation.id,
        extracted_events=events,
    )


def enqueue_context_annotation_workflow_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    annotation_id: UUID,
    request: ExtractAnnotationRequest,
) -> ExtractAnnotationResponse:
    if uow.contexts.get_annotation(user_id, annotation_id) is None:
        raise HTTPException(status_code=404, detail="context annotation not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ExtractAnnotationResponse]:
        workflow = uow.workflows.enqueue(
            user_id,
            "ProcessContextAnnotationWorkflow",
            {
                "annotation_id": str(annotation_id),
                "mutation": request.mutation.model_dump(mode="json"),
                "force": request.force,
            },
        )
        return workflow.id, ExtractAnnotationResponse(
            annotation_id=annotation_id,
            status="queued",
            model_invocation_id=None,
            extracted_events=[],
        )

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="enqueue_context_annotation_extraction",
        entity_type="workflow_run",
        result_type=ExtractAnnotationResponse,
        apply=apply,
    )


def process_context_annotation_workflow_in_uow(
    uow: UnitOfWork,
    workflow_id: UUID,
    extractor: ContextExtractor,
) -> ExtractAnnotationResponse:
    workflow = uow.workflows.mark_running(workflow_id)
    try:
        annotation_id = UUID(str(workflow.input_ref["annotation_id"]))
        mutation = MutationEnvelope.model_validate(workflow.input_ref["mutation"])
        request = ExtractAnnotationRequest(
            mutation=mutation,
            force=bool(workflow.input_ref.get("force", False)),
        )
        if workflow.user_id is None:
            raise HTTPException(status_code=400, detail="workflow missing user scope")
        response = _extract_annotation_once(
            uow,
            workflow.user_id,
            annotation_id,
            request,
            extractor,
        )
    except Exception as exc:
        uow.workflows.mark_failed(workflow_id, exc.__class__.__name__, str(exc))
        raise
    uow.workflows.mark_succeeded(
        workflow_id,
        {
            "annotation_id": str(response.annotation_id),
            "status": response.status,
            "model_invocation_id": str(response.model_invocation_id)
            if response.model_invocation_id
            else None,
            "extracted_event_ids": [str(event.id) for event in response.extracted_events],
        },
    )
    return response


def confirm_extracted_event_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    event_id: UUID,
    request: ConfirmExtractedEventRequest,
) -> ExtractedContextEvent:
    if uow.contexts.get_extracted_event(user_id, event_id) is None:
        raise HTTPException(status_code=404, detail="extracted context event not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ExtractedContextEvent]:
        event = uow.contexts.update_extracted_event_confirmation(
            user_id,
            event_id,
            request.confirmation_state,
        )
        if event is None:
            raise HTTPException(status_code=404, detail="extracted context event not found")
        if request.confirmation_state == "confirmed":
            _apply_confirmed_event(uow, user_id, event, user_corrected=False)
        return event.id, event

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="confirm_extracted_event",
        entity_type="temporal_extracted_context_event",
        result_type=ExtractedContextEvent,
        apply=apply,
    )


def correct_extracted_event_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    event_id: UUID,
    request: CorrectExtractedEventRequest,
) -> ExtractedContextEvent:
    if uow.contexts.get_extracted_event(user_id, event_id) is None:
        raise HTTPException(status_code=404, detail="extracted context event not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ExtractedContextEvent]:
        correction_result = uow.contexts.correct_extracted_event(user_id, event_id, request)
        if correction_result is None:
            raise HTTPException(status_code=404, detail="extracted context event not found")
        event, _correction = correction_result
        _apply_confirmed_event(uow, user_id, event, user_corrected=True)
        return event.id, event

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="correct_extracted_event",
        entity_type="temporal_extracted_context_event",
        result_type=ExtractedContextEvent,
        apply=apply,
    )


def _load_annotation(
    uow: UnitOfWork,
    user_id: UUID,
    annotation_id: UUID,
) -> TemporalContextAnnotation:
    annotation = uow.contexts.get_annotation(user_id, annotation_id)
    if annotation is None:
        raise HTTPException(status_code=404, detail="context annotation not found")
    if uow.timing.get_session(user_id, annotation.session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    return annotation


def _blocked_by_privacy(
    annotation: TemporalContextAnnotation,
    request: ExtractAnnotationRequest,
) -> bool:
    if request.force and annotation.redacted_text:
        return False
    return annotation.privacy_class in {"sensitive", "private"}


def _record_invocation(
    uow: UnitOfWork,
    user_id: UUID,
    annotation: TemporalContextAnnotation,
    *,
    output: object | None,
    schema_valid: bool | None,
    metadata: dict[str, object],
) -> ModelInvocationRecord:
    version = CONTEXT_EXTRACTOR_V1
    invocation = ModelInvocationRecord(
        id=uuid4(),
        user_id=user_id,
        role=version.role,
        provider=version.provider,
        model_name=version.model_name,
        model_version=version.model_version,
        prompt_version=version.prompt_version,
        schema_version=version.schema_version,
        input_privacy_class=annotation.privacy_class,
        request_hash=annotation_request_hash(annotation),
        output_hash=content_hash(output) if output is not None else None,
        schema_valid=schema_valid,
        repair_count=0,
        fallback_used=False,
        latency_ms=0,
        tokens_in=None,
        tokens_out=None,
        metadata=metadata,
        created_at=datetime.now(UTC),
    )
    return uow.contexts.record_model_invocation(invocation)


def _event_from_candidate(
    user_id: UUID,
    annotation: TemporalContextAnnotation,
    model_invocation_id: UUID,
    candidate: ExtractorCandidate,
) -> ExtractedContextEvent:
    candidate_data = candidate.model_dump()
    confidence = float(candidate_data["confidence"])
    return ExtractedContextEvent(
        id=uuid4(),
        user_id=user_id,
        annotation_id=annotation.id,
        session_id=annotation.session_id,
        checkpoint_run_id=annotation.checkpoint_run_id,
        span_type=candidate_data["span_type"],
        friction_category=candidate_data["friction_category"],
        friction_subtype=candidate_data.get("friction_subtype"),
        resource_name=candidate_data.get("resource_name"),
        location_from=candidate_data.get("location_from"),
        location_to=candidate_data.get("location_to"),
        duration_seconds=candidate_data.get("duration_seconds"),
        count_policy=candidate_data["count_policy"],
        count_in_wall_time=candidate_data["count_in_wall_time"],
        count_in_active_time=candidate_data["count_in_active_time"],
        model_update_scopes=candidate_data["model_update_scopes"],
        suggested_preflight_text=candidate_data.get("suggested_preflight_text"),
        confidence=confidence,
        confirmation_state="needs_confirmation"
        if confidence >= 0.75
        else "deferred_to_review",
        sensitive_data_detected=bool(candidate_data["sensitive_data_detected"]),
        model_invocation_id=model_invocation_id,
        source_json=candidate_data["source_json"],
        user_correction_json={},
    )


def _response_status(events: list[ExtractedContextEvent]) -> ExtractionStatus:
    if not events:
        return "no_candidate"
    if any(event.confirmation_state == "needs_confirmation" for event in events):
        return "needs_confirmation"
    return "extracted"


def _apply_confirmed_event(
    uow: UnitOfWork,
    user_id: UUID,
    event: ExtractedContextEvent,
    *,
    user_corrected: bool,
) -> None:
    uow.timing.upsert_extracted_event_span(user_id, event, user_corrected=user_corrected)
    session = uow.timing.get_session(user_id, event.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    if event.suggested_preflight_text or event.resource_name:
        uow.contexts.create_preflight_check(user_id, session.activity_id, event)
    uow.profiles.recompute_activity_stats(user_id, session.activity_id)
