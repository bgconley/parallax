from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.context import (
    AnnotationStatus,
    CaptureContextSnapshot,
    ContextCapturePolicy,
    CreateAnnotationRequest,
    CreateCaptureContextSnapshotRequest,
    CreatePlaceRequest,
    DeviceContextObservation,
    DeviceContextObservationInput,
    GeospatialObservation,
    GeospatialObservationInput,
    RadioObservation,
    RadioObservationInput,
    ResolvePlaceCandidate,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    TemporalContextAnnotation,
    TimingReviewFlag,
    TimingReviewFlagStatus,
    UpdateContextCapturePolicyRequest,
    UpdatePlaceRequest,
    UserPlace,
)
from ..schemas.timing import AppendTimingEventRequest, TimingEvent
from .memory import InMemoryStore


class ContextRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_annotation(
        self,
        user_id: UUID,
        annotation_id: UUID,
    ) -> TemporalContextAnnotation | None:
        annotation = self._store.annotations.get(annotation_id)
        if annotation is None or annotation.user_id != user_id:
            return None
        return _resolve_annotation_snapshot_link(self._store, annotation)

    def create_annotation(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateAnnotationRequest,
    ) -> TemporalContextAnnotation:
        now = datetime.now(UTC)
        annotation = TemporalContextAnnotation(
            id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            checkpoint_run_id=request.checkpoint_run_id,
            input_mode=request.input_mode,
            raw_text=request.raw_text,
            redacted_text=None,
            transcript_confidence=None,
            audio_object_ref=request.audio_object_ref,
            timer_elapsed_seconds=request.timer_elapsed_seconds,
            timer_active_seconds=request.timer_active_seconds,
            occurred_at=request.occurred_at,
            privacy_class=request.privacy_class,
            status=_initial_annotation_status(request),
            client_mutation_id=request.mutation.client_mutation_id,
            client_device_id=request.mutation.client_device_id,
            idempotency_key=request.mutation.idempotency_key,
            capture_context_snapshot_id=request.capture_context_snapshot_id
            or self.snapshot_id_for_reference(user_id, request.capture_context_snapshot_ref),
            capture_context_snapshot_ref=request.capture_context_snapshot_ref,
            metadata={
                **request.metadata,
                "retrieval_document": {
                    "created": False,
                    "reason": "extraction_not_available",
                },
            },
        )
        self._store.annotations[annotation.id] = annotation
        self._store.session_annotations.setdefault(session_id, []).append(annotation.id)
        self._store.session_events.setdefault(session_id, []).append(
            _annotation_source_event(user_id, session_id, request, annotation, now)
        )
        return annotation

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy:
        existing = self._store.context_policies.get(user_id)
        if existing is not None:
            return existing
        policy = _default_context_capture_policy(user_id)
        self._store.context_policies[user_id] = policy
        return policy

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy:
        current = self.get_context_capture_policy(user_id)
        updates = {
            key: value
            for key, value in request.model_dump(exclude={"mutation"}).items()
            if value is not None
        }
        policy = current.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        self._store.context_policies[user_id] = policy
        return policy

    def create_capture_context_snapshot(
        self,
        user_id: UUID,
        session_id: UUID,
        request: CreateCaptureContextSnapshotRequest,
        *,
        geospatial_observations: list[GeospatialObservationInput],
        radio_observations: list[RadioObservationInput],
        device_context_observations: list[DeviceContextObservationInput],
    ) -> CaptureContextSnapshot:
        now = datetime.now(UTC)
        snapshot_id = uuid4()
        geospatial = [
            GeospatialObservation(
                **observation.model_dump(),
                id=uuid4(),
                user_id=user_id,
                snapshot_id=snapshot_id,
                created_at=now,
            )
            for observation in geospatial_observations
        ]
        radio = [
            RadioObservation(
                **observation.model_dump(),
                id=uuid4(),
                user_id=user_id,
                snapshot_id=snapshot_id,
                created_at=now,
            )
            for observation in radio_observations
        ]
        device = [
            DeviceContextObservation(
                **observation.model_dump(),
                id=uuid4(),
                user_id=user_id,
                snapshot_id=snapshot_id,
                created_at=now,
            )
            for observation in device_context_observations
        ]
        snapshot = CaptureContextSnapshot(
            id=snapshot_id,
            user_id=user_id,
            session_id=session_id,
            checkpoint_run_id=request.checkpoint_run_id,
            user_place_id=request.user_place_id,
            capture_method=request.capture_method,
            capture_trigger=request.capture_trigger,
            client_captured_at=request.client_captured_at,
            server_received_at=now,
            client_monotonic_millis=request.client_monotonic_millis,
            source_device_id=request.source_device_id,
            app_foreground_state=request.app_foreground_state,
            location_state=request.location_state,
            radio_state=request.radio_state,
            motion_state_available=request.motion_state_available,
            device_context_state=request.device_context_state,
            privacy_class=request.privacy_class,
            retention_policy=request.retention_policy,
            context_quality_score=request.context_quality_score,
            permission_summary=request.permission_summary,
            metadata=request.metadata,
            geospatial_observations=geospatial,
            radio_observations=radio,
            device_context_observations=device,
            inferred_places=[],
            client_mutation_id=request.mutation.client_mutation_id,
            client_device_id=request.mutation.client_device_id,
            idempotency_key=request.mutation.idempotency_key,
            created_at=now,
        )
        self._store.capture_snapshots[snapshot.id] = snapshot
        self._store.session_snapshots.setdefault(session_id, []).append(snapshot.id)
        self.resolve_pending_snapshot_references(user_id, snapshot)
        return snapshot

    def list_capture_context_snapshots(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[CaptureContextSnapshot]:
        snapshot_ids = self._store.session_snapshots.get(session_id, [])
        snapshots = [self._store.capture_snapshots[snapshot_id] for snapshot_id in snapshot_ids]
        return [snapshot for snapshot in snapshots if snapshot.user_id == user_id]

    def snapshot_id_for_reference(self, user_id: UUID, snapshot_ref: str | None) -> UUID | None:
        if snapshot_ref is None:
            return None
        for snapshot in self._store.capture_snapshots.values():
            if snapshot.user_id != user_id:
                continue
            if snapshot_ref in {snapshot.client_mutation_id, snapshot.idempotency_key}:
                return snapshot.id
        return None

    def resolve_pending_snapshot_references(
        self,
        user_id: UUID,
        snapshot: CaptureContextSnapshot,
    ) -> None:
        references = {snapshot.client_mutation_id, snapshot.idempotency_key}
        for session_id, events in self._store.session_events.items():
            self._store.session_events[session_id] = [
                event.model_copy(update={"capture_context_snapshot_id": snapshot.id})
                if event.user_id == user_id
                and event.capture_context_snapshot_id is None
                and event.capture_context_snapshot_ref in references
                else event
                for event in events
            ]
        for annotation_id, annotation in list(self._store.annotations.items()):
            if (
                annotation.user_id == user_id
                and annotation.capture_context_snapshot_id is None
                and annotation.capture_context_snapshot_ref in references
            ):
                self._store.annotations[annotation_id] = annotation.model_copy(
                    update={"capture_context_snapshot_id": snapshot.id}
                )

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace:
        now = datetime.now(UTC)
        place = UserPlace(
            id=uuid4(),
            user_id=user_id,
            display_name=request.display_name,
            category=request.category,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.radius_meters,
            source=request.source,
            privacy_class=request.privacy_class,
            confirmed_by_user=request.confirmed_by_user,
            is_sensitive=request.is_sensitive,
            aliases=request.aliases,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
        )
        self._store.places[place.id] = place
        return place

    def list_places(self, user_id: UUID) -> list[UserPlace]:
        return sorted(
            [place for place in self._store.places.values() if place.user_id == user_id],
            key=lambda place: place.created_at,
        )

    def get_place(self, user_id: UUID, place_id: UUID) -> UserPlace | None:
        place = self._store.places.get(place_id)
        if place is None or place.user_id != user_id:
            return None
        return place

    def update_place(
        self,
        user_id: UUID,
        place_id: UUID,
        request: UpdatePlaceRequest,
    ) -> UserPlace | None:
        place = self.get_place(user_id, place_id)
        if place is None:
            return None
        updates = {
            key: value
            for key, value in request.model_dump(exclude={"mutation"}).items()
            if value is not None
        }
        updated = place.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        self._store.places[place_id] = updated
        return updated

    def resolve_place(self, user_id: UUID, request: ResolvePlaceRequest) -> ResolvePlaceResponse:
        existing = (
            self.get_place(user_id, request.existing_place_id)
            if request.existing_place_id
            else None
        )
        if existing is None and request.candidate_label:
            existing = next(
                (
                    place
                    for place in self.list_places(user_id)
                    if place.display_name.casefold() == request.candidate_label.casefold()
                ),
                None,
            )
        if existing is not None:
            return ResolvePlaceResponse(
                candidates=[
                    ResolvePlaceCandidate(
                        place=existing,
                        candidate_label=existing.display_name,
                        candidate_category=existing.category,
                        confidence=1.0,
                        match_type="existing_place",
                        evidence={"reason": "user_confirmed_place_match"},
                    )
                ],
                recommended_place_id=existing.id,
                requires_confirmation=False,
            )
        return ResolvePlaceResponse(
            candidates=[
                ResolvePlaceCandidate(
                    place=None,
                    candidate_label=request.candidate_label,
                    candidate_category=request.candidate_category,
                    confidence=0.0,
                    match_type="manual_candidate" if request.candidate_label else "no_match",
                    evidence={"reason": "resolver_is_read_only"},
                )
            ],
            recommended_place_id=None,
            requires_confirmation=True,
        )

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]:
        flags = [
            flag
            for flag in self._store.review_flags.values()
            if flag.user_id == user_id and flag.session_id == session_id
        ]
        if status is not None:
            flags = [flag for flag in flags if flag.status == status]
        return sorted(flags, key=lambda flag: flag.created_at)

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        status: TimingReviewFlagStatus,
        resolution_note: str | None,
    ) -> TimingReviewFlag | None:
        flag = self._store.review_flags.get(flag_id)
        if flag is None or flag.user_id != user_id:
            return None
        resolved_at = datetime.now(UTC) if status in {"resolved", "dismissed"} else None
        updated = flag.model_copy(
            update={
                "status": status,
                "resolution_note": resolution_note,
                "resolved_at": resolved_at,
            }
        )
        self._store.review_flags[flag_id] = updated
        return updated


