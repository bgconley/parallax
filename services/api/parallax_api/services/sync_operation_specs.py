from __future__ import annotations

from ..schemas.activity import CreateActivityRequest
from ..schemas.activity_metadata import (
    ActivityMergeRequest,
    AddActivityAliasRequest,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    DecideActivityAliasRequest,
    DecideActivityRelationshipRequest,
    DecidePreflightCheckRequest,
    PutCheckpointsRequest,
)
from ..schemas.context import CreateAnnotationRequest, CreateCaptureContextSnapshotRequest
from ..schemas.extraction import (
    ConfirmExtractedEventRequest,
    CorrectExtractedEventRequest,
    ExtractAnnotationRequest,
)
from ..schemas.privacy import (
    PrivacyDeleteRequest,
    PrivacyExportRequest,
    PrivacyRedactRequest,
    UpdatePrivacySettingsRequest,
)
from ..schemas.temporal import (
    CreatePredictionRequest,
    RecomputeFeatureVectorsRequest,
    RecordPredictionOutcomeRequest,
    TemporalQueryRequest,
)
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingEventSpanRequest,
    CreateTimingSessionRequest,
    ReviewTimingSessionRequest,
)
from .sync_operation_types import OperationSpec

SUPPORTED_MUTATING_OPERATIONS: dict[str, OperationSpec] = {
    "create_activity": OperationSpec("create_activity", ("/v1/activities",), CreateActivityRequest),
    "createActivity": OperationSpec("create_activity", ("/v1/activities",), CreateActivityRequest),
    "add_activity_alias": OperationSpec(
        "add_activity_alias",
        ("/v1/activities/", "/aliases"),
        AddActivityAliasRequest,
        "activity_id",
    ),
    "addActivityAlias": OperationSpec(
        "add_activity_alias",
        ("/v1/activities/", "/aliases"),
        AddActivityAliasRequest,
        "activity_id",
    ),
    "decide_activity_alias": OperationSpec(
        "decide_activity_alias",
        ("/v1/activities/", "/aliases/", "/decision"),
        DecideActivityAliasRequest,
        ("activity_id", "alias_id"),
    ),
    "decideActivityAlias": OperationSpec(
        "decide_activity_alias",
        ("/v1/activities/", "/aliases/", "/decision"),
        DecideActivityAliasRequest,
        ("activity_id", "alias_id"),
    ),
    "create_activity_relationship": OperationSpec(
        "create_activity_relationship",
        ("/v1/activities/", "/relationships"),
        CreateActivityRelationshipRequest,
        "activity_id",
    ),
    "decide_activity_relationship": OperationSpec(
        "decide_activity_relationship",
        ("/v1/activities/", "/relationships/", "/decision"),
        DecideActivityRelationshipRequest,
        ("activity_id", "relationship_id"),
    ),
    "decideActivityRelationship": OperationSpec(
        "decide_activity_relationship",
        ("/v1/activities/", "/relationships/", "/decision"),
        DecideActivityRelationshipRequest,
        ("activity_id", "relationship_id"),
    ),
    "merge_activities": OperationSpec(
        "merge_activities",
        ("/v1/activities/", "/merge"),
        ActivityMergeRequest,
        "activity_id",
    ),
    "mergeActivities": OperationSpec(
        "merge_activities",
        ("/v1/activities/", "/merge"),
        ActivityMergeRequest,
        "activity_id",
    ),
    "createActivityRelationship": OperationSpec(
        "create_activity_relationship",
        ("/v1/activities/", "/relationships"),
        CreateActivityRelationshipRequest,
        "activity_id",
    ),
    "replace_checkpoints": OperationSpec(
        "replace_checkpoints",
        ("/v1/activities/", "/checkpoints"),
        PutCheckpointsRequest,
        "activity_id",
    ),
    "putCheckpoints": OperationSpec(
        "replace_checkpoints",
        ("/v1/activities/", "/checkpoints"),
        PutCheckpointsRequest,
        "activity_id",
    ),
    "create_preflight_check": OperationSpec(
        "create_preflight_check",
        ("/v1/activities/", "/preflight-checks"),
        CreatePreflightCheckRequest,
        "activity_id",
    ),
    "createPreflightCheck": OperationSpec(
        "create_preflight_check",
        ("/v1/activities/", "/preflight-checks"),
        CreatePreflightCheckRequest,
        "activity_id",
    ),
    "decide_preflight_check": OperationSpec(
        "decide_preflight_check",
        ("/v1/activities/", "/preflight-checks/", "/decision"),
        DecidePreflightCheckRequest,
        ("activity_id", "check_id"),
    ),
    "decidePreflightCheck": OperationSpec(
        "decide_preflight_check",
        ("/v1/activities/", "/preflight-checks/", "/decision"),
        DecidePreflightCheckRequest,
        ("activity_id", "check_id"),
    ),
    "create_timing_session": OperationSpec(
        "create_timing_session", ("/v1/timing/sessions",), CreateTimingSessionRequest
    ),
    "createTimingSession": OperationSpec(
        "create_timing_session", ("/v1/timing/sessions",), CreateTimingSessionRequest
    ),
    "append_timing_event": OperationSpec(
        "append_timing_event",
        ("/v1/timing/sessions/", "/events"),
        AppendTimingEventRequest,
        "session_id",
    ),
    "appendTimingEvent": OperationSpec(
        "append_timing_event",
        ("/v1/timing/sessions/", "/events"),
        AppendTimingEventRequest,
        "session_id",
    ),
    "create_timing_event_span": OperationSpec(
        "create_timing_event_span",
        ("/v1/timing/sessions/", "/event-spans"),
        CreateTimingEventSpanRequest,
        "session_id",
    ),
    "createTimingEventSpan": OperationSpec(
        "create_timing_event_span",
        ("/v1/timing/sessions/", "/event-spans"),
        CreateTimingEventSpanRequest,
        "session_id",
    ),
    "complete_timing_session": OperationSpec(
        "complete_timing_session",
        ("/v1/timing/sessions/", "/complete"),
        CompleteTimingSessionRequest,
        "session_id",
    ),
    "completeTimingSession": OperationSpec(
        "complete_timing_session",
        ("/v1/timing/sessions/", "/complete"),
        CompleteTimingSessionRequest,
        "session_id",
    ),
    "review_timing_session": OperationSpec(
        "review_timing_session",
        ("/v1/timing/sessions/", "/review"),
        ReviewTimingSessionRequest,
        "session_id",
    ),
    "reviewTimingSession": OperationSpec(
        "review_timing_session",
        ("/v1/timing/sessions/", "/review"),
        ReviewTimingSessionRequest,
        "session_id",
    ),
    "discard_timing_session": OperationSpec(
        "discard_timing_session",
        ("/v1/timing/sessions/", "/discard"),
        ReviewTimingSessionRequest,
        "session_id",
    ),
    "discardTimingSession": OperationSpec(
        "discard_timing_session",
        ("/v1/timing/sessions/", "/discard"),
        ReviewTimingSessionRequest,
        "session_id",
    ),
    "create_context_annotation": OperationSpec(
        "create_context_annotation",
        ("/v1/timing/sessions/", "/annotations"),
        CreateAnnotationRequest,
        "session_id",
    ),
    "createContextAnnotation": OperationSpec(
        "create_context_annotation",
        ("/v1/timing/sessions/", "/annotations"),
        CreateAnnotationRequest,
        "session_id",
    ),
    "create_capture_context_snapshot": OperationSpec(
        "create_capture_context_snapshot",
        ("/v1/timing/sessions/", "/capture-context"),
        CreateCaptureContextSnapshotRequest,
        "session_id",
    ),
    "createCaptureContextSnapshot": OperationSpec(
        "create_capture_context_snapshot",
        ("/v1/timing/sessions/", "/capture-context"),
        CreateCaptureContextSnapshotRequest,
        "session_id",
    ),
    "extract_context_annotation": OperationSpec(
        "extract_context_annotation",
        ("/v1/timing/annotations/", "/extract"),
        ExtractAnnotationRequest,
        "annotation_id",
    ),
    "extractContextAnnotation": OperationSpec(
        "extract_context_annotation",
        ("/v1/timing/annotations/", "/extract"),
        ExtractAnnotationRequest,
        "annotation_id",
    ),
    "confirm_extracted_event": OperationSpec(
        "confirm_extracted_event",
        ("/v1/timing/extracted-events/", "/confirm"),
        ConfirmExtractedEventRequest,
        "event_id",
    ),
    "confirmExtractedEvent": OperationSpec(
        "confirm_extracted_event",
        ("/v1/timing/extracted-events/", "/confirm"),
        ConfirmExtractedEventRequest,
        "event_id",
    ),
    "correct_extracted_event": OperationSpec(
        "correct_extracted_event",
        ("/v1/timing/extracted-events/", "/correct"),
        CorrectExtractedEventRequest,
        "event_id",
    ),
    "correctExtractedEvent": OperationSpec(
        "correct_extracted_event",
        ("/v1/timing/extracted-events/", "/correct"),
        CorrectExtractedEventRequest,
        "event_id",
    ),
    "update_privacy_settings": OperationSpec(
        "update_privacy_settings", ("/v1/privacy/settings",), UpdatePrivacySettingsRequest
    ),
    "updatePrivacySettings": OperationSpec(
        "update_privacy_settings", ("/v1/privacy/settings",), UpdatePrivacySettingsRequest
    ),
    "privacy_redact": OperationSpec(
        "privacy_redact", ("/v1/privacy/redact",), PrivacyRedactRequest
    ),
    "redactPrivacyData": OperationSpec(
        "privacy_redact", ("/v1/privacy/redact",), PrivacyRedactRequest
    ),
    "privacy_export": OperationSpec(
        "privacy_export", ("/v1/privacy/export",), PrivacyExportRequest
    ),
    "requestPrivacyExport": OperationSpec(
        "privacy_export", ("/v1/privacy/export",), PrivacyExportRequest
    ),
    "privacy_delete": OperationSpec(
        "privacy_delete", ("/v1/privacy/delete",), PrivacyDeleteRequest
    ),
    "requestPrivacyDelete": OperationSpec(
        "privacy_delete", ("/v1/privacy/delete",), PrivacyDeleteRequest
    ),
    "create_temporal_prediction": OperationSpec(
        "create_temporal_prediction", ("/v1/temporal/predictions",), CreatePredictionRequest
    ),
    "createTemporalPrediction": OperationSpec(
        "create_temporal_prediction", ("/v1/temporal/predictions",), CreatePredictionRequest
    ),
    "record_prediction_outcome": OperationSpec(
        "record_prediction_outcome",
        ("/v1/temporal/predictions/", "/outcome"),
        RecordPredictionOutcomeRequest,
        "prediction_id",
    ),
    "recordPredictionOutcome": OperationSpec(
        "record_prediction_outcome",
        ("/v1/temporal/predictions/", "/outcome"),
        RecordPredictionOutcomeRequest,
        "prediction_id",
    ),
    "create_temporal_query": OperationSpec(
        "create_temporal_query", ("/v1/temporal/query",), TemporalQueryRequest
    ),
    "createTemporalQuery": OperationSpec(
        "create_temporal_query", ("/v1/temporal/query",), TemporalQueryRequest
    ),
    "recompute_feature_vectors": OperationSpec(
        "recompute_feature_vectors",
        ("/v1/analytics/feature-vectors/recompute",),
        RecomputeFeatureVectorsRequest,
    ),
    "requestFeatureVectorRecompute": OperationSpec(
        "recompute_feature_vectors",
        ("/v1/analytics/feature-vectors/recompute",),
        RecomputeFeatureVectorsRequest,
    ),
}
