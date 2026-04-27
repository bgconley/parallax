from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.sync import SyncPushRequest, SyncPushResponse
from ..services.sync_service import SyncService

router = APIRouter(prefix="/v1/sync", tags=["sync"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.post("/push", response_model=SyncPushResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_push(
    payload: SyncPushRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> SyncPushResponse:
    return SyncService(uow_factory).push(auth.user_id, payload)
