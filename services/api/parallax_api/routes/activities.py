from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.memory import InMemoryStore
from ..schemas.activity import (
    Activity,
    CreateActivityRequest,
    ResolveActivityRequest,
    ResolveActivityResponse,
)
from ..services.activity_service import ActivityService

router = APIRouter(prefix="/v1/activities", tags=["activities"])


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


AUTH_CONTEXT = Depends(get_auth_context)
STORE = Depends(get_store)


@router.post("", response_model=Activity, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: CreateActivityRequest,
    auth: AuthContext = AUTH_CONTEXT,
    store: InMemoryStore = STORE,
) -> Activity:
    return ActivityService(store).create_activity(auth.user_id, payload)


@router.get("", response_model=list[Activity])
def list_activities(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    auth: AuthContext = AUTH_CONTEXT,
    store: InMemoryStore = STORE,
) -> list[Activity]:
    return ActivityService(store).list_activities(auth.user_id, q, limit)


@router.post("/resolve", response_model=ResolveActivityResponse)
def resolve_activity(
    payload: ResolveActivityRequest,
    auth: AuthContext = AUTH_CONTEXT,
    store: InMemoryStore = STORE,
) -> ResolveActivityResponse:
    return ActivityService(store).resolve_activity(auth.user_id, payload)


@router.get("/{activity_id}", response_model=Activity)
def get_activity(
    activity_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    store: InMemoryStore = STORE,
) -> Activity:
    return ActivityService(store).get_activity(auth.user_id, activity_id)
