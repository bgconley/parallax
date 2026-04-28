from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.context import (
    CaptureContextSnapshot,
    ContextCapturePolicy,
    CreateAnnotationRequest,
    CreateCaptureContextSnapshotRequest,
    CreatePlaceRequest,
    DeviceContextObservationInput,
    GeospatialObservationInput,
    RadioObservationInput,
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
from .mutations import MutationReplayService

_SENSITIVE_PLACE_CATEGORIES = {"home", "work", "medical", "school", "religious", "client_site"}


class ContextService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_annotation(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
    ) -> TemporalContextAnnotation:
        with self._uow_factory() as uow:
            return create_annotation_in_uow(uow, user_id, session_id, request)

    def get_annotation(self, user_id: UUID, annotation_id: UUID) -> TemporalContextAnnotation:
        with self._uow_factory() as uow:
            annotation = uow.contexts.get_annotation(user_id, annotation_id)
        if annotation is None:
            raise HTTPException(status_code=404, detail="context annotation not found")
        return annotation

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy:
        with self._uow_factory() as uow:
            return uow.contexts.get_context_capture_policy(user_id)

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy:
        with self._uow_factory() as uow:
            return update_context_capture_policy_in_uow(uow, user_id, request)

    def create_capture_context_snapshot(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateCaptureContextSnapshotRequest,
    ) -> CaptureContextSnapshot:
        with self._uow_factory() as uow:
            return create_capture_context_snapshot_in_uow(uow, user_id, session_id, request)

    def list_capture_context_snapshots(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[CaptureContextSnapshot]:
        with self._uow_factory() as uow:
            if uow.timing.get_session(user_id, session_id) is None:
                raise HTTPException(status_code=404, detail="timing session not found")
            return uow.contexts.list_capture_context_snapshots(user_id, session_id)

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace:
        with self._uow_factory() as uow:
            return create_place_in_uow(uow, user_id, request)

    def list_places(self, user_id: UUID) -> list[UserPlace]:
        with self._uow_factory() as uow:
            return uow.contexts.list_places(user_id)

    def resolve_place(self, user_id: UUID, request: ResolvePlaceRequest) -> ResolvePlaceResponse:
        with self._uow_factory() as uow:
            return uow.contexts.resolve_place(user_id, request)

    def update_place(
        self,
        user_id: UUID,
        place_id: UUID,
        request: UpdatePlaceRequest,
    ) -> UserPlace:
        with self._uow_factory() as uow:
            return update_place_in_uow(uow, user_id, place_id, request)

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]:
        with self._uow_factory() as uow:
            if uow.timing.get_session(user_id, session_id) is None:
                raise HTTPException(status_code=404, detail="timing session not found")
            return uow.contexts.list_review_flags(user_id, session_id, status)

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        request: UpdateTimingReviewFlagRequest,
    ) -> TimingReviewFlag:
        with self._uow_factory() as uow:
            return update_review_flag_in_uow(uow, user_id, flag_id, request)


def create_annotation_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: CreateAnnotationRequest,
) -> TemporalContextAnnotation:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TemporalContextAnnotation]:
        annotation = uow.contexts.create_annotation(user_id, session_id, request)
        return annotation.id, annotation

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_context_annotation",
        entity_type="temporal_context_annotation",
        result_type=TemporalContextAnnotation,
        apply=apply,
    )


def update_context_capture_policy_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: UpdateContextCapturePolicyRequest,
) -> ContextCapturePolicy:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, ContextCapturePolicy]:
        policy = uow.contexts.update_context_capture_policy(user_id, request)
        return policy.id, policy

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="update_context_capture_policy",
        entity_type="context_capture_policy",
        result_type=ContextCapturePolicy,
        apply=apply,
    )


def create_capture_context_snapshot_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    session_id: UUID,
    request: CreateCaptureContextSnapshotRequest,
) -> CaptureContextSnapshot:
    if uow.timing.get_session(user_id, session_id) is None:
        raise HTTPException(status_code=404, detail="timing session not found")
    if (
        request.user_place_id is not None
        and uow.contexts.get_place(user_id, request.user_place_id) is None
    ):
        raise HTTPException(status_code=404, detail="place not found")
    policy = uow.contexts.get_context_capture_policy(user_id)
    filtered_request, geospatial, radio, device = _apply_capture_policy(request, policy)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, CaptureContextSnapshot]:
        snapshot = uow.contexts.create_capture_context_snapshot(
            user_id,
            session_id,
            filtered_request,
            geospatial_observations=geospatial,
            radio_observations=radio,
            device_context_observations=device,
        )
        return snapshot.id, snapshot

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_capture_context_snapshot",
        entity_type="capture_context_snapshot",
        result_type=CaptureContextSnapshot,
        apply=apply,
    )


