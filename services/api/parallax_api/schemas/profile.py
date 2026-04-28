from __future__ import annotations

from typing import Literal

from pydantic import Field

from .activity import Activity
from .common import ApiModel
from .timing import TimingSession

ConfidenceLabel = Literal["very_low", "low", "medium", "high"]


class ActivityProfileStats(ApiModel):
    sample_size: int = Field(ge=0)
    confidence: ConfidenceLabel
    active_p50_seconds: int | None = Field(default=None, ge=0)
    active_p80_seconds: int | None = Field(default=None, ge=0)
    wall_p50_seconds: int | None = Field(default=None, ge=0)
    wall_p80_seconds: int | None = Field(default=None, ge=0)
    start_latency_p80_seconds: int | None = Field(default=None, ge=0)
    top_friction: list[dict[str, object]] = Field(default_factory=list)


class ActivityProfile(ApiModel):
    activity: Activity
    latest_stats: ActivityProfileStats | None = None
    preflight_checks: list[dict[str, object]] = Field(default_factory=list)
    recent_sessions: list[TimingSession] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
