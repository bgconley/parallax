from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope
from .context import PrivacyClass
from .timing import CountPolicy, FrictionCategory, TemporalSpanType

ConfirmationState = Literal[
    "auto_logged",
    "needs_confirmation",
    "confirmed",
    "corrected",
    "ignored",
    "deferred_to_review",
]
ExtractionStatus = Literal[
    "queued",
    "needs_confirmation",
    "extracted",
    "blocked_by_privacy",
    "model_output_invalid",
    "model_unavailable",
    "no_candidate",
]


class ExtractAnnotationRequest(ApiModel):
    mutation: MutationEnvelope
    force: bool = False


class ConfirmExtractedEventRequest(ApiModel):
    mutation: MutationEnvelope
    confirmation_state: Literal["confirmed", "ignored"]


class CorrectExtractedEventRequest(ApiModel):
    mutation: MutationEnvelope
    span_type: TemporalSpanType
    friction_category: FrictionCategory
    friction_subtype: str | None = None
    resource_name: str | None = None
    location_from: str | None = None
    location_to: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    count_policy: CountPolicy
    count_in_wall_time: bool
    count_in_active_time: bool
    suggested_preflight_text: str | None = None
    user_note: str | None = None


class ExtractedContextEvent(ApiModel):
    id: UUID
    user_id: UUID
    annotation_id: UUID
    session_id: UUID
    checkpoint_run_id: UUID | None = None
    span_type: TemporalSpanType
    friction_category: FrictionCategory
    friction_subtype: str | None = None
    resource_name: str | None = None
    location_from: str | None = None
    location_to: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    count_policy: CountPolicy
    count_in_wall_time: bool
    count_in_active_time: bool
    model_update_scopes: list[str]
    suggested_preflight_text: str | None = None
    confidence: float = Field(ge=0, le=1)
    confirmation_state: ConfirmationState
    sensitive_data_detected: bool
    model_invocation_id: UUID | None = None
    source_json: dict[str, object]
    user_correction_json: dict[str, object]


class ExtractAnnotationResponse(ApiModel):
    annotation_id: UUID
    status: ExtractionStatus
    model_invocation_id: UUID | None = None
    extracted_events: list[ExtractedContextEvent]


class ModelInvocationRecord(ApiModel):
    id: UUID
    user_id: UUID | None
    role: str
    provider: str
    model_name: str
    model_version: str | None = None
    prompt_version: str
    schema_version: str | None = None
    input_privacy_class: PrivacyClass
    request_hash: str | None = None
    output_hash: str | None = None
    schema_valid: bool | None = None
    repair_count: int = Field(default=0, ge=0)
    fallback_used: bool
    latency_ms: int | None = Field(default=None, ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    metadata: dict[str, object]
    created_at: datetime


class TemporalCorrection(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID | None = None
    entity_type: str
    entity_id: UUID
    correction_type: str
    before_json: dict[str, object]
    after_json: dict[str, object]
    user_note: str | None = None
    created_at: datetime
