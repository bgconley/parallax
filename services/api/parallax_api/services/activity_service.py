from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.activity_repository import ActivityRepository, DuplicateActivityError
from ..repositories.memory import InMemoryStore
from ..schemas.activity import (
    Activity,
    CreateActivityRequest,
    ResolveActivityRequest,
    ResolveActivityResponse,
)
from .mutations import MutationReplayService


class ActivityService:
    def __init__(self, store: InMemoryStore) -> None:
        self._activities = ActivityRepository(store)
        self._mutations = MutationReplayService(store)

    def create_activity(self, user_id: UUID, request: CreateActivityRequest) -> Activity:
        def apply() -> tuple[UUID, Activity]:
            try:
                activity = self._activities.create(user_id, request)
            except DuplicateActivityError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return activity.id, activity

        return self._mutations.replay_or_apply(
            user_id=user_id,
            mutation=request.mutation,
            mutation_type="create_activity",
            entity_type="activity",
            apply=apply,
        )

    def list_activities(self, user_id: UUID, query: str | None, limit: int) -> list[Activity]:
        return self._activities.list_activities(user_id, query=query, limit=limit)

    def get_activity(self, user_id: UUID, activity_id: UUID) -> Activity:
        activity = self._activities.get(user_id, activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail="activity not found")
        return activity

    def resolve_activity(
        self,
        user_id: UUID,
        request: ResolveActivityRequest,
    ) -> ResolveActivityResponse:
        candidates = self._activities.resolve(user_id, request.query, request.limit)
        if not candidates:
            return ResolveActivityResponse(
                candidates=[],
                recommended_activity_id=None,
                requires_confirmation=True,
            )

        best_candidate = candidates[0]
        recommended = best_candidate.activity.id if best_candidate.activity else None
        return ResolveActivityResponse(
            candidates=candidates,
            recommended_activity_id=recommended,
            requires_confirmation=recommended is None or best_candidate.confidence < 0.99,
        )
