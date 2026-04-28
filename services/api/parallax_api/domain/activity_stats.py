from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev

from ..schemas.profile import ActivityProfileStats, ConfidenceLabel
from ..schemas.timing import TimingSession


@dataclass(frozen=True)
class ActivityStatsComputation:
    stats: ActivityProfileStats | None
    limitations: list[str]


def compute_activity_stats(sessions: list[TimingSession]) -> ActivityStatsComputation:
    active_values = [
        session.active_seconds
        for session in sessions
        if session.model_inclusion in {"full", "active_duration_only"}
        and session.active_seconds is not None
    ]
    wall_values = [
        session.wall_seconds
        for session in sessions
        if session.model_inclusion in {"full", "wall_envelope_only"}
        and session.wall_seconds is not None
    ]
    sample_size = max(len(active_values), len(wall_values))
    if sample_size == 0:
        return ActivityStatsComputation(
            stats=None,
            limitations=["No reviewed runs are eligible for duration stats."],
        )

    limitations = _limitations(sample_size)
    stats = ActivityProfileStats(
        sample_size=sample_size,
        confidence=_confidence(sample_size, active_values + wall_values),
        active_p50_seconds=_percentile_nearest_rank(active_values, 0.50),
        active_p80_seconds=_percentile_nearest_rank(active_values, 0.80),
        wall_p50_seconds=_percentile_nearest_rank(wall_values, 0.50),
        wall_p80_seconds=_percentile_nearest_rank(wall_values, 0.80),
        start_latency_p80_seconds=_percentile_nearest_rank(
            [
                session.start_latency_seconds
                for session in sessions
                if session.start_latency_seconds is not None
            ],
            0.80,
        ),
        top_friction=_top_friction(sessions),
    )
    return ActivityStatsComputation(stats=stats, limitations=limitations)


def _percentile_nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, int((len(ordered) * percentile) + 0.999999))
    return ordered[min(rank - 1, len(ordered) - 1)]


def _confidence(sample_size: int, values: list[int]) -> ConfidenceLabel:
    if sample_size < 2:
        return "very_low"
    if sample_size < 5:
        return "low"
    label: ConfidenceLabel = "medium" if sample_size < 10 else "high"
    if len(values) >= 3:
        mean = sum(values) / len(values)
        if mean > 0 and pstdev(values) / mean > 0.75:
            return "low" if label == "medium" else "medium"
    return label


def _limitations(sample_size: int) -> list[str]:
    if sample_size == 1:
        return ["Only 1 reviewed run is available."]
    if sample_size < 5:
        return [f"Only {sample_size} reviewed runs are available."]
    return []


def _top_friction(sessions: list[TimingSession]) -> list[dict[str, object]]:
    totals = {
        "resource": sum(session.detour_seconds or 0 for session in sessions),
        "interruption": sum(session.interruption_seconds or 0 for session in sessions),
        "waiting": sum(session.waiting_seconds or 0 for session in sessions),
        "side_quest": sum(session.side_quest_seconds or 0 for session in sessions),
        "setup": sum(session.setup_seconds or 0 for session in sessions),
    }
    ranked = [
        {"friction_category": category, "total_seconds": seconds}
        for category, seconds in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        if seconds > 0
    ]
    return ranked[:5]
