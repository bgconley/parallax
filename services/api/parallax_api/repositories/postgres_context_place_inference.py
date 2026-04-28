from __future__ import annotations

from collections.abc import Mapping
from math import asin, cos, radians, sin, sqrt
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.context import (
    CaptureContextSnapshot,
    InferredPlaceObservation,
    ResolvePlaceCandidate,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    UserPlace,
)
from .postgres_context_common import place_from_row


class PostgresContextPlaceInferenceRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def infer_for_snapshot(
        self,
        user_id: UUID,
        snapshot: CaptureContextSnapshot,
    ) -> list[InferredPlaceObservation]:
        existing = self.list_for_snapshot(user_id, snapshot.id)
        if existing:
            return existing
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
        place_distance = self._nearest_place(
            user_id,
            observation_latitude,
            observation_longitude,
        )
        if place_distance is None:
            return []
        place, distance = place_distance
        sensitive_label_detected = place.is_sensitive or place.privacy_class in {
            "sensitive",
            "private",
        }
        evidence = {
            "source": "geospatial_distance",
            "distance_meters": round(distance, 2),
            "place_radius_meters": place.radius_meters,
        }
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into inferred_place_observation (
                  user_id, snapshot_id, user_place_id, candidate_label,
                  candidate_category, confidence, confirmation_state, evidence,
                  sensitive_label_detected
                )
                values (%s, %s, %s, %s, %s, %s, 'needs_confirmation', %s, %s)
                returning *
                """,
                (
                    user_id,
                    snapshot.id,
                    place.id,
                    None if sensitive_label_detected else place.display_name,
                    place.category,
                    max(0.5, min(0.95, 1 - (distance / max(place.radius_meters or 1, 1)))),
                    Jsonb(evidence),
                    sensitive_label_detected,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("inferred place insert returned no row")
        return [_inferred_place_from_row(row)]

    def list_for_snapshot(
        self,
        user_id: UUID,
        snapshot_id: UUID,
    ) -> list[InferredPlaceObservation]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from inferred_place_observation
                where user_id = %s and snapshot_id = %s
                order by created_at, id
                """,
                (user_id, snapshot_id),
            )
            rows = cursor.fetchall()
        return [_inferred_place_from_row(row) for row in rows]

    def resolve_for_snapshot(
        self,
        user_id: UUID,
        request: ResolvePlaceRequest,
    ) -> ResolvePlaceResponse | None:
        if request.snapshot_id is None:
            return None
        inferred = self.list_for_snapshot(user_id, request.snapshot_id)
        if not inferred:
            return None
        candidates: list[ResolvePlaceCandidate] = []
        recommended_place_id: UUID | None = None
        for item in inferred:
            place = self._load_place(user_id, item.user_place_id)
            if recommended_place_id is None:
                recommended_place_id = item.user_place_id
            candidates.append(
                ResolvePlaceCandidate(
                    place=(
                        place
                        if place is not None and not item.sensitive_label_detected
                        else None
                    ),
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

    def _nearest_place(
        self,
        user_id: UUID,
        latitude: float,
        longitude: float,
    ) -> tuple[UserPlace, float] | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                from user_place
                where user_id = %s and latitude is not null and longitude is not null
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        best: tuple[UserPlace, float] | None = None
        for row in rows:
            place = place_from_row(row)
            if place.radius_meters is None:
                continue
            distance = _meters_between(latitude, longitude, place.latitude, place.longitude)
            if distance <= max(place.radius_meters, 25) and (
                best is None or distance < best[1]
            ):
                best = (place, distance)
        return best

    def _load_place(self, user_id: UUID, place_id: UUID | None) -> UserPlace | None:
        if place_id is None:
            return None
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                from user_place
                where user_id = %s and id = %s
                """,
                (user_id, place_id),
            )
            row = cursor.fetchone()
        return place_from_row(row) if row is not None else None


def _inferred_place_from_row(row: Mapping[str, Any]) -> InferredPlaceObservation:
    return InferredPlaceObservation.model_validate(dict(row))


def _meters_between(lat_a: float, lon_a: float, lat_b: float | None, lon_b: float | None) -> float:
    if lat_b is None or lon_b is None:
        return float("inf")
    earth_radius_meters = 6_371_000
    d_lat = radians(lat_b - lat_a)
    d_lon = radians(lon_b - lon_a)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_meters * asin(sqrt(a))
