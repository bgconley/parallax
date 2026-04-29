from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..schemas.timing import FrictionCategory, TimingSession
from .timing_spans import TimingEventSpanDraft


@dataclass(frozen=True)
class StartLatencyObservationDraft:
    activity_id: UUID
    session_id: UUID
    intended_start_at: datetime
    actual_start_at: datetime
    latency_seconds: int
    reason_category: FrictionCategory = "unknown"
    evidence_annotation_id: UUID | None = None


@dataclass(frozen=True)
class TransitionObservationDraft:
    from_session_id: UUID
    to_session_id: UUID | None
    from_checkpoint_run_id: UUID | None
    to_checkpoint_run_id: UUID | None
    started_at: datetime | None
    ended_at: datetime | None
    transition_seconds: int | None
    reason_category: FrictionCategory
    metadata: dict[str, object]


def derive_start_latency_observation(
    session: TimingSession,
) -> StartLatencyObservationDraft | None:
    if (
        session.intended_start_at is None
        or session.started_at is None
        or session.started_at <= session.intended_start_at
    ):
        return None
    return StartLatencyObservationDraft(
        activity_id=session.activity_id,
        session_id=session.id,
        intended_start_at=session.intended_start_at,
        actual_start_at=session.started_at,
        latency_seconds=int((session.started_at - session.intended_start_at).total_seconds()),
    )


def derive_transition_observations(
    session: TimingSession,
    spans: list[TimingEventSpanDraft],
) -> list[TransitionObservationDraft]:
    observations: list[TransitionObservationDraft] = []
    for span in spans:
        if span.span_type != "transition":
            continue
        observations.append(
            TransitionObservationDraft(
                from_session_id=session.id,
                to_session_id=None,
                from_checkpoint_run_id=None,
                to_checkpoint_run_id=None,
                started_at=span.started_at,
                ended_at=span.ended_at,
                transition_seconds=span.duration_seconds,
                reason_category=span.friction_category,
                metadata={
                    "source": "timing_event_span",
                    "start_event_id": str(span.start_event_id)
                    if span.start_event_id is not None
                    else None,
                    "end_event_id": str(span.end_event_id)
                    if span.end_event_id is not None
                    else None,
                },
            )
        )
    return observations
