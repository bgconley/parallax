from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .activity import TimingMode
from .common import ApiModel, MutationEnvelope

WorkMode = Literal["unknown", "home", "wfh", "office", "travel", "weekend", "errand", "hybrid"]
ActorMode = Literal["solo", "assisted", "delegated", "unknown"]
TimingSessionStatus = Literal[
    "draft",
    "intent_recorded",
    "running",
    "paused",
    "completed_unreviewed",
    "reviewed",
    "discarded",
    "abandoned",
]
TimingEventType = Literal[
    "intent_recorded",
    "session_started",
    "session_paused",
    "session_resumed",
    "session_completed",
    "session_abandoned",
    "checkpoint_started",
    "checkpoint_completed",
    "checkpoint_skipped",
    "annotation_captured",
    "extracted_event_created",
    "active_work_started",
    "active_work_completed",
    "setup_started",
    "setup_completed",
    "resource_detour_started",
    "resource_detour_completed",
    "interruption_started",
    "interruption_completed",
    "waiting_started",
    "waiting_completed",
    "side_quest_started",
    "side_quest_completed",
    "transition_started",
    "transition_completed",
    "bad_timer_marked",
    "scope_changed",
    "user_correction_applied",
    "review_saved",
    "sync_reconciled",
]
TemporalSpanType = Literal[
    "active_work",
    "setup",
    "resource_detour",
    "interruption",
    "waiting",
    "side_quest",
    "start_latency",
    "transition",
    "body_energy",
    "decision_loop",
    "attention_drift",
    "environment_friction",
    "bad_timer",
    "scope_change",
    "other",
]
FrictionCategory = Literal[
    "none",
    "resource",
    "setup",
    "transition",
    "interruption",
    "waiting",
    "side_quest",
    "decision",
    "attention",
    "body_energy",
    "environment",
    "timer_quality",
    "scope",
    "unknown",
]
CountPolicy = Literal[
    "wall_and_active",
    "wall_only",
    "active_only",
    "separate_start_latency",
    "separate_transition",
    "do_not_count",
    "review_required",
]
RunQuality = Literal[
    "unknown",
    "typical",
    "useful_unusual",
    "assisted",
    "partial",
    "bad_timer",
    "corrupted",
    "do_not_train",
]
ModelInclusion = Literal[
    "not_reviewed",
    "full",
    "active_duration_only",
    "wall_envelope_only",
    "friction_patterns_only",
    "query_evidence_only",
    "exclude",
]
ModelUpdateDecisionType = Literal[
    "save_useful_run",
    "mark_unusual",
    "save_partial",
    "active_only",
    "friction_only",
    "query_evidence_only",
    "discard_timing_keep_note",
    "discard_all",
]


class TimingEvent(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    event_type: TimingEventType
    client_time: datetime
    server_time: datetime
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    client_sequence: int | None = Field(default=None, ge=0)
    client_mutation_id: str
    client_device_id: str
    idempotency_key: str
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    payload: dict[str, object]


class TimingEventSpan(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    checkpoint_run_id: UUID | None = None
    span_type: TemporalSpanType
    friction_category: FrictionCategory
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    count_policy: CountPolicy
    count_in_wall_time: bool
    count_in_active_time: bool
    model_update_scopes: list[str]
    linked_annotation_id: UUID | None = None
    linked_extracted_event_id: UUID | None = None
    user_corrected: bool


CheckpointRunStatus = Literal[
    "planned",
    "running",
    "completed",
    "skipped",
    "moved",
    "merged",
    "deleted",
]


class CheckpointRun(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    checkpoint_template_id: UUID | None = None
    sequence_order: int = Field(ge=1)
    label: str = Field(min_length=1)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    active_seconds: int | None = Field(default=None, ge=0)
    wall_seconds: int | None = Field(default=None, ge=0)
    friction_seconds: int | None = Field(default=None, ge=0)
    status: CheckpointRunStatus
    user_corrected: bool
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class StartLatencyObservation(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    session_id: UUID | None = None
    intended_start_at: datetime | None = None
    nudge_shown_at: datetime | None = None
    actual_start_at: datetime
    latency_seconds: int = Field(ge=0)
    reason_category: FrictionCategory
    evidence_annotation_id: UUID | None = None
    created_at: datetime


class TransitionObservation(ApiModel):
    id: UUID
    user_id: UUID
    from_session_id: UUID | None = None
    to_session_id: UUID | None = None
    from_checkpoint_run_id: UUID | None = None
    to_checkpoint_run_id: UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transition_seconds: int | None = Field(default=None, ge=0)
    reason_category: FrictionCategory
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class TimingSession(ApiModel):
    id: UUID
    user_id: UUID
    activity_id: UUID
    client_session_id: str | None = None
    source_device_id: str | None = None
    mode: TimingMode
    status: TimingSessionStatus
    work_mode: WorkMode
    actor_mode: ActorMode
    intended_start_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    active_seconds: int | None = Field(default=None, ge=0)
    wall_seconds: int | None = Field(default=None, ge=0)
    setup_seconds: int | None = Field(default=None, ge=0)
    detour_seconds: int | None = Field(default=None, ge=0)
    interruption_seconds: int | None = Field(default=None, ge=0)
    waiting_seconds: int | None = Field(default=None, ge=0)
    side_quest_seconds: int | None = Field(default=None, ge=0)
    start_latency_seconds: int | None = Field(default=None, ge=0)
    transition_seconds: int | None = Field(default=None, ge=0)
    run_quality: RunQuality
    model_inclusion: ModelInclusion
    needs_timeline_recompute: bool
    events: list[TimingEvent] = Field(default_factory=list)
    spans: list[TimingEventSpan] = Field(default_factory=list)


class CreateTimingSessionRequest(ApiModel):
    mutation: MutationEnvelope
    activity_id: UUID
    client_session_id: str
    mode: TimingMode = "whole_task"
    work_mode: WorkMode = "unknown"
    actor_mode: ActorMode = "unknown"
    intended_start_at: datetime | None = None
    user_pre_estimate_seconds: int | None = Field(default=None, ge=0)


class AppendTimingEventRequest(ApiModel):
    mutation: MutationEnvelope
    event_type: TimingEventType
    client_time: datetime
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class CompleteTimingSessionRequest(ApiModel):
    mutation: MutationEnvelope
    completed_at: datetime
    timer_elapsed_seconds: int | None = Field(default=None, ge=0)
    timer_active_seconds: int | None = Field(default=None, ge=0)
    capture_context_snapshot_id: UUID | None = None
    capture_context_snapshot_ref: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class ReviewTimingSessionRequest(ApiModel):
    mutation: MutationEnvelope
    decision: ModelUpdateDecisionType
    model_inclusion: ModelInclusion
    scopes: list[str]
    span_overrides: list[dict[str, object]] = Field(default_factory=list)
    user_note: str | None = None


class ModelUpdateDecision(ApiModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    decision: ModelUpdateDecisionType
    model_inclusion: ModelInclusion
    scopes: list[str]
    reviewed_at: datetime
    user_note: str | None = None
    payload: dict[str, object]


class CreateTimingEventSpanRequest(ApiModel):
    mutation: MutationEnvelope
    span: TimingEventSpan
