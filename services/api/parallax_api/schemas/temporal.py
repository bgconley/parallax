from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import ApiModel, MutationEnvelope
from .timing import ActorMode, WorkMode

PredictionType = Literal[
    "duration_range",
    "temporal_envelope",
    "start_by",
    "checkpoint_range",
]
PredictionBasis = Literal[
    "generic_prior",
    "personal_last_time",
    "personal_rolling_stats",
    "personal_model",
    "hybrid",
    "insufficient_data",
]
ConfidenceLabel = Literal["very_low", "low", "medium", "high"]
PredictionOutcomeType = Literal["completed", "skipped", "deferred", "abandoned", "ignored"]
TemporalQueryStatus = Literal["pending", "complete", "failed", "corrected"]
FeatureFamily = Literal[
    "duration_prediction",
    "start_latency",
    "transition_latency",
    "friction",
    "place_inference",
    "prompt_policy",
    "anomaly_detection",
]


class CreatePredictionRequest(ApiModel):
    mutation: MutationEnvelope
    activity_id: UUID
    prediction_type: PredictionType
    deadline: datetime | None = None
    work_mode: WorkMode = "unknown"


class TemporalPrediction(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    prediction_type: PredictionType
    work_mode: WorkMode
    actor_mode: ActorMode
    active_p50_seconds: int | None = Field(default=None, ge=0)
    active_p80_seconds: int | None = Field(default=None, ge=0)
    wall_p50_seconds: int | None = Field(default=None, ge=0)
    wall_p80_seconds: int | None = Field(default=None, ge=0)
    setup_risk_seconds_p80: int | None = Field(default=None, ge=0)
    start_latency_p80_seconds: int | None = Field(default=None, ge=0)
    basis: PredictionBasis
    sample_size: int = Field(ge=0)
    confidence: ConfidenceLabel
    warnings: list[str]
    evidence_bundle_id: UUID | None = None


class RecordPredictionOutcomeRequest(ApiModel):
    mutation: MutationEnvelope
    session_id: UUID | None = None
    outcome_type: PredictionOutcomeType
    actual_active_seconds: int | None = Field(default=None, ge=0)
    actual_wall_seconds: int | None = Field(default=None, ge=0)


class PredictionOutcome(ApiModel):
    id: UUID
    user_id: UUID
    prediction_id: UUID
    session_id: UUID | None = None
    outcome_type: PredictionOutcomeType
    actual_active_seconds: int | None = Field(default=None, ge=0)
    actual_wall_seconds: int | None = Field(default=None, ge=0)
    created_at: datetime


class TemporalQueryRequest(ApiModel):
    mutation: MutationEnvelope
    question: str = Field(min_length=1)
    activity_id: UUID | None = None
    time_window: str | None = None
    include_raw_quotes: bool = False


class TemporalQueryEvidenceItem(ApiModel):
    entity_type: str
    entity_id: UUID
    summary: str
    occurred_at: datetime | None = None
    score: float | None = None


class TemporalQueryAnswer(ApiModel):
    id: UUID
    user_id: UUID
    question: str = Field(min_length=1)
    answer: str | None = None
    confidence: ConfidenceLabel
    sample_size: int = Field(ge=0)
    time_window: str | None = None
    computed_facts: dict[str, object]
    limitations: list[str]
    evidence: list[TemporalQueryEvidenceItem]
    status: TemporalQueryStatus


PrivacyClass = Literal["normal", "sensitive", "private"]


class TemporalFeatureVector(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID | None = None
    session_id: UUID | None = None
    snapshot_id: UUID | None = None
    feature_schema_version: str
    feature_family: FeatureFamily
    features: dict[str, object]
    source_entity_refs: list[dict[str, object]]
    privacy_class: PrivacyClass
    model_eligible: bool
    exclusion_reason: str | None = None
    generated_at: datetime


class RecomputeFeatureVectorsRequest(ApiModel):
    mutation: MutationEnvelope
    user_id: UUID | None = None
    activity_id: UUID | None = None
    session_id: UUID | None = None
    feature_families: list[FeatureFamily]
    reason: str


class JobAcceptedResponse(ApiModel):
    workflow_run_id: UUID
    status: str
