from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
from ..schemas.context import (
    CaptureContextSnapshot,
    ContextCapturePolicy,
    CreateAnnotationRequest,
    CreateCaptureContextSnapshotRequest,
    CreatePlaceRequest,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    TemporalContextAnnotation,
    TimingReviewFlag,
    TimingReviewFlagStatus,
    UpdateContextCapturePolicyRequest,
    UpdatePlaceRequest,
    UpdateTimingReviewFlagRequest,
    UserPlace,
)
from ..services.context_service import ContextService

router = APIRouter(tags=["context"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.post(
    "/v1/timing/sessions/{session_id}/annotations",
    response_model=TemporalContextAnnotation,
    status_code=status.HTTP_201_CREATED,
)
def create_context_annotation(
    session_id: UUID,
    payload: CreateAnnotationRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TemporalContextAnnotation:
    return ContextService(uow_factory).create_annotation(auth.user_id, session_id, payload)


@router.get("/v1/timing/annotations/{annotation_id}", response_model=TemporalContextAnnotation)
def get_context_annotation(
    annotation_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TemporalContextAnnotation:
    return ContextService(uow_factory).get_annotation(auth.user_id, annotation_id)


@router.get("/v1/privacy/context-capture-policy", response_model=ContextCapturePolicy)
def get_context_capture_policy(
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ContextCapturePolicy:
    return ContextService(uow_factory).get_context_capture_policy(auth.user_id)


@router.patch("/v1/privacy/context-capture-policy", response_model=ContextCapturePolicy)
def update_context_capture_policy(
    payload: UpdateContextCapturePolicyRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ContextCapturePolicy:
    return ContextService(uow_factory).update_context_capture_policy(auth.user_id, payload)


@router.post(
    "/v1/timing/sessions/{session_id}/capture-context",
    response_model=CaptureContextSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def create_capture_context_snapshot(
    session_id: UUID,
    payload: CreateCaptureContextSnapshotRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> CaptureContextSnapshot:
    return ContextService(uow_factory).create_capture_context_snapshot(
        auth.user_id, session_id, payload
    )


@router.get(
    "/v1/timing/sessions/{session_id}/capture-context",
    response_model=list[CaptureContextSnapshot],
)
def list_capture_context_snapshots(
    session_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[CaptureContextSnapshot]:
    return ContextService(uow_factory).list_capture_context_snapshots(auth.user_id, session_id)


@router.get(
    "/v1/timing/sessions/{session_id}/review-flags",
    response_model=list[TimingReviewFlag],
)
def list_timing_review_flags(
    session_id: UUID,
    status: TimingReviewFlagStatus | None = None,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[TimingReviewFlag]:
    return ContextService(uow_factory).list_review_flags(auth.user_id, session_id, status)


@router.patch("/v1/timing/review-flags/{flag_id}", response_model=TimingReviewFlag)
def update_timing_review_flag(
    flag_id: UUID,
    payload: UpdateTimingReviewFlagRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TimingReviewFlag:
    return ContextService(uow_factory).update_review_flag(auth.user_id, flag_id, payload)


@router.post("/v1/places", response_model=UserPlace, status_code=status.HTTP_201_CREATED)
def create_user_place(
    payload: CreatePlaceRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> UserPlace:
    return ContextService(uow_factory).create_place(auth.user_id, payload)


@router.get("/v1/places", response_model=list[UserPlace])
def list_user_places(
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> list[UserPlace]:
    return ContextService(uow_factory).list_places(auth.user_id)


@router.post("/v1/places/resolve", response_model=ResolvePlaceResponse)
def resolve_user_place(
    payload: ResolvePlaceRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> ResolvePlaceResponse:
    return ContextService(uow_factory).resolve_place(auth.user_id, payload)


@router.patch("/v1/places/{place_id}", response_model=UserPlace)
def update_user_place(
    place_id: UUID,
    payload: UpdatePlaceRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> UserPlace:
    return ContextService(uow_factory).update_place(auth.user_id, place_id, payload)
