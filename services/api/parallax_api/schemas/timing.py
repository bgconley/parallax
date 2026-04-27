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
    run_quality: Literal[
        "unknown",
        "typical",
        "useful_unusual",
        "assisted",
        "partial",
        "bad_timer",
        "corrupted",
        "do_not_train",
    ]
    model_inclusion: Literal[
        "not_reviewed",
        "full",
        "active_duration_only",
        "wall_envelope_only",
        "friction_patterns_only",
        "query_evidence_only",
        "exclude",
    ]
    needs_timeline_recompute: bool
    events: list[TimingEvent] = Field(default_factory=list)
    spans: list[dict[str, object]] = Field(default_factory=list)


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
