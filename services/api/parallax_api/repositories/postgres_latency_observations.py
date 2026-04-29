from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..domain.latency_observations import (
    StartLatencyObservationDraft,
    TransitionObservationDraft,
)
from ..schemas.timing import TimingSession


def replace_latency_observations(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    *,
    user_id: UUID,
    session: TimingSession,
    start_latency: StartLatencyObservationDraft | None,
    transitions: list[TransitionObservationDraft],
) -> None:
    cursor.execute(
        "delete from start_latency_observation where user_id = %s and session_id = %s",
        (user_id, session.id),
    )
    cursor.execute(
        """
        delete from transition_observation
        where user_id = %s and (from_session_id = %s or to_session_id = %s)
        """,
        (user_id, session.id, session.id),
    )
    if start_latency is not None:
        cursor.execute(
            """
            insert into start_latency_observation (
              user_id, activity_id, session_id, intended_start_at, actual_start_at,
              latency_seconds, reason_category, evidence_annotation_id
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                start_latency.activity_id,
                start_latency.session_id,
                start_latency.intended_start_at,
                start_latency.actual_start_at,
                start_latency.latency_seconds,
                start_latency.reason_category,
                start_latency.evidence_annotation_id,
            ),
        )
    for transition in transitions:
        cursor.execute(
            """
            insert into transition_observation (
              user_id, from_session_id, to_session_id, from_checkpoint_run_id,
              to_checkpoint_run_id, started_at, ended_at, transition_seconds,
              reason_category, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                transition.from_session_id,
                transition.to_session_id,
                transition.from_checkpoint_run_id,
                transition.to_checkpoint_run_id,
                transition.started_at,
                transition.ended_at,
                transition.transition_seconds,
                transition.reason_category,
                Jsonb(transition.metadata),
            ),
        )
