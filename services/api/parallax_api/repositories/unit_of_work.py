from __future__ import annotations

from types import TracebackType
from typing import Literal, Protocol
from uuid import UUID

from ..domain.timing_spans import TimingEventSpanDraft, TimingSpanTotals
from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
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
from ..schemas.profile import ActivityProfile
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    ModelUpdateDecision,
    ReviewTimingSessionRequest,
    TimingEvent,
    TimingEventSpan,
    TimingSession,
)
from .mutation_log import MutationLogRepository


class ActivityRepositoryProtocol(Protocol):
    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity: ...

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]: ...

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None: ...

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]: ...


class TimingRepositoryProtocol(Protocol):
    def create_session(
        self,
        user_id: UUID,
        request: CreateTimingSessionRequest,
    ) -> TimingSession: ...

    def get_session(self, user_id: UUID, session_id: UUID) -> TimingSession | None: ...

    def append_event(
        self,
        user_id: UUID,
        session_id: UUID,
        request: AppendTimingEventRequest,
    ) -> TimingEvent: ...

    def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CompleteTimingSessionRequest,
    ) -> TimingSession: ...

    def review_session(
        self,
        user_id: UUID,
        session_id: UUID,
        request: ReviewTimingSessionRequest,
        span_drafts: list[TimingEventSpanDraft],
        totals: TimingSpanTotals,
    ) -> ModelUpdateDecision: ...

    def replace_derived_spans(
        self,
        user_id: UUID,
        session_id: UUID,
        span_drafts: list[TimingEventSpanDraft],
    ) -> list[TimingEventSpan]: ...

    def upsert_extracted_event_span(
        self,
        user_id: UUID,
        extracted_event: ExtractedContextEvent,
        *,
        user_corrected: bool,
    ) -> TimingEventSpan: ...


class ProfileRepositoryProtocol(Protocol):
    def recompute_activity_stats(self, user_id: UUID, activity_id: UUID) -> None: ...

    def get_activity_profile(self, user_id: UUID, activity_id: UUID) -> ActivityProfile | None: ...


class ContextRepositoryProtocol(Protocol):
    def get_annotation(
        self,
        user_id: UUID,
        annotation_id: UUID,
    ) -> TemporalContextAnnotation | None: ...

    def create_annotation(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
    ) -> TemporalContextAnnotation: ...

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy: ...

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy: ...

    def create_capture_context_snapshot(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateCaptureContextSnapshotRequest,
        *,
        geospatial_observations: list[GeospatialObservationInput],
        radio_observations: list[RadioObservationInput],
        device_context_observations: list[DeviceContextObservationInput],
    ) -> CaptureContextSnapshot: ...

    def list_capture_context_snapshots(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[CaptureContextSnapshot]: ...

    def snapshot_id_for_reference(self, user_id: UUID, snapshot_ref: str | None) -> UUID | None: ...

    def resolve_pending_snapshot_references(
        self,
        user_id: UUID,
        snapshot: CaptureContextSnapshot,
    ) -> None: ...

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace: ...

    def list_places(self, user_id: UUID) -> list[UserPlace]: ...

    def get_place(self, user_id: UUID, place_id: UUID) -> UserPlace | None: ...

    def update_place(
        self,
        user_id: UUID,
        place_id: UUID,
        request: UpdatePlaceRequest,
    ) -> UserPlace | None: ...

    def resolve_place(
        self,
        user_id: UUID,
        request: ResolvePlaceRequest,
    ) -> ResolvePlaceResponse: ...

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]: ...

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        status: TimingReviewFlagStatus,
        resolution_note: str | None,
    ) -> TimingReviewFlag | None: ...

    def update_annotation_status(
        self,
        user_id: UUID,
        annotation_id: UUID,
        status: str,
        metadata_update: dict[str, object],
    ) -> TemporalContextAnnotation | None: ...

    def record_model_invocation(
        self,
        invocation: ModelInvocationRecord,
    ) -> ModelInvocationRecord: ...

    def create_extracted_event(
        self,
        event: ExtractedContextEvent,
    ) -> ExtractedContextEvent: ...

    def get_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> ExtractedContextEvent | None: ...

    def update_extracted_event_confirmation(
        self,
        user_id: UUID,
        event_id: UUID,
        confirmation_state: str,
    ) -> ExtractedContextEvent | None: ...

    def correct_extracted_event(
        self,
        user_id: UUID,
        event_id: UUID,
        request: CorrectExtractedEventRequest,
    ) -> tuple[ExtractedContextEvent, TemporalCorrection] | None: ...

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        source_event: ExtractedContextEvent,
    ) -> None: ...


class UnitOfWork(Protocol):
    activities: ActivityRepositoryProtocol
    timing: TimingRepositoryProtocol
    profiles: ProfileRepositoryProtocol
    contexts: ContextRepositoryProtocol
    mutations: MutationLogRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
