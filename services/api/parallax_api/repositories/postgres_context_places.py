from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.context import (
    CreatePlaceRequest,
    ResolvePlaceCandidate,
    ResolvePlaceRequest,
    ResolvePlaceResponse,
    UpdatePlaceRequest,
    UserPlace,
)
from .postgres_context_common import place_from_row
from .postgres_identity import ensure_app_user


class PostgresContextPlaceRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create_place(self, user_id: UUID, request: CreatePlaceRequest) -> UserPlace:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into user_place (
                  user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                """,
                (
                    user_id,
                    request.display_name,
                    request.category,
                    request.latitude,
                    request.longitude,
                    request.radius_meters,
                    request.source,
                    request.privacy_class,
                    request.confirmed_by_user,
                    request.is_sensitive,
                    request.aliases,
                    Jsonb(request.metadata),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("place insert returned no row")
        return place_from_row(row)

    def list_places(self, user_id: UUID) -> list[UserPlace]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, display_name, category, latitude, longitude,
                  radius_meters, source, privacy_class, confirmed_by_user,
                  is_sensitive, aliases, metadata, created_at, updated_at
                from user_place
                where user_id = %s
                order by created_at, id
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        return [place_from_row(row) for row in rows]

    def get_place(self, user_id: UUID, place_id: UUID) -> UserPlace | None:
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
        return place_from_row(row) if row else None

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
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update user_place
                set display_name = %s,
                    category = %s,
                    radius_meters = %s,
                    privacy_class = %s,
                    confirmed_by_user = %s,
                    is_sensitive = %s,
                    aliases = %s,
                    updated_at = %s
                where user_id = %s and id = %s
                """,
                (
                    updated.display_name,
                    updated.category,
                    updated.radius_meters,
                    updated.privacy_class,
                    updated.confirmed_by_user,
                    updated.is_sensitive,
                    updated.aliases,
                    updated.updated_at,
                    user_id,
                    place_id,
                ),
            )
        return updated

    def resolve_place(self, user_id: UUID, request: ResolvePlaceRequest) -> ResolvePlaceResponse:
        existing = (
            self.get_place(user_id, request.existing_place_id)
            if request.existing_place_id
            else None
        )
        if existing is None and request.candidate_label:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, user_id, display_name, category, latitude, longitude,
                      radius_meters, source, privacy_class, confirmed_by_user,
                      is_sensitive, aliases, metadata, created_at, updated_at
                    from user_place
                    where user_id = %s and lower(display_name) = lower(%s)
                    order by confirmed_by_user desc, created_at desc
                    limit 1
                    """,
                    (user_id, request.candidate_label),
                )
                row = cursor.fetchone()
            existing = place_from_row(row) if row else None
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
