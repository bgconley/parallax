from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope

RelationshipKind = Literal[
    "same_as",
    "alias_of",
    "part_of",
    "has_checkpoint",
    "variant_of",
    "related_to",
    "usually_before",
    "usually_after",
]
PreflightCheckState = Literal["active", "snoozed", "hidden", "retired"]
PreflightCheckSource = Literal[
    "user_created",
    "model_suggested",
    "resource_dependency",
    "checkpoint_pattern",
]


class AddActivityAliasRequest(ApiModel):
    mutation: MutationEnvelope
    alias_text: str = Field(min_length=1)
    user_confirmed: bool = True


class ActivityAlias(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    alias_text: str
    normalized_alias: str
    source: Literal["user", "system_suggested", "imported"]
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool
    rejected: bool
    created_at: datetime


class CreateActivityRelationshipRequest(ApiModel):
    mutation: MutationEnvelope
    to_activity_id: UUID
    kind: RelationshipKind
    metadata: dict[str, object] = Field(default_factory=dict)


class ActivityRelationship(ApiModel):
    id: UUID
    user_id: UUID
    from_activity_id: UUID
    to_activity_id: UUID
    kind: RelationshipKind
    metadata: dict[str, object]
    user_confirmed: bool
    created_at: datetime


class CheckpointTemplateInput(ApiModel):
    label: str = Field(min_length=1)
    sequence_order: int = Field(ge=1)
    optional: bool = False
    phase_type: str | None = None


class PutCheckpointsRequest(ApiModel):
    mutation: MutationEnvelope
    checkpoints: list[CheckpointTemplateInput]


class CheckpointTemplate(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    sequence_order: int = Field(ge=1)
    label: str = Field(min_length=1)
    phase_type: str | None = None
    optional: bool
    usual_active_p50_seconds: int | None = Field(default=None, ge=0)
    usual_active_p80_seconds: int | None = Field(default=None, ge=0)
    usual_wall_p50_seconds: int | None = Field(default=None, ge=0)
    usual_wall_p80_seconds: int | None = Field(default=None, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreatePreflightCheckRequest(ApiModel):
    mutation: MutationEnvelope
    check_text: str = Field(min_length=1)
    source: PreflightCheckSource = "user_created"


class PreflightCheck(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    check_text: str = Field(min_length=1)
    state: PreflightCheckState
    source: PreflightCheckSource
    confidence: float | None = Field(default=None, ge=0, le=1)
    failure_count: int = Field(ge=0)
    last_triggered_at: datetime | None = None
    source_event_id: UUID | None = None
