from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityIdentityChange,
    ActivityMergePreview,
    ActivityRelationship,
    ActivitySplitPreview,
)


class PostgresActivityIdentityQueries:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def list_aliases(self, user_id: UUID, activity_id: UUID) -> list[ActivityAlias]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from activity_alias
                where user_id = %s and activity_id = %s
                order by created_at
                """,
                (user_id, activity_id),
            )
            rows = cursor.fetchall()
        return [ActivityAlias.model_validate(dict(row)) for row in rows]

    def decide_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_id: UUID,
        decision: str,
    ) -> ActivityAlias | None:
        accepted = decision == "accept"
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update activity_alias
                set user_confirmed = %s,
                    rejected = %s,
                    confidence = case when %s then 1.0 else confidence end
                where id = %s and user_id = %s and activity_id = %s
                returning *
                """,
                (accepted, not accepted, accepted, alias_id, user_id, activity_id),
            )
            row = cursor.fetchone()
            if row is not None:
                cursor.execute(
                    """
                    insert into audit_log (
                      user_id, actor_user_id, event_name, entity_type, entity_id, metadata
                    )
                    values (%s, %s, 'activity.alias_decided', 'activity_alias', %s, %s)
                    """,
                    (
                        user_id,
                        user_id,
                        alias_id,
                        Jsonb({"activity_id": str(activity_id), "decision": decision}),
                    ),
                )
        return ActivityAlias.model_validate(dict(row)) if row is not None else None

    def list_relationships(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ActivityRelationship]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from activity_relationship
                where user_id = %s and from_activity_id = %s
                order by created_at
                """,
                (user_id, activity_id),
            )
            rows = cursor.fetchall()
        return [ActivityRelationship.model_validate(dict(row)) for row in rows]

    def decide_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        relationship_id: UUID,
        decision: str,
    ) -> ActivityRelationship | None:
        accepted = decision == "accept"
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update activity_relationship
                set user_confirmed = %s,
                    state = %s
                where id = %s and user_id = %s and from_activity_id = %s
                returning *
                """,
                (
                    accepted,
                    "confirmed" if accepted else "rejected",
                    relationship_id,
                    user_id,
                    activity_id,
                ),
            )
            row = cursor.fetchone()
            if row is not None:
                cursor.execute(
                    """
                    insert into audit_log (
                      user_id, actor_user_id, event_name, entity_type, entity_id, metadata
                    )
                    values (
                      %s, %s, 'activity.relationship_decided',
                      'activity_relationship', %s, %s
                    )
                    """,
                    (
                        user_id,
                        user_id,
                        relationship_id,
                        Jsonb({"activity_id": str(activity_id), "decision": decision}),
                    ),
                )
        return ActivityRelationship.model_validate(dict(row)) if row is not None else None

    def merge_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
    ) -> ActivityMergePreview:
        return ActivityMergePreview(
            source_activity_id=source_activity_id,
            target_activity_id=target_activity_id,
            affected_session_count=self._count_sessions(user_id, source_activity_id),
        )

    def merge_activities(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
        reason: str | None,
    ) -> ActivityIdentityChange:
        affected_session_count = self._count_sessions(user_id, source_activity_id)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update activity
                set status = 'merged',
                    merged_into_activity_id = %s,
                    updated_at = now()
                where user_id = %s and id = %s
                """,
                (target_activity_id, user_id, source_activity_id),
            )
            cursor.execute(
                """
                insert into activity_relationship (
                  user_id, from_activity_id, to_activity_id, kind,
                  metadata, user_confirmed, state
                )
                values (%s, %s, %s, 'same_as', %s, true, 'confirmed')
                on conflict (from_activity_id, to_activity_id, kind)
                do update set user_confirmed = true, state = 'confirmed',
                  metadata = activity_relationship.metadata || excluded.metadata
                returning *
                """,
                (
                    user_id,
                    source_activity_id,
                    target_activity_id,
                    Jsonb({"reason": reason} if reason else {}),
                ),
            )
            cursor.execute(
                """
                insert into audit_log (
                  user_id, actor_user_id, event_name, entity_type, entity_id, metadata
                )
                values (%s, %s, 'activity.merged', 'activity', %s, %s)
                returning id
                """,
                (
                    user_id,
                    user_id,
                    source_activity_id,
                    Jsonb(
                        {
                            "target_activity_id": str(target_activity_id),
                            "affected_session_count": affected_session_count,
                            "reason": reason,
                        }
                    ),
                ),
            )
            audit_row = cursor.fetchone()
            if audit_row is None:
                raise RuntimeError("activity merge audit insert returned no row")
            cursor.execute(
                """
                insert into activity_identity_change (
                  user_id, change_type, source_activity_id, target_activity_id,
                  affected_session_count, audit_id, metadata
                )
                values (%s, 'merge', %s, %s, %s, %s, %s)
                returning id, user_id, change_type, source_activity_id,
                  target_activity_id, affected_session_count, audit_id, created_at
                """,
                (
                    user_id,
                    source_activity_id,
                    target_activity_id,
                    affected_session_count,
                    audit_row["id"],
                    Jsonb({"reason": reason} if reason else {}),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("activity identity change insert returned no row")
        return ActivityIdentityChange.model_validate(dict(row))

    def split_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        proposed_display_name: str,
        session_ids: list[UUID],
    ) -> ActivitySplitPreview:
        with self._connection.cursor() as cursor:
            if session_ids:
                cursor.execute(
                    """
                    select count(*)
                    from timing_session
                    where user_id = %s and activity_id = %s and id = any(%s)
                    """,
                    (user_id, source_activity_id, session_ids),
                )
            else:
                cursor.execute(
                    """
                    select count(*)
                    from timing_session
                    where user_id = %s and activity_id = %s
                    """,
                    (user_id, source_activity_id),
                )
            row = cursor.fetchone()
        return ActivitySplitPreview(
            source_activity_id=source_activity_id,
            proposed_display_name=proposed_display_name,
            movable_session_count=int(row["count"]) if row is not None else 0,
        )

    def _count_sessions(self, user_id: UUID, activity_id: UUID) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*)
                from timing_session
                where user_id = %s and activity_id = %s
                """,
                (user_id, activity_id),
            )
            row = cursor.fetchone()
        return int(row["count"]) if row is not None else 0
