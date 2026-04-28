from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity import CreateActivityRequest
from ..schemas.common import MutationEnvelope
from ..schemas.context import CreateAnnotationRequest, CreateCaptureContextSnapshotRequest
from ..schemas.sync import SyncPushRequest, SyncPushResponse
from ..schemas.timing import (
    AppendTimingEventRequest,
    CompleteTimingSessionRequest,
    CreateTimingSessionRequest,
    ReviewTimingSessionRequest,
)
from ..validation_errors import safe_validation_errors
from .activity_service import create_activity_in_uow
from .context_service import (
    create_annotation_in_uow,
    create_capture_context_snapshot_in_uow,
)
from .mutations import MutationReplayService
from .timing_service import (
    append_event_in_uow,
    complete_session_in_uow,
    create_session_in_uow,
    save_review_decision_in_uow,
)


@dataclass(frozen=True)
class OperationSpec:
    kind: str
    path_parts: tuple[str, ...]
    payload_type: type[BaseModel]


@dataclass(frozen=True)
class ParsedSyncOperation:
    kind: str
    payload: BaseModel
    session_id: UUID | None = None


_SUPPORTED_MUTATING_OPERATIONS: dict[str, OperationSpec] = {
    "create_activity": OperationSpec("create_activity", ("/v1/activities",), CreateActivityRequest),
    "createActivity": OperationSpec("create_activity", ("/v1/activities",), CreateActivityRequest),
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
    ),
    "appendTimingEvent": OperationSpec(
        "append_timing_event",
        ("/v1/timing/sessions/", "/events"),
        AppendTimingEventRequest,
    ),
    "complete_timing_session": OperationSpec(
        "complete_timing_session",
        ("/v1/timing/sessions/", "/complete"),
        CompleteTimingSessionRequest,
    ),
    "completeTimingSession": OperationSpec(
        "complete_timing_session",
        ("/v1/timing/sessions/", "/complete"),
        CompleteTimingSessionRequest,
    ),
    "review_timing_session": OperationSpec(
        "review_timing_session",
        ("/v1/timing/sessions/", "/review"),
        ReviewTimingSessionRequest,
    ),
    "reviewTimingSession": OperationSpec(
        "review_timing_session",
        ("/v1/timing/sessions/", "/review"),
        ReviewTimingSessionRequest,
    ),
    "discard_timing_session": OperationSpec(
        "discard_timing_session",
        ("/v1/timing/sessions/", "/discard"),
        ReviewTimingSessionRequest,
    ),
    "discardTimingSession": OperationSpec(
        "discard_timing_session",
        ("/v1/timing/sessions/", "/discard"),
        ReviewTimingSessionRequest,
    ),
    "create_context_annotation": OperationSpec(
        "create_context_annotation",
        ("/v1/timing/sessions/", "/annotations"),
        CreateAnnotationRequest,
    ),
    "createContextAnnotation": OperationSpec(
        "create_context_annotation",
        ("/v1/timing/sessions/", "/annotations"),
        CreateAnnotationRequest,
    ),
    "create_capture_context_snapshot": OperationSpec(
        "create_capture_context_snapshot",
        ("/v1/timing/sessions/", "/capture-context"),
        CreateCaptureContextSnapshotRequest,
    ),
    "createCaptureContextSnapshot": OperationSpec(
        "create_capture_context_snapshot",
        ("/v1/timing/sessions/", "/capture-context"),
        CreateCaptureContextSnapshotRequest,
    ),
}


