from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from ..schemas.temporal import ConfidenceLabel

TemporalQueryIntent = Literal["duration_summary", "delay_drivers"]

DEFAULT_QUERY_WINDOW_DAYS = 180


@dataclass(frozen=True)
class TemporalQueryWindow:
    label: str
    days: int


@dataclass(frozen=True)
class TemporalQueryPlan:
    intent: TemporalQueryIntent
    window: TemporalQueryWindow
    activity_id: UUID | None
    activity_name: str | None


def build_temporal_query_plan(
    *,
    question: str,
    activity_id: UUID | None,
    activity_name: str | None,
    time_window: str | None,
) -> TemporalQueryPlan:
    return TemporalQueryPlan(
        intent=classify_temporal_query_intent(question),
        window=parse_temporal_query_window(time_window),
        activity_id=activity_id,
        activity_name=activity_name,
    )


def classify_temporal_query_intent(question: str) -> TemporalQueryIntent:
    normalized = question.casefold()
    delay_terms = (
        "delay",
        "delays",
        "delayed",
        "slow",
        "slows",
        "slowed",
        "friction",
        "detour",
        "detours",
        "interruption",
        "interruptions",
        "waiting",
        "wait",
    )
    if any(term in normalized for term in delay_terms):
        return "delay_drivers"
    return "duration_summary"


def parse_temporal_query_window(time_window: str | None) -> TemporalQueryWindow:
    if not time_window:
        return TemporalQueryWindow(label=f"last_{DEFAULT_QUERY_WINDOW_DAYS}_days", days=180)

    normalized = time_window.strip().casefold().replace(" ", "_").replace("-", "_")
    match = re.fullmatch(r"(?:last_)?(\d+)_?(?:d|day|days)", normalized)
    if match:
        days = max(1, min(int(match.group(1)), 3650))
        return TemporalQueryWindow(label=f"last_{days}_days", days=days)

    return TemporalQueryWindow(label=time_window, days=DEFAULT_QUERY_WINDOW_DAYS)


def confidence_for_sample_size(sample_size: int) -> ConfidenceLabel:
    if sample_size >= 10:
        return "high"
    if sample_size >= 5:
        return "medium"
    if sample_size >= 2:
        return "low"
    return "very_low"


def deterministic_duration_answer(facts: dict[str, object]) -> str:
    sample_size = _int_value(facts.get("sample_size"))
    if sample_size == 0:
        return "I do not have reviewed timing history for that scope yet."
    activity_name = facts.get("activity_name") or "that activity"
    active_p50 = _format_seconds(facts.get("active_p50_seconds"))
    active_p80 = _format_seconds(facts.get("active_p80_seconds"))
    wall_p80 = _format_seconds(facts.get("wall_p80_seconds"))
    return (
        f"Based on {sample_size} reviewed runs for {activity_name}, the typical active "
        f"time is {active_p50}, the active p80 is {active_p80}, and the wall p80 is "
        f"{wall_p80}."
    )


def deterministic_delay_answer(facts: dict[str, object]) -> str:
    sample_size = _int_value(facts.get("sample_size"))
    categories = facts.get("friction_categories")
    if sample_size == 0 or not isinstance(categories, list) or not categories:
        return "I do not have reviewed friction evidence for that scope yet."
    first = categories[0]
    if not isinstance(first, dict):
        return "I found friction evidence, but it is not specific enough to summarize."
    category = str(first.get("friction_category") or "unknown")
    event_count = _int_value(first.get("event_count"))
    p80 = _format_seconds(first.get("p80_seconds"))
    return (
        f"The most common reviewed delay pattern is {category}, appearing in "
        f"{event_count} evidence item(s), with a p80 delay of {p80}."
    )


def base_query_limitations(
    *,
    sample_size: int,
    include_raw_quotes: bool,
    raw_quotes_allowed: bool,
) -> list[str]:
    limitations = ["Deterministic facts only; no LLM narration was used."]
    if sample_size == 0:
        limitations.append("No reviewed runs matched the query scope.")
    elif sample_size < 3:
        limitations.append(f"Only {sample_size} reviewed run(s) matched the query scope.")
    if include_raw_quotes and not raw_quotes_allowed:
        limitations.append("Raw quotes are disabled by privacy settings.")
    elif include_raw_quotes:
        limitations.append("Raw quote retrieval is not included in the Phase 7 baseline path.")
    return limitations


def _format_seconds(value: object) -> str:
    if value is None:
        return "unknown"
    seconds = _int_value(value)
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{seconds} seconds"


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return 0
