from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityIdentityChange,
    ActivityMergePreview,
    ActivityRelationship,
    ActivitySplitPreview,
    CheckpointTemplate,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    PreflightCheck,
    PreflightDecision,
    PutCheckpointsRequest,
    ResourceDependency,
)
from .activity_repository import DuplicateActivityError, normalize_activity_key
from .postgres_activity_identity import PostgresActivityIdentityQueries
from .postgres_activity_preflight import PostgresActivityPreflightQueries
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
        self._identity = PostgresActivityIdentityQueries(connection)
        self._preflight = PostgresActivityPreflightQueries(connection)

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
                where aa.user_id = %s
                  and aa.normalized_alias = %s
                  and aa.user_confirmed = true
                  and aa.rejected = false
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

    def add_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_text: str,
        *,
        user_confirmed: bool,
    ) -> ActivityAlias:
        normalized_alias = normalize_activity_key(alias_text)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into activity_alias (
                  user_id, activity_id, alias_text, normalized_alias,
                  source, confidence, user_confirmed
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    user_id,
                    activity_id,
                    alias_text,
                    normalized_alias,
                    "user" if user_confirmed else "system_suggested",
                    1.0 if user_confirmed else 0.75,
                    user_confirmed,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("activity alias insert returned no row")
        return ActivityAlias.model_validate(dict(row))

    def list_aliases(self, user_id: UUID, activity_id: UUID) -> list[ActivityAlias]:
        return self._identity.list_aliases(user_id, activity_id)

    def decide_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_id: UUID,
        decision: str,
    ) -> ActivityAlias | None:
        return self._identity.decide_alias(user_id, activity_id, alias_id, decision)

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into activity_relationship (
                  user_id, from_activity_id, to_activity_id, kind, metadata, user_confirmed, state
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    user_id,
                    activity_id,
                    request.to_activity_id,
                    request.kind,
                    Jsonb(request.metadata),
                    request.user_confirmed,
                    "confirmed" if request.user_confirmed else "suggested",
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("activity relationship insert returned no row")
        return ActivityRelationship.model_validate(dict(row))

    def list_relationships(self, user_id: UUID, activity_id: UUID) -> list[ActivityRelationship]:
        return self._identity.list_relationships(user_id, activity_id)

    def decide_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        relationship_id: UUID,
        decision: str,
    ) -> ActivityRelationship | None:
        return self._identity.decide_relationship(
            user_id,
            activity_id,
            relationship_id,
            decision,
        )

    def merge_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
    ) -> ActivityMergePreview:
        return self._identity.merge_preview(user_id, source_activity_id, target_activity_id)

    def merge_activities(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
        reason: str | None,
    ) -> ActivityIdentityChange:
        return self._identity.merge_activities(
            user_id,
            source_activity_id,
            target_activity_id,
            reason,
        )

    def split_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        proposed_display_name: str,
        session_ids: list[UUID],
    ) -> ActivitySplitPreview:
        return self._identity.split_preview(
            user_id,
            source_activity_id,
            proposed_display_name,
            session_ids,
        )

    def list_checkpoints(self, user_id: UUID, activity_id: UUID) -> list[CheckpointTemplate]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from checkpoint_template
                where user_id = %s and activity_id = %s
                order by sequence_order
                """,
                (user_id, activity_id),
            )
            rows = cursor.fetchall()
        return [CheckpointTemplate.model_validate(dict(row)) for row in rows]

    def replace_checkpoints(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: PutCheckpointsRequest,
    ) -> list[CheckpointTemplate]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                "delete from checkpoint_template where user_id = %s and activity_id = %s",
                (user_id, activity_id),
            )
            checkpoints: list[CheckpointTemplate] = []
            sorted_checkpoints = sorted(
                request.checkpoints,
                key=lambda checkpoint: checkpoint.sequence_order,
            )
            for item in sorted_checkpoints:
                cursor.execute(
                    """
                    insert into checkpoint_template (
                      user_id, activity_id, sequence_order, label, phase_type, optional
                    )
                    values (%s, %s, %s, %s, %s, %s)
                    returning *
                    """,
                    (
                        user_id,
                        activity_id,
                        item.sequence_order,
                        item.label,
                        item.phase_type,
                        item.optional,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("checkpoint template insert returned no row")
                checkpoints.append(CheckpointTemplate.model_validate(dict(row)))
        return checkpoints

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, activity_id, check_text, state, source, confidence,
                  failure_count, last_triggered_at, source_event_id,
                  source_dependency_id, snoozed_until, evidence_count,
                  evidence_summary, last_decided_at, decision_reason,
                  created_at, updated_at
                from preflight_check
                where user_id = %s and activity_id = %s
                order by check_text
                """,
                (user_id, activity_id),
            )
            rows = cursor.fetchall()
        return [PreflightCheck.model_validate(dict(row)) for row in rows]

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into preflight_check (
                  user_id, activity_id, check_text, state, source, confidence
                )
                values (%s, %s, %s, %s, %s, %s)
                returning id, user_id, activity_id, check_text, state, source, confidence,
                  failure_count, last_triggered_at, source_event_id,
                  source_dependency_id, snoozed_until, evidence_count,
                  evidence_summary, last_decided_at, decision_reason,
                  created_at, updated_at
                """,
                (
                    user_id,
                    activity_id,
                    request.check_text,
                    "active" if request.source == "user_created" else "suggested",
                    request.source,
                    1.0 if request.source == "user_created" else None,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("preflight check insert returned no row")
        return PreflightCheck.model_validate(dict(row))

    def list_resource_dependencies(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ResourceDependency]:
        return self._preflight.list_resource_dependencies(user_id, activity_id)

    def decide_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        check_id: UUID,
        decision: PreflightDecision,
        *,
        snoozed_until: Any,
        reason: str | None,
    ) -> PreflightCheck | None:
        return self._preflight.decide_preflight_check(
            user_id,
            activity_id,
            check_id,
            decision,
            snoozed_until=snoozed_until,
            reason=reason,
        )


def _activity_from_row(row: Mapping[str, Any]) -> Activity:
    return Activity.model_validate(
        {field: row[field] for field in Activity.model_fields if field in row}
    )
