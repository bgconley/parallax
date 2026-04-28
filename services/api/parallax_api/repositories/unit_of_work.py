from __future__ import annotations

from types import TracebackType
from typing import Literal, Protocol
from uuid import UUID

from ..domain.timing_spans import TimingEventSpanDraft, TimingSpanTotals
from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityRelationship,
    CheckpointTemplate,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    PreflightCheck,
    PutCheckpointsRequest,
)
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
from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    PrivacySettings,
)
from ..schemas.profile import ActivityProfile
from ..schemas.temporal import (
    CreatePredictionRequest,
    PredictionOutcome,
    RecordPredictionOutcomeRequest,
    TemporalPrediction,
    TemporalQueryAnswer,
    TemporalQueryRequest,
)
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
from ..schemas.workflows import WorkflowRun
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

    def add_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_text: str,
        *,
        user_confirmed: bool,
    ) -> ActivityAlias: ...

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship: ...

    def list_checkpoints(self, user_id: UUID, activity_id: UUID) -> list[CheckpointTemplate]: ...

    def replace_checkpoints(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: PutCheckpointsRequest,
    ) -> list[CheckpointTemplate]: ...

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]: ...

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck: ...


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

    def create_or_correct_span(
        self,
        user_id: UUID,
        session_id: UUID,
        span: TimingEventSpan,
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


class PrivacyRepositoryProtocol(Protocol):
    def get_settings(self, user_id: UUID) -> PrivacySettings: ...

    def update_settings(self, user_id: UUID, settings: PrivacySettings) -> PrivacySettings: ...

    def request_export(self, user_id: UUID, request: PrivacyExportRequest) -> UUID: ...

    def request_redact(self, user_id: UUID, request: PrivacyRedactRequest) -> UUID: ...

    def request_delete(self, user_id: UUID, request: PrivacyDeleteRequest) -> UUID: ...


class TemporalRepositoryProtocol(Protocol):
    def create_prediction(
        self,
        user_id: UUID,
        request: CreatePredictionRequest,
    ) -> TemporalPrediction: ...

    def record_prediction_outcome(
        self,
        user_id: UUID,
        prediction_id: UUID,
        request: RecordPredictionOutcomeRequest,
    ) -> PredictionOutcome: ...

    def create_query_answer(
        self,
        user_id: UUID,
        request: TemporalQueryRequest,
    ) -> TemporalQueryAnswer: ...

    def get_query_answer(self, user_id: UUID, answer_id: UUID) -> TemporalQueryAnswer | None: ...


class WorkflowRunRepositoryProtocol(Protocol):
    def enqueue(
        self,
        user_id: UUID | None,
        workflow_type: str,
        input_ref: dict[str, object],
    ) -> WorkflowRun: ...

    def get_next_queued(self) -> WorkflowRun | None: ...

    def mark_running(self, workflow_id: UUID) -> WorkflowRun: ...

    def mark_succeeded(self, workflow_id: UUID, result_ref: dict[str, object]) -> WorkflowRun: ...

    def mark_failed(
        self,
        workflow_id: UUID,
        error_code: str,
        error_message: str,
    ) -> WorkflowRun: ...


class UnitOfWork(Protocol):
    activities: ActivityRepositoryProtocol
    timing: TimingRepositoryProtocol
    profiles: ProfileRepositoryProtocol
    contexts: ContextRepositoryProtocol
    privacy: PrivacyRepositoryProtocol
    temporal: TemporalRepositoryProtocol
    workflows: WorkflowRunRepositoryProtocol
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