def create_place_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: CreatePlaceRequest,
) -> UserPlace:
    _validate_sensitive_place_confirmation(request.category, request.confirmed_by_user)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, UserPlace]:
        place = uow.contexts.create_place(user_id, request)
        return place.id, place

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_user_place",
        entity_type="user_place",
        result_type=UserPlace,
        apply=apply,
    )


def update_place_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    place_id: UUID,
    request: UpdatePlaceRequest,
) -> UserPlace:
    if request.category is not None:
        _validate_sensitive_place_confirmation(
            request.category,
            request.confirmed_by_user is True,
        )
    if uow.contexts.get_place(user_id, place_id) is None:
        raise HTTPException(status_code=404, detail="place not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, UserPlace]:
        place = uow.contexts.update_place(user_id, place_id, request)
        if place is None:
            raise HTTPException(status_code=404, detail="place not found")
        return place.id, place

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="update_user_place",
        entity_type="user_place",
        result_type=UserPlace,
        apply=apply,
    )


def update_review_flag_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    flag_id: UUID,
    request: UpdateTimingReviewFlagRequest,
) -> TimingReviewFlag:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TimingReviewFlag]:
        flag = uow.contexts.update_review_flag(
            user_id,
            flag_id,
            request.status,
            request.resolution_note,
        )
        if flag is None:
            raise HTTPException(status_code=404, detail="timing review flag not found")
        return flag.id, flag

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="update_timing_review_flag",
        entity_type="timing_review_flag",
        result_type=TimingReviewFlag,
        apply=apply,
    )


def _apply_capture_policy(
    request: CreateCaptureContextSnapshotRequest,
    policy: ContextCapturePolicy,
) -> tuple[
    CreateCaptureContextSnapshotRequest,
    list[GeospatialObservationInput],
    list[RadioObservationInput],
    list[DeviceContextObservationInput],
]:
    location_allowed = policy.per_run_context_default and policy.location_enabled
    radio_allowed = policy.per_run_context_default and policy.radio_context_enabled
    motion_allowed = policy.per_run_context_default and policy.motion_context_enabled
    device_allowed = policy.per_run_context_default and policy.device_context_enabled

    geospatial = _filter_geospatial_observations(request, policy, location_allowed)
    radio = _filter_radio_observations(request, policy, radio_allowed)
    device = request.device_context_observations if device_allowed else []

    return (
        request.model_copy(
            update={
                "location_state": request.location_state
                if location_allowed or request.location_state != "available"
                else "disabled_by_system",
                "radio_state": request.radio_state
                if radio_allowed or request.radio_state != "available"
                else "disabled_by_system",
                "motion_state_available": request.motion_state_available
                if motion_allowed or request.motion_state_available != "available"
                else "disabled_by_system",
                "device_context_state": request.device_context_state
                if device_allowed or request.device_context_state != "available"
                else "disabled_by_system",
                "geospatial_observations": geospatial,
                "radio_observations": radio,
                "device_context_observations": device,
            }
        ),
        geospatial,
        radio,
        device,
    )


def _filter_geospatial_observations(
    request: CreateCaptureContextSnapshotRequest,
    policy: ContextCapturePolicy,
    location_allowed: bool,
) -> list[GeospatialObservationInput]:
    if not location_allowed or request.location_state != "available":
        return []
    allow_raw_coordinates = policy.default_location_retention_policy in {
        "short_ttl_raw",
        "store_with_consent",
    }
    filtered: list[GeospatialObservationInput] = []
    for observation in request.geospatial_observations:
        if observation.is_precise and not policy.precise_location_enabled:
            filtered.append(
                observation.model_copy(
                    update={"latitude": None, "longitude": None, "is_precise": False}
                )
            )
        elif allow_raw_coordinates:
            filtered.append(observation)
        else:
            filtered.append(observation.model_copy(update={"latitude": None, "longitude": None}))
    return filtered


def _filter_radio_observations(
    request: CreateCaptureContextSnapshotRequest,
    policy: ContextCapturePolicy,
    radio_allowed: bool,
) -> list[RadioObservationInput]:
    if not radio_allowed or request.radio_state != "available":
        return []
    allow_raw_radio = policy.default_radio_retention_policy in {
        "short_ttl_raw",
        "store_with_consent",
    }
    return [
        observation.model_copy(
            update={
                "raw_encrypted_object_ref": observation.raw_encrypted_object_ref
                if allow_raw_radio
                else None,
                "redacted_display_label": observation.redacted_display_label
                if allow_raw_radio
                else None,
            }
        )
        for observation in request.radio_observations
    ]


def _validate_sensitive_place_confirmation(category: str, confirmed_by_user: bool) -> None:
    if category in _SENSITIVE_PLACE_CATEGORIES and not confirmed_by_user:
        raise HTTPException(
            status_code=400,
            detail="sensitive place categories require user confirmation",
        )
