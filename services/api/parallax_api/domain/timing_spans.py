from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..schemas.timing import (
    CountPolicy,
    FrictionCategory,
    TemporalSpanType,
    TimingEvent,
    TimingSession,
)


@dataclass(frozen=True)
class TimingEventSpanDraft:
    span_type: TemporalSpanType
    friction_category: FrictionCategory
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    count_policy: CountPolicy
    count_in_wall_time: bool
    count_in_active_time: bool
    model_update_scopes: list[str]
    start_event_id: UUID | None = None
    end_event_id: UUID | None = None
    checkpoint_run_id: UUID | None = None
    linked_annotation_id: UUID | None = None
    linked_extracted_event_id: UUID | None = None
    user_corrected: bool = False


@dataclass(frozen=True)
class TimingSpanTotals:
    wall_seconds: int | None
    active_seconds: int | None
    setup_seconds: int | None
    detour_seconds: int | None
    interruption_seconds: int | None
    waiting_seconds: int | None
    side_quest_seconds: int | None
    start_latency_seconds: int | None
    transition_seconds: int | None


_SPAN_PAIRS: dict[str, tuple[TemporalSpanType, FrictionCategory, CountPolicy, bool, bool]] = {
    "setup": ("setup", "setup", "review_required", True, False),
    "resource_detour": ("resource_detour", "resource", "wall_only", True, False),
    "interruption": ("interruption", "interruption", "wall_only", True, False),
    "waiting": ("waiting", "waiting", "review_required", True, False),
    "side_quest": ("side_quest", "side_quest", "wall_only", True, False),
    "transition": ("transition", "transition", "separate_transition", False, False),
    "active_work": ("active_work", "none", "wall_and_active", True, True),
}


def derive_timing_spans(
    session: TimingSession,
    events: list[TimingEvent],
) -> list[TimingEventSpanDraft]:
    ordered_events = sorted(events, key=_event_order_key)
    session_started = _first_event_time(ordered_events, "session_started") or session.started_at
    session_completed = (
        _first_event_time(ordered_events, "session_completed") or session.completed_at
    )
    if session_started is None or session_completed is None:
        return []

    spans: list[TimingEventSpanDraft] = []
    open_events: dict[str, TimingEvent] = {}
    pause_started_at: datetime | None = None
    paused_intervals: list[tuple[datetime, datetime]] = []
    explicit_active_spans = False
    bad_timer_started_at: datetime | None = None

    for event in ordered_events:
        event_type = event.event_type
        if event_type == "session_paused":
            pause_started_at = event.client_time
            continue
        if event_type == "session_resumed":
            if pause_started_at is not None:
                paused_intervals.append((pause_started_at, event.client_time))
                pause_started_at = None
            continue
        if event_type == "bad_timer_marked":
            bad_timer_started_at = event.client_time
            continue
        if not event_type.endswith("_started") and not event_type.endswith("_completed"):
            continue

        stem = event_type.removesuffix("_started").removesuffix("_completed")
        if stem not in _SPAN_PAIRS:
            continue
        if event_type.endswith("_started"):
            open_events[stem] = event
            continue

        start_event = open_events.pop(stem, None)
        if start_event is None:
            continue
        span = _span_from_pair(stem, start_event, event)
        if span is None:
            continue
        explicit_active_spans = explicit_active_spans or span.span_type == "active_work"
        spans.append(span)

    if pause_started_at is not None:
        paused_intervals.append((pause_started_at, session_completed))

    if bad_timer_started_at is not None and bad_timer_started_at < session_completed:
        spans.append(
            TimingEventSpanDraft(
                span_type="bad_timer",
                friction_category="timer_quality",
                started_at=bad_timer_started_at,
                ended_at=session_completed,
                duration_seconds=_non_negative_seconds(bad_timer_started_at, session_completed),
                count_policy="do_not_count",
                count_in_wall_time=False,
                count_in_active_time=False,
                model_update_scopes=[],
            )
        )
        session_completed = bad_timer_started_at

    if not explicit_active_spans:
        active_blockers = [
            (span.started_at, span.ended_at)
            for span in spans
            if span.ended_at is not None
            and span.count_in_wall_time
            and not span.count_in_active_time
        ]
        active_blockers.extend(paused_intervals)
        for start, end in _subtract_intervals(
            session_started,
            session_completed,
            active_blockers,
        ):
            duration = _non_negative_seconds(start, end)
            if duration > 0:
                spans.append(
                    TimingEventSpanDraft(
                        span_type="active_work",
                        friction_category="none",
                        started_at=start,
                        ended_at=end,
                        duration_seconds=duration,
                        count_policy="wall_and_active",
                        count_in_wall_time=True,
                        count_in_active_time=True,
                        model_update_scopes=["active_duration", "wall_duration"],
                    )
                )

    return sorted(spans, key=lambda span: (span.started_at, span.span_type))


