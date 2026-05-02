from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.activity_metadata import PreflightCheck, ResourceDependency
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
        if not source_event.suggested_preflight_text and not source_event.resource_name:
            return
        if source_event.suggested_preflight_text and not _matching_preflight_exists(
            self._store,
            activity_id,
            source_event.suggested_preflight_text,
        ):
            check = PreflightCheck(
                id=uuid4(),
                user_id=user_id,
                activity_id=activity_id,
                check_text=source_event.suggested_preflight_text,
                state="suggested",
                source="model_suggested",
                confidence=source_event.confidence,
                failure_count=0,
                source_event_id=source_event.id,
                evidence_count=1,
                evidence_summary="1 confirmed extracted context event",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._store.preflight_checks[check.id] = check
        if not source_event.resource_name:
            return
        dependency = self._upsert_resource_dependency(user_id, activity_id, source_event)
        if dependency.failure_count < 2 or not dependency.suggest_precheck:
            return
        check_text = _preflight_text(self._store, activity_id, source_event)
        if _matching_preflight_exists(self._store, activity_id, check_text):
            return
        check = PreflightCheck(
            id=uuid4(),
            user_id=user_id,
            activity_id=activity_id,
            check_text=check_text,
            state="suggested",
            source="resource_dependency",
            confidence=source_event.confidence,
            failure_count=dependency.failure_count,
            source_event_id=source_event.id,
            source_dependency_id=dependency.id,
            evidence_count=dependency.failure_count,
            evidence_summary=(
                f"{dependency.failure_count} confirmed detours for {dependency.resource_name}"
            ),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._store.preflight_checks[check.id] = check

    def _upsert_resource_dependency(
        self,
        user_id: UUID,
        activity_id: UUID,
        source_event: ExtractedContextEvent,
    ) -> ResourceDependency:
        if source_event.resource_name is None:
            raise ValueError("resource dependency requires resource_name")
        normalized_resource = source_event.resource_name.strip().casefold()
        now = datetime.now(UTC)
        existing = next(
            (
                dependency
                for dependency in self._store.resource_dependencies.values()
                if dependency.user_id == user_id
                and dependency.activity_id == activity_id
                and dependency.resource_name.casefold() == normalized_resource
            ),
            None,
        )
        failure_count = (existing.failure_count if existing else 0) + 1
        delay_seconds = source_event.duration_seconds
        if existing is None:
            dependency = ResourceDependency(
                id=uuid4(),
                user_id=user_id,
                activity_id=activity_id,
                resource_name=source_event.resource_name,
                failure_count=failure_count,
                median_delay_seconds=delay_seconds,
                p80_delay_seconds=delay_seconds,
                suggest_precheck=failure_count >= 2,
                last_failed_at=now,
                created_from_event_id=source_event.id,
                created_at=now,
                updated_at=now,
            )
            self._store.resource_dependency_event_ids[dependency.id] = {source_event.id}
        else:
            counted_event_ids = self._store.resource_dependency_event_ids.setdefault(
                existing.id,
                {existing.created_from_event_id}
                if existing.created_from_event_id is not None
                else set(),
            )
            if source_event.id in counted_event_ids:
                return existing
            counted_event_ids.add(source_event.id)
            dependency = existing.model_copy(
                update={
                    "failure_count": failure_count,
                    "median_delay_seconds": delay_seconds,
                    "p80_delay_seconds": max(
                        existing.p80_delay_seconds or 0,
                        delay_seconds or 0,
                    )
                    or None,
                    "suggest_precheck": failure_count >= 2,
                    "last_failed_at": now,
                    "updated_at": now,
                }
            )
        self._store.resource_dependencies[dependency.id] = dependency
        return dependency


def _matching_preflight_exists(
    store: InMemoryStore,
    activity_id: UUID,
    check_text: str,
) -> bool:
    normalized_text = check_text.strip().casefold()
    return any(
        check.activity_id == activity_id
        and check.check_text.strip().casefold() == normalized_text
        and check.state != "retired"
        for check in store.preflight_checks.values()
    )


def _preflight_text(
    store: InMemoryStore,
    activity_id: UUID,
    source_event: ExtractedContextEvent,
) -> str:
    activity = store.activities.get(activity_id)
    activity_name = activity.display_name.casefold() if activity else "the activity"
    if activity_name.startswith("wash "):
        activity_name = f"washing {activity_name.removeprefix('wash ')}"
    if source_event.resource_name and source_event.resource_name.casefold() == "sponge":
        return f"Check sponge/scrubber before {activity_name}."
    return source_event.suggested_preflight_text or f"Check resources before {activity_name}."
