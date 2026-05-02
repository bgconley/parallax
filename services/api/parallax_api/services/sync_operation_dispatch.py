from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from ..repositories.unit_of_work import UnitOfWork
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
from .activity_identity_service import (
    add_alias_in_uow,
    create_relationship_in_uow,
    decide_alias_in_uow,
    decide_relationship_in_uow,
    merge_activities_in_uow,
)
from .activity_metadata_service import (
    replace_checkpoints_in_uow,
)
from .activity_service import create_activity_in_uow
from .context_service import (
    create_annotation_in_uow,
    create_capture_context_snapshot_in_uow,
)
from .extraction_service import (
    confirm_extracted_event_in_uow,
    correct_extracted_event_in_uow,
    enqueue_context_annotation_workflow_in_uow,
)
from .preflight_learning_service import (
    create_preflight_check_in_uow,
    decide_preflight_check_in_uow,
)
from .privacy_service import (
    request_privacy_delete_in_uow,
    request_privacy_export_in_uow,
    request_privacy_redact_in_uow,
    update_privacy_settings_in_uow,
)
from .sync_operation_types import ParsedSyncOperation
from .temporal_service import (
    create_prediction_in_uow,
    create_query_answer_in_uow,
    record_prediction_outcome_in_uow,
    request_feature_vector_recompute_in_uow,
)
from .timing_service import (
    append_event_in_uow,
    complete_session_in_uow,
    create_or_correct_span_in_uow,
    create_session_in_uow,
    save_review_decision_in_uow,
)

OperationApplier = Callable[[UnitOfWork, UUID, ParsedSyncOperation], None]
PayloadT = TypeVar("PayloadT", bound=BaseModel)


def apply_sync_operations(
    uow: UnitOfWork,
    user_id: UUID,
    operations: list[ParsedSyncOperation],
) -> None:
    for operation in operations:
        _APPLIERS[operation.kind](uow, user_id, operation)


def _require_payload(  # noqa: UP047
    operation: ParsedSyncOperation,
    payload_type: type[PayloadT],
) -> PayloadT:
    if not isinstance(operation.payload, payload_type):
        raise TypeError(f"unexpected {operation.kind} payload")
    return operation.payload


def _require_id(operation: ParsedSyncOperation, id_name: str) -> UUID:
    value = getattr(operation, id_name)
    if not isinstance(value, UUID):
        raise TypeError(f"unexpected {operation.kind} path id")
    return value


def _apply_create_activity(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_activity_in_uow(uow, user_id, _require_payload(operation, CreateActivityRequest))


def _apply_add_alias(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    add_alias_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_payload(operation, AddActivityAliasRequest),
    )


def _apply_decide_alias(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    decide_alias_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_id(operation, "alias_id"),
        _require_payload(operation, DecideActivityAliasRequest),
    )


def _apply_relationship(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_relationship_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_payload(operation, CreateActivityRelationshipRequest),
    )


def _apply_decide_relationship(
    uow: UnitOfWork,
    user_id: UUID,
    operation: ParsedSyncOperation,
) -> None:
    decide_relationship_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_id(operation, "relationship_id"),
        _require_payload(operation, DecideActivityRelationshipRequest),
    )


def _apply_merge_activities(
    uow: UnitOfWork,
    user_id: UUID,
    operation: ParsedSyncOperation,
) -> None:
    merge_activities_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_payload(operation, ActivityMergeRequest),
    )


def _apply_replace_checkpoints(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    replace_checkpoints_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_payload(operation, PutCheckpointsRequest),
    )


def _apply_preflight(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_preflight_check_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_payload(operation, CreatePreflightCheckRequest),
    )


def _apply_decide_preflight(
    uow: UnitOfWork,
    user_id: UUID,
    operation: ParsedSyncOperation,
) -> None:
    decide_preflight_check_in_uow(
        uow,
        user_id,
        _require_id(operation, "activity_id"),
        _require_id(operation, "check_id"),
        _require_payload(operation, DecidePreflightCheckRequest),
    )


def _apply_timing_session(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_session_in_uow(uow, user_id, _require_payload(operation, CreateTimingSessionRequest))


def _apply_timing_event(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    append_event_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, AppendTimingEventRequest),
    )


def _apply_timing_span(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_or_correct_span_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, CreateTimingEventSpanRequest),
    )


def _apply_complete_session(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    complete_session_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, CompleteTimingSessionRequest),
    )


