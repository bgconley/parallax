from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg

from ..schemas.context import (
    CaptureContextSnapshot,
    ContextCapturePolicy,
    CreateAnnotationRequest,
    CreateCaptureContextSnapshotRequest,
    CreatePlaceRequest,
    DeviceContextObservationInput,
    GeospatialObservationInput,
    RadioObservationInput,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    TemporalContextAnnotation,
    TimingReviewFlag,
    TimingReviewFlagStatus,
    UpdateContextCapturePolicyRequest,
    UpdatePlaceRequest,
    UserPlace,
)
from ..schemas.extraction import (
    CorrectExtractedEventRequest,
    ExtractedContextEvent,
    ModelInvocationRecord,
    TemporalCorrection,
)
from .postgres_context_annotations import PostgresContextAnnotationRepository
from .postgres_context_extraction import PostgresContextExtractionRepository
from .postgres_context_place_inference import PostgresContextPlaceInferenceRepository
from .postgres_context_places import PostgresContextPlaceRepository
from .postgres_context_policies import PostgresContextPolicyRepository
from .postgres_context_review_flags import PostgresContextReviewFlagRepository
from .postgres_context_snapshots import PostgresContextSnapshotRepository


class PostgresContextRepository:
    """Facade for the Phase 3 context persistence boundary.

    The unit of work depends on one context repository interface, but the SQL
    paths are split by cohesive responsibility to keep Phase 4 additions from
    collecting in one persistence file.
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._snapshots = PostgresContextSnapshotRepository(connection)
        self._annotations = PostgresContextAnnotationRepository(connection, self._snapshots)
        self._policies = PostgresContextPolicyRepository(connection)
        self._places = PostgresContextPlaceRepository(connection)
        self._review_flags = PostgresContextReviewFlagRepository(connection)
        self._extraction = PostgresContextExtractionRepository(connection)
        self._place_inference = PostgresContextPlaceInferenceRepository(connection)

    def get_annotation(
        self,
        user_id: UUID,
        annotation_id: UUID,
    ) -> TemporalContextAnnotation | None:
        return self._annotations.get_annotation(user_id, annotation_id)

    def create_annotation(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
    ) -> TemporalContextAnnotation:
        return self._annotations.create_annotation(user_id, session_id, request)

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy:
        return self._policies.get_context_capture_policy(user_id)

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy:
        return self._policies.update_context_capture_policy(user_id, request)

    def create_capture_context_snapshot(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateCaptureContextSnapshotRequest,
        *,
        geospatial_observations: list[GeospatialObservationInput],
        radio_observations: list[RadioObservationInput],
        device_context_observations: list[DeviceContextObservationInput],
    ) -> CaptureContextSnapshot:
        snapshot = self._snapshots.create_capture_context_snapshot(
            user_id,
            session_id,
            request,
            geospatial_observations=geospatial_observations,
            radio_observations=radio_observations,
            device_context_observations=device_context_observations,
        )
        return snapshot.model_copy(
            update={
                "inferred_places": self._place_inference.infer_for_snapshot(user_id, snapshot)
            }
        )

    def list_capture_context_snapshots(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[CaptureContextSnapshot]:
        snapshots = self._snapshots.list_capture_context_snapshots(user_id, session_id)
        return [
            snapshot.model_copy(
                update={
                    "inferred_places": self._place_inference.list_for_snapshot(
                        user_id,
                        snapshot.id,
                    )
                }
            )
            for snapshot in snapshots
        ]

    def snapshot_id_for_reference(self, user_id: UUID, snapshot_ref: str | None) -> UUID | None:
        return self._snapshots.snapshot_id_for_reference(user_id, snapshot_ref)

    def resolve_pending_snapshot_references(
        self,
        user_id: UUID,
        snapshot: CaptureContextSnapshot,
    ) -> None:
        self._snapshots.resolve_pending_snapshot_references(user_id, snapshot)

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace:
        return self._places.create_place(user_id, request)

    def list_places(self, user_id: UUID) -> list[UserPlace]:
        return self._places.list_places(user_id)

    def get_place(self, user_id: UUID, place_id: UUID) -> UserPlace | None:
        return self._places.get_place(user_id, place_id)

    def update_place(
        self,
        user_id: UUID,
        place_id: UUID,
        request: UpdatePlaceRequest,
    ) -> UserPlace | None:
        return self._places.update_place(user_id, place_id, request)

    def resolve_place(self, user_id: UUID, request: ResolvePlaceRequest) -> ResolvePlaceResponse:
        inferred = self._place_inference.resolve_for_snapshot(user_id, request)
        if inferred is not None:
            return inferred
        return self._places.resolve_place(user_id, request)

    def update_annotation_status(
        self,
        user_id: UUID,
        annotation_id: UUID,
        status: str,
        metadata_update: dict[str, object],
    ) -> TemporalContextAnnotation | None:
        self._extraction.update_annotation_status(user_id, annotation_id, status, metadata_update)
        return self.get_annotation(user_id, annotation_id)

    def record_model_invocation(
        self,
        invocation: ModelInvocationRecord,
    ) -> ModelInvocationRecord:
        return self._extraction.record_model_invocation(invocation)

    def create_extracted_event(
        self,
        event: ExtractedContextEvent,
    ) -> ExtractedContextEvent:
        return self._extraction.create_extracted_event(event)

    def get_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> ExtractedContextEvent | None:
        return self._extraction.get_extracted_event(user_id, event_id)

    def update_extracted_event_confirmation(
        self,
        user_id: UUID,
        event_id: UUID,
        confirmation_state: str,
    ) -> ExtractedContextEvent | None:
        return self._extraction.update_extracted_event_confirmation(
            user_id,
            event_id,
            confirmation_state,
        )

    def correct_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: CorrectExtractedEventRequest,
    ) -> tuple[ExtractedContextEvent, TemporalCorrection] | None:
        return self._extraction.correct_extracted_event(user_id, event_id, request)

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        source_event: ExtractedContextEvent,
    ) -> None:
        self._extraction.create_preflight_check(user_id, activity_id, source_event)

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]:
        return self._review_flags.list_review_flags(user_id, session_id, status)

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        status: TimingReviewFlagStatus,
        resolution_note: str | None,
    ) -> TimingReviewFlag | None:
        return self._review_flags.update_review_flag(user_id, flag_id, status, resolution_note)
