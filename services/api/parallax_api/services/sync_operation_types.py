from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class OperationSpec:
    kind: str
    path_parts: tuple[str, ...]
    payload_type: type[BaseModel]
    path_id_name: str | None = None


@dataclass(frozen=True)
class ParsedSyncOperation:
    kind: str
    payload: BaseModel
    activity_id: UUID | None = None
    session_id: UUID | None = None
    annotation_id: UUID | None = None
    event_id: UUID | None = None
    prediction_id: UUID | None = None
