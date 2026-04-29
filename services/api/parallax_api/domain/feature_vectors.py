from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ..schemas.context import ContextCapturePolicy
from ..schemas.temporal import FeatureFamily, PrivacyClass
from ..schemas.timing import TimingSession
from .activity_stats import percentile_nearest_rank

FEATURE_SCHEMA_VERSION = "1.3.0"


@dataclass(frozen=True)
class TemporalFeatureVectorDraft:
    activity_id: UUID | None
    session_id: UUID | None
    snapshot_id: UUID | None
    feature_schema_version: str
    feature_family: FeatureFamily
    features: dict[str, object]
    source_entity_refs: list[dict[str, object]]
    privacy_class: PrivacyClass
    model_eligible: bool
    exclusion_reason: str | None
    generated_at: datetime


def build_temporal_feature_vectors(
    *,
    activity_id: UUID | None,
    session_id: UUID | None,
    feature_families: list[FeatureFamily],
    reviewed_sessions: list[TimingSession],
    context_policy: ContextCapturePolicy,
    eligible_snapshot_count: int,
    generated_at: datetime | None = None,
) -> list[TemporalFeatureVectorDraft]:
    now = generated_at or datetime.now(UTC)
    vectors: list[TemporalFeatureVectorDraft] = []
    refs = _session_refs(reviewed_sessions)
    for family in feature_families:
        if family == "duration_prediction":
            vectors.append(
                _duration_vector(activity_id, session_id, reviewed_sessions, refs, now)
            )
        elif family == "start_latency":
            vectors.append(
                _start_latency_vector(activity_id, session_id, reviewed_sessions, refs, now)
            )
        elif family == "transition_latency":
            vectors.append(
                _latency_total_vector(
                    family,
                    "transition_seconds",
                    activity_id,
                    session_id,
                    reviewed_sessions,
                    refs,
                    now,
                )
            )
        elif family == "friction":
            vectors.append(_friction_vector(activity_id, session_id, reviewed_sessions, refs, now))
        elif family == "place_inference":
            vectors.append(
                _place_vector(
                    activity_id,
                    session_id,
                    context_policy,
                    eligible_snapshot_count,
                    refs,
                    now,
                )
            )
        else:
            vectors.append(
                _generic_vector(family, activity_id, session_id, reviewed_sessions, refs, now)
            )
    return vectors


