from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..domain.latency_observations import (
    StartLatencyObservationDraft,
    TransitionObservationDraft,
)
from ..schemas.timing import StartLatencyObservation, TimingSession, TransitionObservation
from .memory import InMemoryStore


def replace_latency_observations(
    store: InMemoryStore,
    user_id: UUID,
    session: TimingSession,
    start_latency: StartLatencyObservationDraft | None,
    transitions: list[TransitionObservationDraft],
) -> None:
    store.start_latency_observations = {
        observation_id: observation
        for observation_id, observation in store.start_latency_observations.items()
        if not (observation.user_id == user_id and observation.session_id == session.id)
    }
    store.transition_observations = {
        observation_id: observation
        for observation_id, observation in store.transition_observations.items()
        if not (
            observation.user_id == user_id
            and (
                observation.from_session_id == session.id
                or observation.to_session_id == session.id
            )
        )
    }
    now = datetime.now(UTC)
    if start_latency is not None:
        start_observation = StartLatencyObservation(
            id=uuid4(),
            user_id=user_id,
            activity_id=start_latency.activity_id,
            session_id=start_latency.session_id,
            intended_start_at=start_latency.intended_start_at,
            nudge_shown_at=None,
            actual_start_at=start_latency.actual_start_at,
            latency_seconds=start_latency.latency_seconds,
            reason_category=start_latency.reason_category,
            evidence_annotation_id=start_latency.evidence_annotation_id,
            created_at=now,
        )
        store.start_latency_observations[start_observation.id] = start_observation
    for transition in transitions:
        transition_observation = TransitionObservation(
            id=uuid4(),
            user_id=user_id,
            from_session_id=transition.from_session_id,
            to_session_id=transition.to_session_id,
            from_checkpoint_run_id=transition.from_checkpoint_run_id,
            to_checkpoint_run_id=transition.to_checkpoint_run_id,
            started_at=transition.started_at,
            ended_at=transition.ended_at,
            transition_seconds=transition.transition_seconds,
            reason_category=transition.reason_category,
            metadata=transition.metadata,
            created_at=now,
        )
        store.transition_observations[transition_observation.id] = transition_observation
