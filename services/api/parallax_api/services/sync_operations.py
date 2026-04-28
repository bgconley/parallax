from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from ..schemas.common import MutationEnvelope
from ..schemas.sync import SyncPushRequest
from ..validation_errors import safe_validation_errors
from .sync_operation_dispatch import apply_sync_operations
from .sync_operation_specs import SUPPORTED_MUTATING_OPERATIONS
from .sync_operation_types import OperationSpec, ParsedSyncOperation

__all__ = ["apply_sync_operations", "parse_sync_operations"]


def parse_sync_operations(request: SyncPushRequest) -> list[ParsedSyncOperation]:
    parsed: list[ParsedSyncOperation] = []
    for index, operation in enumerate(request.mutations):
        spec = SUPPORTED_MUTATING_OPERATIONS.get(operation.operation)
        if spec is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "unsupported_sync_operation",
                    "message": "sync operation is not supported",
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
        _validate_nested_mutation(operation.body, index)
        parsed.append(
            ParsedSyncOperation(
                kind=spec.kind,
                payload=_validate_payload(spec, operation.body, index),
                **_ids_from_path(operation.path, spec, index),
            )
        )
    return parsed


def _validate_nested_mutation(body: dict[str, object], index: int) -> None:
    nested_mutation = body.get("mutation")
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


def _validate_payload(
    spec: OperationSpec,
    body: dict[str, object],
    index: int,
) -> BaseModel:
    try:
        return spec.payload_type.model_validate(body)
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


def _path_matches(path: str, expected_parts: tuple[str, ...]) -> bool:
    if len(expected_parts) == 1:
        return path == expected_parts[0]
    return path.startswith(expected_parts[0]) and path.endswith(expected_parts[1])


def _ids_from_path(path: str, spec: OperationSpec, index: int) -> dict[str, UUID | None]:
    if spec.path_id_name is None:
        return {}
    id_text = path.removeprefix(spec.path_parts[0]).removesuffix(spec.path_parts[1])
    try:
        path_id = UUID(id_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "invalid_sync_operation",
                "message": "sync operation path contains an invalid resource id",
                "details": {"operation_index": index},
                "retryable": False,
            },
        ) from exc
    return {spec.path_id_name: path_id}
