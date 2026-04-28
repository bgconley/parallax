from __future__ import annotations

from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from uuid import UUID, uuid4

from ..schemas.context import (
    CaptureContextSnapshot,
    InferredPlaceObservation,
    ResolvePlaceCandidate,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    UserPlace,
)
from .memory import InMemoryStore


def infer_places_for_snapshot(
    store: InMemoryStore,
    snapshot: CaptureContextSnapshot,
) -> list[InferredPlaceObservation]:
    if not snapshot.geospatial_observations:
        return []
    observation = next(
        (
            item
            for item in snapshot.geospatial_observations
            if item.latitude is not None and item.longitude is not None and not item.is_stale
        ),
        None,
    )
    if observation is None:
        return []
    observation_latitude = observation.latitude
    observation_longitude = observation.longitude
    if observation_latitude is None or observation_longitude is None:
        return []
    best: tuple[UserPlace, float] | None = None
    for place in store.places.values():
        place_latitude = place.latitude
        place_longitude = place.longitude
        place_radius = place.radius_meters
        if (
            place.user_id != snapshot.user_id
            or place_latitude is None
            or place_longitude is None
            or place_radius is None
        ):
            continue
        distance = _meters_between(
            observation_latitude,
            observation_longitude,
            place_latitude,
            place_longitude,
        )
        if distance <= max(place_radius, 25) and (best is None or distance < best[1]):
            best = (place, distance)
    if best is None:
        return []

    place, distance = best
    now = datetime.now(UTC)
    sensitive_label_detected = place.is_sensitive or place.privacy_class in {"sensitive", "private"}
    inferred = InferredPlaceObservation(
        id=uuid4(),
        user_id=snapshot.user_id,
        snapshot_id=snapshot.id,
        user_place_id=place.id,
        candidate_label=None if sensitive_label_detected else place.display_name,
        candidate_category=place.category,
        confidence=max(0.5, min(0.95, 1 - (distance / max(place.radius_meters or 1, 1)))),
        confirmation_state="needs_confirmation",
        evidence={
            "source": "geospatial_distance",
            "distance_meters": round(distance, 2),
            "place_radius_meters": place.radius_meters,
        },
        sensitive_label_detected=sensitive_label_detected,
        confirmed_at=None,
        created_at=now,
    )
    store.inferred_place_observations[inferred.id] = inferred
    return [inferred]


def inferred_candidates_for_snapshot(
    store: InMemoryStore,
    user_id: UUID,
    request: ResolvePlaceRequest,
) -> ResolvePlaceResponse | None:
    if request.snapshot_id is None:
        return None
    inferred = [
        item
        for item in store.inferred_place_observations.values()
        if item.user_id == user_id and item.snapshot_id == request.snapshot_id
    ]
    if not inferred:
        return None
    candidates = []
    recommended_place_id: UUID | None = None
    for item in sorted(inferred, key=lambda candidate: candidate.created_at):
        place = store.places.get(item.user_place_id) if item.user_place_id is not None else None
        if recommended_place_id is None:
            recommended_place_id = item.user_place_id
        candidates.append(
            ResolvePlaceCandidate(
                place=place if place is not None and not item.sensitive_label_detected else None,
                candidate_label=item.candidate_label,
                candidate_category=item.candidate_category,
                confidence=item.confidence,
                match_type="inferred_candidate",
                evidence=item.evidence,
            )
        )
    return ResolvePlaceResponse(
        candidates=candidates,
        recommended_place_id=recommended_place_id,
        requires_confirmation=True,
    )


def _meters_between(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    earth_radius_meters = 6_371_000
    d_lat = radians(lat_b - lat_a)
    d_lon = radians(lon_b - lon_a)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_meters * asin(sqrt(a))
