from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from .activity_repository import DuplicateActivityError, normalize_activity_key
from .postgres_identity import ensure_app_user

_INSERT_ACTIVITY_SQL = """
insert into activity (
  user_id, display_name, canonical_key, description,
  default_timing_mode, privacy_class
)
values (%s, %s, %s, %s, %s, %s)
returning id, user_id, display_name, canonical_key, description, status, merged_into_activity_id,
  default_timing_mode, privacy_class, created_at, updated_at
"""

_SEARCH_ACTIVITIES_SQL = """
select id, user_id, display_name, canonical_key, description, status, merged_into_activity_id,
  default_timing_mode, privacy_class, created_at, updated_at
from activity
where user_id = %s and lower(display_name) like %s
order by created_at
limit %s
"""

_LIST_ACTIVITIES_SQL = """
select id, user_id, display_name, canonical_key, description, status, merged_into_activity_id,
  default_timing_mode, privacy_class, created_at, updated_at
from activity
where user_id = %s
order by created_at
limit %s
"""

_GET_ACTIVITY_SQL = """
select id, user_id, display_name, canonical_key, description, status, merged_into_activity_id,
  default_timing_mode, privacy_class, created_at, updated_at
from activity
where user_id = %s and id = %s
"""

_RESOLVE_ACTIVITY_SQL = """
select id, user_id, display_name, canonical_key, description, status, merged_into_activity_id,
  default_timing_mode, privacy_class, created_at, updated_at
from activity
where user_id = %s and canonical_key = %s
order by created_at
limit %s
"""


class PostgresActivityRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity:
        canonical_key = normalize_activity_key(request.display_name)
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            try:
                cursor.execute(
                    _INSERT_ACTIVITY_SQL,
                    (
                        user_id,
                        request.display_name,
                        canonical_key,
                        request.description,
                        request.default_timing_mode,
                        request.privacy_class,
                    ),
                )
                row = cursor.fetchone()
            except psycopg.errors.UniqueViolation as exc:
                raise DuplicateActivityError(f"activity already exists: {canonical_key}") from exc
        if row is None:
            raise RuntimeError("activity insert returned no row")
        return _activity_from_row(row)

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]:
        with self._connection.cursor() as cursor:
            if query:
                cursor.execute(
                    _SEARCH_ACTIVITIES_SQL,
                    (user_id, f"%{query.casefold()}%", limit),
                )
            else:
                cursor.execute(
                    _LIST_ACTIVITIES_SQL,
                    (user_id, limit),
                )
            rows = cursor.fetchall()
        return [_activity_from_row(row) for row in rows]

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                _GET_ACTIVITY_SQL,
                (user_id, activity_id),
            )
            row = cursor.fetchone()
        return _activity_from_row(row) if row is not None else None

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]:
        canonical_key = normalize_activity_key(query)
        with self._connection.cursor() as cursor:
            cursor.execute(
                _RESOLVE_ACTIVITY_SQL,
                (user_id, canonical_key, limit),
            )
            rows = cursor.fetchall()

        if rows:
            return [
                ResolveActivityCandidate(
                    activity=_activity_from_row(row),
                    display_name=str(row["display_name"]),
                    confidence=1.0,
                    match_type="canonical",
                    evidence={"canonical_key": canonical_key},
                )
                for row in rows
            ]

        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  a.id, a.user_id, a.display_name, a.canonical_key, a.description, a.status,
                  a.merged_into_activity_id, a.default_timing_mode, a.privacy_class,
                  a.created_at, a.updated_at, aa.confidence as alias_confidence
                from activity_alias aa
                join activity a on a.id = aa.activity_id and a.user_id = aa.user_id
                where aa.user_id = %s and aa.normalized_alias = %s and aa.rejected = false
                order by aa.confidence desc, aa.created_at
                limit %s
                """,
                (user_id, canonical_key, limit),
            )
            alias_rows = cursor.fetchall()

        if alias_rows:
            return [
                ResolveActivityCandidate(
                    activity=_activity_from_row(row),
                    display_name=str(row["display_name"]),
                    confidence=float(row["alias_confidence"]),
                    match_type="alias",
                    evidence={"normalized_alias": canonical_key},
                )
                for row in alias_rows
            ]

        return [
            ResolveActivityCandidate(
                activity=None,
                display_name=query,
                confidence=0.0,
                match_type="no_match",
                evidence={"reason": "no matching activity"},
            )
        ]


def _activity_from_row(row: Mapping[str, Any]) -> Activity:
    return Activity.model_validate(
        {field: row[field] for field in Activity.model_fields if field in row}
    )