def _duration_vector(
    activity_id: UUID | None,
    session_id: UUID | None,
    sessions: list[TimingSession],
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    active_values = [
        session.active_seconds
        for session in sessions
        if session.active_seconds is not None
    ]
    wall_values = [session.wall_seconds for session in sessions if session.wall_seconds is not None]
    sample_size = max(len(active_values), len(wall_values))
    return _vector(
        activity_id,
        session_id,
        "duration_prediction",
        {
            "sample_size": sample_size,
            "active_p50_seconds": percentile_nearest_rank(active_values, 0.50),
            "active_p80_seconds": percentile_nearest_rank(active_values, 0.80),
            "wall_p50_seconds": percentile_nearest_rank(wall_values, 0.50),
            "wall_p80_seconds": percentile_nearest_rank(wall_values, 0.80),
            "low_sample_fallback": sample_size < 5,
        },
        refs,
        sample_size > 0,
        None if sample_size > 0 else "insufficient_reviewed_samples",
        generated_at,
    )


def _start_latency_vector(
    activity_id: UUID | None,
    session_id: UUID | None,
    sessions: list[TimingSession],
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    values = [
        session.start_latency_seconds
        for session in sessions
        if session.start_latency_seconds is not None
    ]
    return _latency_vector(
        "start_latency",
        "start_latency",
        values,
        activity_id,
        session_id,
        refs,
        generated_at,
    )


def _latency_total_vector(
    family: FeatureFamily,
    feature_prefix: str,
    activity_id: UUID | None,
    session_id: UUID | None,
    sessions: list[TimingSession],
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    values = [
        getattr(session, feature_prefix)
        for session in sessions
        if getattr(session, feature_prefix) is not None
    ]
    return _latency_vector(
        family,
        feature_prefix.removesuffix("_seconds"),
        values,
        activity_id,
        session_id,
        refs,
        generated_at,
    )


def _latency_vector(
    family: FeatureFamily,
    feature_prefix: str,
    values: list[int],
    activity_id: UUID | None,
    session_id: UUID | None,
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    sample_size = len(values)
    return _vector(
        activity_id,
        session_id,
        family,
        {
            "sample_size": sample_size,
            f"{feature_prefix}_p50_seconds": percentile_nearest_rank(values, 0.50),
            f"{feature_prefix}_p80_seconds": percentile_nearest_rank(values, 0.80),
            "low_sample_fallback": sample_size < 5,
        },
        refs,
        sample_size > 0,
        None if sample_size > 0 else "insufficient_reviewed_samples",
        generated_at,
    )


def _friction_vector(
    activity_id: UUID | None,
    session_id: UUID | None,
    sessions: list[TimingSession],
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    features: dict[str, object] = {
        "sample_size": len(sessions),
        "setup_seconds": sum(session.setup_seconds or 0 for session in sessions),
        "detour_seconds": sum(session.detour_seconds or 0 for session in sessions),
        "interruption_seconds": sum(session.interruption_seconds or 0 for session in sessions),
        "waiting_seconds": sum(session.waiting_seconds or 0 for session in sessions),
        "side_quest_seconds": sum(session.side_quest_seconds or 0 for session in sessions),
    }
    return _vector(
        activity_id,
        session_id,
        "friction",
        features,
        refs,
        len(sessions) > 0,
        None if sessions else "insufficient_reviewed_samples",
        generated_at,
    )


def _place_vector(
    activity_id: UUID | None,
    session_id: UUID | None,
    policy: ContextCapturePolicy,
    eligible_snapshot_count: int,
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    context_enabled = policy.location_enabled or policy.radio_context_enabled
    if not context_enabled:
        return _vector(
            activity_id,
            session_id,
            "place_inference",
            {
                "eligible_snapshot_count": 0,
                "location_enabled": policy.location_enabled,
                "radio_context_enabled": policy.radio_context_enabled,
            },
            refs,
            False,
            "context_disabled_by_policy",
            generated_at,
            privacy_class="sensitive",
        )
    return _vector(
        activity_id,
        session_id,
        "place_inference",
        {
            "eligible_snapshot_count": eligible_snapshot_count,
            "location_enabled": policy.location_enabled,
            "radio_context_enabled": policy.radio_context_enabled,
        },
        refs,
        eligible_snapshot_count > 0,
        None if eligible_snapshot_count > 0 else "no_eligible_context_snapshots",
        generated_at,
        privacy_class="sensitive",
    )


def _generic_vector(
    family: FeatureFamily,
    activity_id: UUID | None,
    session_id: UUID | None,
    sessions: list[TimingSession],
    refs: list[dict[str, object]],
    generated_at: datetime,
) -> TemporalFeatureVectorDraft:
    return _vector(
        activity_id,
        session_id,
        family,
        {"sample_size": len(sessions), "low_sample_fallback": len(sessions) < 5},
        refs,
        bool(sessions),
        None if sessions else "insufficient_reviewed_samples",
        generated_at,
    )


def _vector(
    activity_id: UUID | None,
    session_id: UUID | None,
    family: FeatureFamily,
    features: dict[str, object],
    refs: list[dict[str, object]],
    model_eligible: bool,
    exclusion_reason: str | None,
    generated_at: datetime,
    *,
    privacy_class: PrivacyClass = "normal",
) -> TemporalFeatureVectorDraft:
    return TemporalFeatureVectorDraft(
        activity_id=activity_id,
        session_id=session_id,
        snapshot_id=None,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        feature_family=family,
        features=features,
        source_entity_refs=refs,
        privacy_class=privacy_class,
        model_eligible=model_eligible,
        exclusion_reason=exclusion_reason,
        generated_at=generated_at,
    )


def _session_refs(sessions: list[TimingSession]) -> list[dict[str, object]]:
    return [
        {
            "entity_type": "timing_session",
            "entity_id": str(session.id),
            "model_inclusion": session.model_inclusion,
        }
        for session in sessions
    ]
