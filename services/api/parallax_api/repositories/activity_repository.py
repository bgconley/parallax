from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from .memory import InMemoryStore


class DuplicateActivityError(ValueError):
    pass


class ActivityRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity:
        canonical_key = normalize_activity_key(request.display_name)
        if (user_id, canonical_key) in self._store.activity_keys:
            raise DuplicateActivityError(f"activity already exists: {canonical_key}")

        now = datetime.now(UTC)
        activity = Activity(
            id=uuid4(),
            user_id=user_id,
            display_name=request.display_name,
            canonical_key=canonical_key,
            description=request.description,
            status="active",
            merged_into_activity_id=None,
            default_timing_mode=request.default_timing_mode,
            privacy_class=request.privacy_class,
            created_at=now,
            updated_at=now,
        )
        self._store.activities[activity.id] = activity
        self._store.activity_keys[(user_id, canonical_key)] = activity.id
        return activity

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]:
        activities = [
            activity
            for activity in self._store.activities.values()
            if activity.user_id == user_id
        ]
        if query:
            normalized_query = query.casefold()
            activities = [a for a in activities if normalized_query in a.display_name.casefold()]
        return sorted(activities, key=lambda activity: activity.created_at)[:limit]

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None:
        activity = self._store.activities.get(activity_id)
        if activity is None or activity.user_id != user_id:
            return None
        return activity

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]:
        canonical_key = normalize_activity_key(query)
        activity_id = self._store.activity_keys.get((user_id, canonical_key))
        if activity_id:
            activity = self._store.activities[activity_id]
            return [
                ResolveActivityCandidate(
                    activity=activity,
                    display_name=activity.display_name,
                    confidence=1.0,
                    match_type="canonical",
                    evidence={"canonical_key": canonical_key},
                )
            ][:limit]

        return [
            ResolveActivityCandidate(
                activity=None,
                display_name=query,
                confidence=0.0,
                match_type="no_match",
                evidence={"reason": "no matching activity"},
            )
        ]


def normalize_activity_key(display_name: str) -> str:
    lowered = display_name.strip().casefold()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return collapsed or "activity"
