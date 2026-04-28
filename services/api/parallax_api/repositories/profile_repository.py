from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ..domain.activity_stats import compute_activity_stats
from ..schemas.profile import ActivityProfile
from ..schemas.timing import TimingSession
from .memory import InMemoryStore
from .timing_repository import TimingRepository


class ProfileRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def recompute_activity_stats(self, user_id: UUID, activity_id: UUID) -> None:
        sessions = self._reviewed_sessions(user_id, activity_id)
        computation = compute_activity_stats(sessions)
        if computation.stats is None:
            self._store.activity_stats.pop(activity_id, None)
        else:
            self._store.activity_stats[activity_id] = computation.stats

    def get_activity_profile(self, user_id: UUID, activity_id: UUID) -> ActivityProfile | None:
        activity = self._store.activities.get(activity_id)
        if activity is None or activity.user_id != user_id:
            return None
        sessions = self._reviewed_sessions(user_id, activity_id)
        computation = compute_activity_stats(sessions)
        return ActivityProfile(
            activity=activity,
            latest_stats=self._store.activity_stats.get(activity_id) or computation.stats,
            preflight_checks=[],
            recent_sessions=sessions[:5],
            limitations=computation.limitations,
        )

    def _reviewed_sessions(self, user_id: UUID, activity_id: UUID) -> list[TimingSession]:
        timing = TimingRepository(self._store)
        sessions = [
            timing.get_session(user_id, session.id)
            for session in self._store.sessions.values()
            if session.user_id == user_id
            and session.activity_id == activity_id
            and session.status == "reviewed"
        ]
        return sorted(
            (session for session in sessions if session is not None),
            key=lambda session: session.completed_at
            or session.started_at
            or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
