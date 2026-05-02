from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity_metadata import (
    CreatePreflightCheckRequest,
    DecidePreflightCheckRequest,
    PreflightCheck,
    ResourceDependency,
)
from .mutations import MutationReplayService


class PreflightLearningService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_preflight_checks(user_id, activity_id)

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck:
        with self._uow_factory() as uow:
            return create_preflight_check_in_uow(uow, user_id, activity_id, request)

    def decide_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        check_id: UUID,
        request: DecidePreflightCheckRequest,
    ) -> PreflightCheck:
        with self._uow_factory() as uow:
            return decide_preflight_check_in_uow(uow, user_id, activity_id, check_id, request)

    def list_resource_dependencies(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ResourceDependency]:
        with self._uow_factory() as uow:
            _require_activity(uow, user_id, activity_id)
            return uow.activities.list_resource_dependencies(user_id, activity_id)


def create_preflight_check_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    request: CreatePreflightCheckRequest,
) -> PreflightCheck:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, PreflightCheck]:
        check = uow.activities.create_preflight_check(user_id, activity_id, request)
        return check.id, check

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_preflight_check",
        entity_type="preflight_check",
        result_type=PreflightCheck,
        apply=apply,
    )


def decide_preflight_check_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    activity_id: UUID,
    check_id: UUID,
    request: DecidePreflightCheckRequest,
) -> PreflightCheck:
    _require_activity(uow, user_id, activity_id)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, PreflightCheck]:
        check = uow.activities.decide_preflight_check(
            user_id,
            activity_id,
            check_id,
            request.decision,
            snoozed_until=request.snoozed_until,
            reason=request.reason,
        )
        if check is None:
            raise HTTPException(status_code=404, detail="preflight check not found")
        return check.id, check

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="decide_preflight_check",
        entity_type="preflight_check",
        result_type=PreflightCheck,
        apply=apply,
    )


def _require_activity(uow: UnitOfWork, user_id: UUID, activity_id: UUID) -> None:
    if uow.activities.get(user_id, activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