def _apply_review_session(
    uow: UnitOfWork,
    user_id: UUID,
    operation: ParsedSyncOperation,
    *,
    discard_endpoint: bool,
) -> None:
    save_review_decision_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, ReviewTimingSessionRequest),
        discard_endpoint=discard_endpoint,
    )


def _apply_annotation(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_annotation_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, CreateAnnotationRequest),
    )


def _apply_context_snapshot(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    create_capture_context_snapshot_in_uow(
        uow,
        user_id,
        _require_id(operation, "session_id"),
        _require_payload(operation, CreateCaptureContextSnapshotRequest),
    )


def _apply_extract_annotation(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    enqueue_context_annotation_workflow_in_uow(
        uow,
        user_id,
        _require_id(operation, "annotation_id"),
        _require_payload(operation, ExtractAnnotationRequest),
    )


def _apply_confirm_event(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    confirm_extracted_event_in_uow(
        uow,
        user_id,
        _require_id(operation, "event_id"),
        _require_payload(operation, ConfirmExtractedEventRequest),
    )


def _apply_correct_event(uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation) -> None:
    correct_extracted_event_in_uow(
        uow,
        user_id,
        _require_id(operation, "event_id"),
        _require_payload(operation, CorrectExtractedEventRequest),
    )


def _apply_prediction_outcome(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    record_prediction_outcome_in_uow(
        uow,
        user_id,
        _require_id(operation, "prediction_id"),
        _require_payload(operation, RecordPredictionOutcomeRequest),
    )


def _apply_update_privacy_settings(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    update_privacy_settings_in_uow(
        uow,
        user_id,
        _require_payload(operation, UpdatePrivacySettingsRequest),
    )


def _apply_privacy_redact(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    request_privacy_redact_in_uow(
        uow,
        user_id,
        _require_payload(operation, PrivacyRedactRequest),
    )


def _apply_privacy_export(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    request_privacy_export_in_uow(
        uow,
        user_id,
        _require_payload(operation, PrivacyExportRequest),
    )


def _apply_privacy_delete(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    request_privacy_delete_in_uow(
        uow,
        user_id,
        _require_payload(operation, PrivacyDeleteRequest),
    )


def _apply_temporal_prediction(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    create_prediction_in_uow(
        uow,
        user_id,
        _require_payload(operation, CreatePredictionRequest),
    )


def _apply_temporal_query(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    create_query_answer_in_uow(
        uow,
        user_id,
        _require_payload(operation, TemporalQueryRequest),
    )


def _apply_recompute_feature_vectors(
    uow: UnitOfWork, user_id: UUID, operation: ParsedSyncOperation
) -> None:
    request_feature_vector_recompute_in_uow(
        uow,
        user_id,
        _require_payload(operation, RecomputeFeatureVectorsRequest),
    )


_APPLIERS: dict[str, OperationApplier] = {
    "create_activity": _apply_create_activity,
    "add_activity_alias": _apply_add_alias,
    "decide_activity_alias": _apply_decide_alias,
    "create_activity_relationship": _apply_relationship,
    "decide_activity_relationship": _apply_decide_relationship,
    "merge_activities": _apply_merge_activities,
    "replace_checkpoints": _apply_replace_checkpoints,
    "create_preflight_check": _apply_preflight,
    "decide_preflight_check": _apply_decide_preflight,
    "create_timing_session": _apply_timing_session,
    "append_timing_event": _apply_timing_event,
    "create_timing_event_span": _apply_timing_span,
    "complete_timing_session": _apply_complete_session,
    "review_timing_session": lambda uow, user_id, op: _apply_review_session(
        uow, user_id, op, discard_endpoint=False
    ),
    "discard_timing_session": lambda uow, user_id, op: _apply_review_session(
        uow, user_id, op, discard_endpoint=True
    ),
    "create_context_annotation": _apply_annotation,
    "create_capture_context_snapshot": _apply_context_snapshot,
    "extract_context_annotation": _apply_extract_annotation,
    "confirm_extracted_event": _apply_confirm_event,
    "correct_extracted_event": _apply_correct_event,
    "update_privacy_settings": _apply_update_privacy_settings,
    "privacy_redact": _apply_privacy_redact,
    "privacy_export": _apply_privacy_export,
    "privacy_delete": _apply_privacy_delete,
    "create_temporal_prediction": _apply_temporal_prediction,
    "record_prediction_outcome": _apply_prediction_outcome,
    "create_temporal_query": _apply_temporal_query,
    "recompute_feature_vectors": _apply_recompute_feature_vectors,
}