def summarize_timing_spans(
    session: TimingSession,
    spans: list[TimingEventSpanDraft],
) -> TimingSpanTotals:
    return TimingSpanTotals(
        wall_seconds=session.wall_seconds,
        active_seconds=_sum_seconds(spans, count_in_active_time=True)
        if spans
        else session.active_seconds,
        setup_seconds=_sum_seconds(spans, span_type="setup"),
        detour_seconds=_sum_seconds(spans, span_type="resource_detour"),
        interruption_seconds=_sum_seconds(spans, span_type="interruption"),
        waiting_seconds=_sum_seconds(spans, span_type="waiting"),
        side_quest_seconds=_sum_seconds(spans, span_type="side_quest"),
        start_latency_seconds=session.start_latency_seconds,
        transition_seconds=_sum_seconds(spans, span_type="transition"),
    )


def _span_from_pair(
    stem: str,
    start_event: TimingEvent,
    end_event: TimingEvent,
) -> TimingEventSpanDraft | None:
    if end_event.client_time < start_event.client_time:
        return None
    span_type, friction_category, count_policy, count_wall, count_active = _SPAN_PAIRS[stem]
    scopes = ["active_duration", "wall_duration"] if count_active else ["friction_patterns"]
    return TimingEventSpanDraft(
        span_type=span_type,
        friction_category=friction_category,
        started_at=start_event.client_time,
        ended_at=end_event.client_time,
        duration_seconds=_non_negative_seconds(start_event.client_time, end_event.client_time),
        count_policy=count_policy,
        count_in_wall_time=count_wall,
        count_in_active_time=count_active,
        model_update_scopes=scopes,
        start_event_id=start_event.id,
        end_event_id=end_event.id,
    )


def _event_order_key(event: TimingEvent) -> tuple[bool, int, datetime, datetime, UUID]:
    return (
        event.client_sequence is None,
        event.client_sequence if event.client_sequence is not None else 0,
        event.client_time,
        event.server_time,
        event.id,
    )


def _first_event_time(events: list[TimingEvent], event_type: str) -> datetime | None:
    for event in events:
        if event.event_type == event_type:
            return event.client_time
    return None


def _subtract_intervals(
    started_at: datetime,
    ended_at: datetime,
    blockers: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    ranges: list[tuple[datetime, datetime]] = [(started_at, ended_at)]
    for block_start, block_end in sorted(blockers):
        if block_end <= block_start:
            continue
        next_ranges: list[tuple[datetime, datetime]] = []
        for range_start, range_end in ranges:
            if block_end <= range_start or block_start >= range_end:
                next_ranges.append((range_start, range_end))
                continue
            if range_start < block_start:
                next_ranges.append((range_start, min(block_start, range_end)))
            if block_end < range_end:
                next_ranges.append((max(block_end, range_start), range_end))
        ranges = next_ranges
    return ranges


def _sum_seconds(
    spans: list[TimingEventSpanDraft],
    *,
    span_type: TemporalSpanType | None = None,
    count_in_active_time: bool | None = None,
) -> int | None:
    total = 0
    matched = False
    for span in spans:
        if span.duration_seconds is None:
            continue
        if span_type is not None and span.span_type != span_type:
            continue
        if count_in_active_time is not None and span.count_in_active_time != count_in_active_time:
            continue
        total += span.duration_seconds
        matched = True
    return total if matched else None


def _non_negative_seconds(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds()))
