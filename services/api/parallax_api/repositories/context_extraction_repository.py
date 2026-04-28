from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.extraction import (
    CorrectExtractedEventRequest,
    ExtractedContextEvent,
    ModelInvocationRecord,
    TemporalCorrection,
)
from .memory import InMemoryStore


class ContextExtractionRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def update_annotation_status(
        self,
        user_id: UUID,
        annotation_id: UUID,
        status: str,
        metadata_update: dict[str, object],
    ) -> None:
        annotation = self._store.annotations.get(annotation_id)
        if annotation is None or annotation.user_id != user_id:
            return
        updated = annotation.model_copy(
            update={
                "status": status,
                "metadata": {**annotation.metadata, **metadata_update},
            }
        )
        self._store.annotations[annotation_id] = updated

    def record_model_invocation(
        self,
        invocation: ModelInvocationRecord,
    ) -> ModelInvocationRecord:
        self._store.model_invocations[invocation.id] = invocation
        return invocation

    def create_extracted_event(
        self,
        event: ExtractedContextEvent,
    ) -> ExtractedContextEvent:
        self._store.extracted_events[event.id] = event
        return event

    def get_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> ExtractedContextEvent | None:
        event = self._store.extracted_events.get(event_id)
        if event is None or event.user_id != user_id:
            return None
        return event

    def update_extracted_event_confirmation(
        self,
        user_id: UUID,
        event_id: UUID,
        confirmation_state: str,
    ) -> ExtractedContextEvent | None:
        event = self.get_extracted_event(user_id, event_id)
        if event is None:
            return None
        updated = event.model_copy(update={"confirmation_state": confirmation_state})
        self._store.extracted_events[event_id] = updated
        return updated

    def correct_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: CorrectExtractedEventRequest,
    ) -> tuple[ExtractedContextEvent, TemporalCorrection] | None:
        event = self.get_extracted_event(user_id, event_id)
        if event is None:
            return None
        before_json = event.model_dump(mode="json")
        update = request.model_dump(exclude={"mutation", "user_note"})
        correction_json = {
            "before": before_json,
            "after": update,
            "user_note": request.user_note,
        }
        updated = event.model_copy(
            update={
                **update,
                "confirmation_state": "corrected",
                "user_correction_json": correction_json,
            }
        )
        correction = TemporalCorrection(
            id=uuid4(),
            user_id=user_id,
            session_id=event.session_id,
            entity_type="temporal_extracted_context_event",
            entity_id=event.id,
            correction_type="correct_extracted_event",
            before_json=before_json,
            after_json=updated.model_dump(mode="json"),
            user_note=request.user_note,
            created_at=datetime.now(UTC),
        )
        self._store.extracted_events[event_id] = updated
        self._store.temporal_corrections[correction.id] = correction
        return updated, correction

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        source_event: ExtractedContextEvent,
    ) -> None:
        return None
