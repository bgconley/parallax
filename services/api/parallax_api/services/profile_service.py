from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.profile import ActivityProfile


class ProfileService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def get_activity_profile(self, user_id: UUID, activity_id: UUID) -> ActivityProfile:
        with self._uow_factory() as uow:
            profile = uow.profiles.get_activity_profile(user_id, activity_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="activity not found")
        return profile