def _default_context_capture_policy(user_id: UUID) -> ContextCapturePolicy:
    now = datetime.now(UTC)
    return ContextCapturePolicy(
        id=uuid4(),
        user_id=user_id,
        location_enabled=False,
        precise_location_enabled=False,
        background_location_enabled=False,
        radio_context_enabled=False,
        motion_context_enabled=False,
        device_context_enabled=True,
        raw_location_retention_days=None,
        raw_radio_retention_days=None,
        default_location_retention_policy="derived_only",
        default_radio_retention_policy="derived_only",
        per_run_context_default=True,
        updated_at=now,
        created_at=now,
    )


def _initial_annotation_status(request: CreateAnnotationRequest) -> AnnotationStatus:
    if request.input_mode == "voice" and request.raw_text is None:
        return "transcription_pending"
    if request.raw_text is not None or request.input_mode in {"quick_chip", "review_note"}:
        return "extraction_pending"
    return "captured"


def _annotation_source_event(
    user_id: UUID,
    session_id: UUID,
    request: CreateAnnotationRequest,
    annotation: TemporalContextAnnotation,
    server_time: datetime,
) -> TimingEvent:
    event_request = AppendTimingEventRequest(
        mutation=request.mutation,
        event_type="annotation_captured",
        client_time=request.occurred_at,
        timer_elapsed_seconds=request.timer_elapsed_seconds,
        timer_active_seconds=request.timer_active_seconds,
        capture_context_snapshot_id=annotation.capture_context_snapshot_id,
        capture_context_snapshot_ref=request.capture_context_snapshot_ref,
        payload={"annotation_id": str(annotation.id), "input_mode": request.input_mode},
    )
    return TimingEvent(
        id=uuid4(),
        user_id=user_id,
        session_id=session_id,
        event_type=event_request.event_type,
        client_time=event_request.client_time,
        server_time=server_time,
        timer_elapsed_seconds=event_request.timer_elapsed_seconds,
        timer_active_seconds=event_request.timer_active_seconds,
        client_sequence=event_request.mutation.client_sequence,
        client_mutation_id=event_request.mutation.client_mutation_id,
        client_device_id=event_request.mutation.client_device_id,
        idempotency_key=event_request.mutation.idempotency_key,
        capture_context_snapshot_id=event_request.capture_context_snapshot_id,
        capture_context_snapshot_ref=event_request.capture_context_snapshot_ref,
        payload=event_request.payload,
    )


def _resolve_annotation_snapshot_link(
    store: InMemoryStore,
    annotation: TemporalContextAnnotation,
) -> TemporalContextAnnotation:
    if (
        annotation.capture_context_snapshot_id is not None
        or annotation.capture_context_snapshot_ref is None
    ):
        return annotation
    for snapshot in store.capture_snapshots.values():
        if (
            snapshot.user_id == annotation.user_id
            and annotation.capture_context_snapshot_ref
            in {snapshot.client_mutation_id, snapshot.idempotency_key}
        ):
            updated = annotation.model_copy(update={"capture_context_snapshot_id": snapshot.id})
            store.annotations[annotation.id] = updated
            return updated
    return annotation
