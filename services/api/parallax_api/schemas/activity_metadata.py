from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

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
RelationshipState = Literal["suggested", "confirmed", "rejected"]
PreflightCheckState = Literal["suggested", "active", "snoozed", "hidden", "retired"]
PreflightCheckSource = Literal[
    "user_created",
    "model_suggested",
    "resource_dependency",
    "checkpoint_pattern",
]
IdentityDecision = Literal["accept", "reject"]
PreflightDecision = Literal["accept", "hide", "snooze", "retire"]


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
    user_confirmed: bool = True


class ActivityRelationship(ApiModel):
    id: UUID
    user_id: UUID
    from_activity_id: UUID
    to_activity_id: UUID
    kind: RelationshipKind
    metadata: dict[str, object]
    user_confirmed: bool
    state: RelationshipState = "confirmed"
    created_at: datetime


class DecideActivityAliasRequest(ApiModel):
    mutation: MutationEnvelope
    decision: IdentityDecision
    reason: str | None = None


class DecideActivityRelationshipRequest(ApiModel):
    mutation: MutationEnvelope
    decision: IdentityDecision
    reason: str | None = None


class ActivityMergePreviewRequest(ApiModel):
    target_activity_id: UUID


class ActivityMergeRequest(ApiModel):
    mutation: MutationEnvelope
    target_activity_id: UUID
    reason: str | None = None


class ActivityMergePreview(ApiModel):
    source_activity_id: UUID
    target_activity_id: UUID
    relationship_kind: Literal["same_as"] = "same_as"
    affected_session_count: int = Field(ge=0)
    history_preservation: Literal["source_activity_soft_merged"] = "source_activity_soft_merged"
    requires_confirmation: bool = True


class ActivityIdentityChange(ApiModel):
    id: UUID
    user_id: UUID
    change_type: Literal["merge"]
    source_activity_id: UUID
    target_activity_id: UUID
    affected_session_count: int = Field(ge=0)
    audit_id: UUID
    created_at: datetime


class ActivitySplitPreviewRequest(ApiModel):
    proposed_display_name: str = Field(min_length=1)
    session_ids: list[UUID] = Field(default_factory=list)


class ActivitySplitPreview(ApiModel):
    source_activity_id: UUID
    proposed_display_name: str
    movable_session_count: int = Field(ge=0)
    requires_confirmation: bool = True
    commit_supported: bool = False


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
    source_dependency_id: UUID | None = None
    snoozed_until: datetime | None = None
    evidence_count: int = Field(default=0, ge=0)
    evidence_summary: str | None = None
    last_decided_at: datetime | None = None
    decision_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DecidePreflightCheckRequest(ApiModel):
    mutation: MutationEnvelope
    decision: PreflightDecision
    snoozed_until: datetime | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_snooze_target(self) -> DecidePreflightCheckRequest:
        if self.decision == "snooze" and self.snoozed_until is None:
            raise ValueError("snoozed_until is required when decision is snooze")
        return self


class ResourceDependency(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    resource_name: str
    required_state: str | None = None
    usual_location: str | None = None
    failure_count: int = Field(ge=0)
    median_delay_seconds: int | None = Field(default=None, ge=0)
    p80_delay_seconds: int | None = Field(default=None, ge=0)
    suggest_precheck: bool
    last_failed_at: datetime | None = None
    created_from_event_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
