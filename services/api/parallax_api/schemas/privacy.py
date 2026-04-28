from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope

DeleteScope = Literal[
    "raw_context",
    "location_context",
    "radio_context",
    "place_context",
    "context_features",
    "audio",
    "activity",
    "account",
]
PrivacyRequestType = Literal["export", "redact", "delete"]


class PrivacySettings(ApiModel):
    user_id: UUID
    retain_raw_context: bool
    retain_transcripts: bool
    retain_audio: bool
    allow_cloud_llm_fallback: bool
    allow_raw_notes_in_query_answers: bool
    allow_embedding_of_sensitive_notes: bool
    community_aggregation_opt_in: bool
    raw_context_retention_days: int | None = Field(default=None, ge=0)
    audio_retention_days: int | None = Field(default=None, ge=0)
    updated_at: datetime


class UpdatePrivacySettingsRequest(ApiModel):
    mutation: MutationEnvelope
    settings: PrivacySettings


class PrivacyRedactRequest(ApiModel):
    mutation: MutationEnvelope
    entity_type: str = Field(min_length=1)
    entity_id: UUID
    reason: str | None = None


class PrivacyExportRequest(ApiModel):
    mutation: MutationEnvelope
    include_raw_context: bool = True
    include_audio: bool = False


class PrivacyDeleteRequest(ApiModel):
    mutation: MutationEnvelope
    delete_scope: DeleteScope
    entity_id: UUID | None = None
    confirm: bool


class PrivacyWorkflowResponse(ApiModel):
    request_id: UUID
    request_type: PrivacyRequestType
    status: str
    workflow_run_id: UUID
