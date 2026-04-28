from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.activity_repository import DuplicateActivityError
from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity import (
    Activity,
    CreateActivityRequest,
    ResolveActivityRequest,
    ResolveActivityResponse,
)
from .mutations import MutationReplayService


class ActivityService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_activity(self, user_id: UUID, request: CreateActivityRequest) -> Activity:
        with self._uow_factory() as uow:
            return create_activity_in_uow(uow, user_id, request)

    def list_activities(self, user_id: UUID, query: str | None, limit: int) -> list[Activity]:
        with self._uow_factory() as uow:
            return uow.activities.list_activities(user_id, query=query, limit=limit)

    def get_activity(self, user_id: UUID, activity_id: UUID) -> Activity:
        with self._uow_factory() as uow:
            activity = uow.activities.get(user_id, activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail="activity not found")
        return activity

    def resolve_activity(
        self,
        user_id: UUID,
        request: ResolveActivityRequest,
    ) -> ResolveActivityResponse:
        with self._uow_factory() as uow:
            candidates = uow.activities.resolve(user_id, request.query, request.limit)
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


def create_activity_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: CreateActivityRequest,
) -> Activity:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, Activity]:
        try:
            activity = uow.activities.create(user_id, request)
        except DuplicateActivityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return activity.id, activity

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_activity",
        entity_type="activity",
        result_type=Activity,
        apply=apply,
    )
