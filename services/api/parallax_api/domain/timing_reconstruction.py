from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..schemas.timing import TimingEvent, TimingSession, TimingSessionStatus


@dataclass(frozen=True)
class TimingProjection:
    ordered_events: list[TimingEvent]
    session_updates: dict[str, object]


def project_timing_session(session: TimingSession, events: list[TimingEvent]) -> TimingProjection:
    ordered_events = sorted(events, key=_event_order_key)
    out_of_order = [event.id for event in ordered_events] != [event.id for event in events]
    impossible_sequence = False

    started_at: datetime | None = session.started_at
    completed_at: datetime | None = session.completed_at
    active_anchor: datetime | None = None
    computed_active_seconds = 0
    explicit_wall_seconds: int | None = None
    explicit_active_seconds: int | None = None
    terminal_event_type: str | None = None
    status: TimingSessionStatus = (
        "draft" if session.intended_start_at is None else "intent_recorded"
    )

    for event in ordered_events:
        if event.event_type == "intent_recorded":
            status = "intent_recorded"
        elif event.event_type == "session_started":
            if started_at is not None and started_at != event.client_time:
                impossible_sequence = True
            started_at = started_at or event.client_time
            status = "running"
            active_anchor = active_anchor or event.client_time
        elif event.event_type == "session_paused":
            if active_anchor is None:
                impossible_sequence = True
            else:
                computed_active_seconds += _non_negative_seconds(active_anchor, event.client_time)
                active_anchor = None
            status = "paused"
        elif event.event_type == "session_resumed":
            if started_at is None or active_anchor is not None:
                impossible_sequence = True
            active_anchor = event.client_time
            status = "running"
        elif event.event_type == "session_completed":
            if terminal_event_type is not None:
                impossible_sequence = True
            terminal_event_type = event.event_type
            if started_at is None:
                impossible_sequence = True
            if active_anchor is not None:
                computed_active_seconds += _non_negative_seconds(active_anchor, event.client_time)
                active_anchor = None
            completed_at = event.client_time
            explicit_wall_seconds = event.timer_elapsed_seconds
            explicit_active_seconds = event.timer_active_seconds
            status = "completed_unreviewed"
        elif event.event_type == "session_abandoned":
            if terminal_event_type is not None:
                impossible_sequence = True
            terminal_event_type = event.event_type
            status = "abandoned"

    wall_seconds = explicit_wall_seconds
    if wall_seconds is None and started_at is not None and completed_at is not None:
        wall_seconds = _non_negative_seconds(started_at, completed_at)

    active_seconds = explicit_active_seconds
    if active_seconds is None and completed_at is not None:
        active_seconds = computed_active_seconds

    return TimingProjection(
        ordered_events=ordered_events,
        session_updates={
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "wall_seconds": wall_seconds,
            "active_seconds": active_seconds,
            "needs_timeline_recompute": session.needs_timeline_recompute
            or out_of_order
            or impossible_sequence,
        },
    )


def _event_order_key(event: TimingEvent) -> tuple[bool, int, datetime, datetime, UUID]:
    return (
        event.client_sequence is None,
        event.client_sequence if event.client_sequence is not None else 0,
        event.client_time,
        event.server_time,
        event.id,
    )


def _non_negative_seconds(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds()))
