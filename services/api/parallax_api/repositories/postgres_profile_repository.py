from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..domain.activity_stats import compute_activity_stats
from ..schemas.activity import Activity
from ..schemas.profile import ActivityProfile, ActivityProfileStats
from ..schemas.timing import TimingSession
from .postgres_timing_repository import PostgresTimingRepository

_LOAD_ACTIVITY_SQL = """
select id, user_id, display_name, canonical_key, description, status,
  merged_into_activity_id, default_timing_mode, privacy_class, created_at, updated_at
from activity
where user_id = %s and id = %s
"""

_LOAD_LATEST_STATS_SQL = """
select useful_run_count as sample_size, confidence, active_p50_seconds,
  active_p80_seconds, wall_p50_seconds, wall_p80_seconds,
  start_latency_p80_seconds, top_friction
from activity_stats_snapshot
where user_id = %s and activity_id = %s and work_mode = 'unknown' and actor_mode = 'unknown'
order by computed_at desc
limit 1
"""

_INSERT_STATS_SQL = """
insert into activity_stats_snapshot (
  user_id, activity_id, useful_run_count, active_p50_seconds, active_p80_seconds,
  wall_p50_seconds, wall_p80_seconds, start_latency_p80_seconds, top_friction,
  confidence
)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


class PostgresProfileRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def recompute_activity_stats(self, user_id: UUID, activity_id: UUID) -> None:
        computation = compute_activity_stats(self._reviewed_sessions(user_id, activity_id))
        if computation.stats is None:
            return
        stats = computation.stats
        with self._connection.cursor() as cursor:
            cursor.execute(
                _INSERT_STATS_SQL,
                (
                    user_id,
                    activity_id,
                    stats.sample_size,
                    stats.active_p50_seconds,
                    stats.active_p80_seconds,
                    stats.wall_p50_seconds,
                    stats.wall_p80_seconds,
                    stats.start_latency_p80_seconds,
                    Jsonb(stats.top_friction),
                    stats.confidence,
                ),
            )

    def get_activity_profile(self, user_id: UUID, activity_id: UUID) -> ActivityProfile | None:
        activity = self._load_activity(user_id, activity_id)
        if activity is None:
            return None
        sessions = self._reviewed_sessions(user_id, activity_id, limit=5)
        computation = compute_activity_stats(self._reviewed_sessions(user_id, activity_id))
        latest_stats = (
            self._load_latest_stats(user_id, activity_id)
            if computation.stats is not None
            else None
        )
        return ActivityProfile(
            activity=activity,
            latest_stats=latest_stats or computation.stats,
            preflight_checks=[],
            recent_sessions=sessions,
            limitations=computation.limitations,
        )

    def _load_activity(self, user_id: UUID, activity_id: UUID) -> Activity | None:
        with self._connection.cursor() as cursor:
            cursor.execute(_LOAD_ACTIVITY_SQL, (user_id, activity_id))
            row = cursor.fetchone()
        return Activity.model_validate(dict(row)) if row is not None else None

    def _load_latest_stats(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> ActivityProfileStats | None:
        with self._connection.cursor() as cursor:
            cursor.execute(_LOAD_LATEST_STATS_SQL, (user_id, activity_id))
            row = cursor.fetchone()
        return _stats_from_row(row) if row is not None else None

    def _reviewed_sessions(
        self,
        user_id: UUID,
        activity_id: UUID,
        limit: int | None = None,
    ) -> list[TimingSession]:
        query = """
            select id
            from timing_session
            where user_id = %s and activity_id = %s and status = 'reviewed'
            order by completed_at desc nulls last, updated_at desc, id
        """
        params: tuple[object, ...]
        if limit is None:
            params = (user_id, activity_id)
        else:
            query = f"{query}\nlimit %s"
            params = (user_id, activity_id, limit)
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        timing = PostgresTimingRepository(self._connection)
        sessions: list[TimingSession] = []
        for row in rows:
            session = timing.get_session(user_id, row["id"])
            if session is not None:
                sessions.append(session)
        return sessions


def _stats_from_row(row: Mapping[str, Any]) -> ActivityProfileStats:
    return ActivityProfileStats.model_validate(dict(row))
