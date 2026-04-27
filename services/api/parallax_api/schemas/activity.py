from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope

TimingMode = Literal[
    "estimate_only",
    "whole_task",
    "checkpointed",
    "routine",
    "calibration",
    "passive",
]
PrivacyClass = Literal["normal", "sensitive", "private"]


class Activity(ApiModel):
    id: UUID
    user_id: UUID
    display_name: str = Field(min_length=1)
    canonical_key: str | None = None
    description: str | None = None
    status: Literal["active", "archived", "merged"]
    merged_into_activity_id: UUID | None = None
    default_timing_mode: TimingMode
    privacy_class: PrivacyClass
    created_at: datetime
    updated_at: datetime


class CreateActivityRequest(ApiModel):
    mutation: MutationEnvelope
    display_name: str = Field(min_length=1)
    description: str | None = None
    default_timing_mode: TimingMode = "whole_task"
    privacy_class: PrivacyClass = "normal"


class ResolveActivityRequest(ApiModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=25)


class ResolveActivityCandidate(ApiModel):
    activity: Activity | None
    display_name: str
    confidence: float = Field(ge=0, le=1)
    match_type: Literal["canonical", "alias", "fuzzy", "no_match"]
    evidence: dict[str, object]


class ResolveActivityResponse(ApiModel):
    candidates: list[ResolveActivityCandidate]
    recommended_activity_id: UUID | None = None
    requires_confirmation: bool
