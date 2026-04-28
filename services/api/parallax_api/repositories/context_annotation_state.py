from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from ..schemas.context import (
    AnnotationStatus,
    CreateAnnotationRequest,
    TemporalContextAnnotation,
)
from ..schemas.timing import AppendTimingEventRequest, TimingEvent
from .memory import InMemoryStore


def initial_annotation_status(request: CreateAnnotationRequest) -> AnnotationStatus:
    if request.input_mode == "voice" and request.raw_text is None:
        return "transcription_pending"
    if request.raw_text is not None or request.input_mode in {"quick_chip", "review_note"}:
        return "extraction_pending"
    return "captured"


def annotation_source_event(
    user_id: UUID,
    session_id: UUID,
    request: CreateAnnotationRequest,
    annotation: TemporalContextAnnotation,
    server_time: datetime,
) -> TimingEvent:
    event_request = AppendTimingEventRequest(
        mutation=request.mutation,
        event_type="annotation_captured",
        client_time=request.occurred_at,
        timer_elapsed_seconds=request.timer_elapsed_seconds,
        timer_active_seconds=request.timer_active_seconds,
        capture_context_snapshot_id=annotation.capture_context_snapshot_id,
        capture_context_snapshot_ref=request.capture_context_snapshot_ref,
        payload={"annotation_id": str(annotation.id), "input_mode": request.input_mode},
    )
    return TimingEvent(
        id=uuid4(),
        user_id=user_id,
        session_id=session_id,
        event_type=event_request.event_type,
        client_time=event_request.client_time,
        server_time=server_time,
        timer_elapsed_seconds=event_request.timer_elapsed_seconds,
        timer_active_seconds=event_request.timer_active_seconds,
        client_sequence=event_request.mutation.client_sequence,
        client_mutation_id=event_request.mutation.client_mutation_id,
        client_device_id=event_request.mutation.client_device_id,
        idempotency_key=event_request.mutation.idempotency_key,
        capture_context_snapshot_id=event_request.capture_context_snapshot_id,
        capture_context_snapshot_ref=event_request.capture_context_snapshot_ref,
        payload=event_request.payload,
    )


def resolve_annotation_snapshot_link(
    store: InMemoryStore,
    annotation: TemporalContextAnnotation,
) -> TemporalContextAnnotation:
    if (
        annotation.capture_context_snapshot_id is not None
        or annotation.capture_context_snapshot_ref is None
    ):
        return annotation
    for snapshot in store.capture_snapshots.values():
        if (
            snapshot.user_id == annotation.user_id
            and annotation.capture_context_snapshot_ref
            in {snapshot.client_mutation_id, snapshot.idempotency_key}
        ):
            updated = annotation.model_copy(update={"capture_context_snapshot_id": snapshot.id})
            store.annotations[annotation.id] = updated
            return updated
    return annotation