class SyncService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def push(self, user_id: UUID, request: SyncPushRequest) -> SyncPushResponse:
        operations = self._parse_operations(request)

        with self._uow_factory() as uow:
            mutations = MutationReplayService(uow.mutations)

            def apply() -> tuple[UUID | None, SyncPushResponse]:
                self._apply_operations(uow, user_id, operations)
                return None, SyncPushResponse(
                    accepted=True,
                    operation_count=len(operations),
                    server_time=datetime.now(UTC),
                )

            return mutations.replay_or_apply(
                user_id=user_id,
                mutation=request.mutation,
                mutation_type="sync_push",
                entity_type="sync_batch",
                result_type=SyncPushResponse,
                apply=apply,
            )

    @staticmethod
    def _apply_operations(
        uow: UnitOfWork,
        user_id: UUID,
        operations: list[ParsedSyncOperation],
    ) -> None:
        for operation in operations:
            if operation.kind == "create_activity":
                if not isinstance(operation.payload, CreateActivityRequest):
                    raise TypeError("unexpected create_activity payload")
                create_activity_in_uow(uow, user_id, operation.payload)
            elif operation.kind == "create_timing_session":
                if not isinstance(operation.payload, CreateTimingSessionRequest):
                    raise TypeError("unexpected create_timing_session payload")
                create_session_in_uow(uow, user_id, operation.payload)
            elif operation.kind == "append_timing_event":
                if operation.session_id is None or not isinstance(
                    operation.payload, AppendTimingEventRequest
                ):
                    raise TypeError("unexpected append_timing_event payload")
                append_event_in_uow(uow, user_id, operation.session_id, operation.payload)
            elif operation.kind == "complete_timing_session":
                if operation.session_id is None or not isinstance(
                    operation.payload, CompleteTimingSessionRequest
                ):
                    raise TypeError("unexpected complete_timing_session payload")
                complete_session_in_uow(uow, user_id, operation.session_id, operation.payload)
            elif operation.kind == "review_timing_session":
                if operation.session_id is None or not isinstance(
                    operation.payload, ReviewTimingSessionRequest
                ):
                    raise TypeError("unexpected review_timing_session payload")
                save_review_decision_in_uow(
                    uow,
                    user_id,
                    operation.session_id,
                    operation.payload,
                    discard_endpoint=False,
                )
            elif operation.kind == "discard_timing_session":
                if operation.session_id is None or not isinstance(
                    operation.payload, ReviewTimingSessionRequest
                ):
                    raise TypeError("unexpected discard_timing_session payload")
                save_review_decision_in_uow(
                    uow,
                    user_id,
                    operation.session_id,
                    operation.payload,
                    discard_endpoint=True,
                )
            elif operation.kind == "create_context_annotation":
                if operation.session_id is None or not isinstance(
                    operation.payload, CreateAnnotationRequest
                ):
                    raise TypeError("unexpected create_context_annotation payload")
                create_annotation_in_uow(uow, user_id, operation.session_id, operation.payload)
            elif operation.kind == "create_capture_context_snapshot":
                if operation.session_id is None or not isinstance(
                    operation.payload, CreateCaptureContextSnapshotRequest
                ):
                    raise TypeError("unexpected create_capture_context_snapshot payload")
                create_capture_context_snapshot_in_uow(
                    uow,
                    user_id,
                    operation.session_id,
                    operation.payload,
                )
            else:
                raise TypeError(f"unsupported parsed sync operation: {operation.kind}")

    @staticmethod
    def _parse_operations(request: SyncPushRequest) -> list[ParsedSyncOperation]:
        parsed: list[ParsedSyncOperation] = []
        for index, operation in enumerate(request.mutations):
            spec = _SUPPORTED_MUTATING_OPERATIONS.get(operation.operation)
            if spec is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "unsupported_sync_operation",
                        "message": "sync operation is not supported in the active phase",
                        "details": {"operation_index": index, "operation": operation.operation},
                        "retryable": False,
                    },
                )
            if not _path_matches(operation.path, spec.path_parts):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation path does not match operation type",
                        "details": {"operation_index": index, "operation": operation.operation},
                        "retryable": False,
                    },
                )
            nested_mutation = operation.body.get("mutation")
            if nested_mutation is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation is missing its mutation envelope",
                        "details": {"operation_index": index},
                        "retryable": False,
                    },
                )
            try:
                MutationEnvelope.model_validate(nested_mutation)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation",
                        "message": "sync operation has invalid mutation envelope",
                        "details": {"operation_index": index},
                        "retryable": False,
                    },
                ) from exc
            try:
                payload = spec.payload_type.model_validate(operation.body)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "invalid_sync_operation_payload",
                        "message": "sync operation payload does not match endpoint schema",
                        "details": {
                            "operation_index": index,
                            "errors": safe_validation_errors(exc.errors()),
                        },
                        "retryable": False,
                    },
                ) from exc

            parsed.append(
                ParsedSyncOperation(
                    kind=spec.kind,
                    payload=payload,
                    session_id=_session_id_from_path(operation.path, spec.path_parts, index),
                )
            )
        return parsed


def _path_matches(path: str, expected_parts: tuple[str, ...]) -> bool:
    if len(expected_parts) == 1:
        return path == expected_parts[0]
    return path.startswith(expected_parts[0]) and path.endswith(expected_parts[1])


def _session_id_from_path(path: str, expected_parts: tuple[str, ...], index: int) -> UUID | None:
    if len(expected_parts) == 1:
        return None
    session_id_text = path.removeprefix(expected_parts[0]).removesuffix(expected_parts[1])
    try:
        return UUID(session_id_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "invalid_sync_operation",
                "message": "sync operation path contains an invalid session id",
                "details": {"operation_index": index},
                "retryable": False,
            },
        ) from exc
