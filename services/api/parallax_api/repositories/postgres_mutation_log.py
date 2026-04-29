from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from ..schemas.common import MutationEnvelope
from .mutation_log import StoredMutation, StoredSyncChange
from .postgres_identity import ensure_app_user, mark_user_device_seen


class PostgresMutationLogRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def lock(self, user_id: UUID, mutation: MutationEnvelope) -> None:
        lock_keys = sorted(
            (
                f"{user_id}:device:{mutation.client_device_id}:{mutation.client_mutation_id}",
                f"{user_id}:idempotency:{mutation.idempotency_key}",
            )
        )
        with self._connection.cursor() as cursor:
            for lock_key in lock_keys:
                cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", (lock_key,))

    def get(self, user_id: UUID, mutation: MutationEnvelope) -> StoredMutation | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select mutation_type, entity_type, entity_id, result_json
                from client_mutation_log
                where user_id = %s
                  and (
                    (client_device_id = %s and client_mutation_id = %s)
                    or idempotency_key = %s
                  )
                order by received_at asc
                limit 1
                """,
                (
                    user_id,
                    mutation.client_device_id,
                    mutation.client_mutation_id,
                    mutation.idempotency_key,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return StoredMutation(
            mutation_type=row["mutation_type"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            result=row["result_json"],
        )

    def list_changes(
        self,
        user_id: UUID,
        *,
        cursor: str | None,
        limit: int,
    ) -> list[StoredSyncChange]:
        after = _parse_sync_cursor(cursor)
        with self._connection.cursor() as cursor_handle:
            if after is None:
                cursor_handle.execute(
                    """
                    select id, mutation_type, entity_type, entity_id, result_json, received_at
                    from client_mutation_log
                    where user_id = %s and mutation_type <> 'sync_push'
                    order by received_at asc, id asc
                    limit %s
                    """,
                    (user_id, limit),
                )
            else:
                received_at, mutation_id = after
                cursor_handle.execute(
                    """
                    select id, mutation_type, entity_type, entity_id, result_json, received_at
                    from client_mutation_log
                    where user_id = %s
                      and mutation_type <> 'sync_push'
                      and (
                        received_at > %s
                        or (received_at = %s and id > %s)
                      )
                    order by received_at asc, id asc
                    limit %s
                    """,
                    (user_id, received_at, received_at, mutation_id, limit),
                )
            rows = cursor_handle.fetchall()
        return [
            StoredSyncChange(
                cursor=_sync_cursor(row["received_at"], row["id"]),
                mutation_type=row["mutation_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                result=row["result_json"],
                received_at=row["received_at"],
            )
            for row in rows
        ]

    def save(
        self,
        *,
        user_id: UUID,
        mutation: MutationEnvelope,
        mutation_type: str,
        entity_type: str,
        entity_id: UUID | None,
        result: BaseModel,
    ) -> None:
        result_json = result.model_dump(mode="json")
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            mark_user_device_seen(cursor, user_id, mutation.client_device_id)
            cursor.execute(
                """
                insert into client_mutation_log (
                  user_id, client_device_id, client_mutation_id, idempotency_key,
                  mutation_type, entity_type, entity_id, result_json
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, idempotency_key) do nothing
                """,
                (
                    user_id,
                    mutation.client_device_id,
                    mutation.client_mutation_id,
                    mutation.idempotency_key,
                    mutation_type,
                    entity_type,
                    entity_id,
                    Jsonb(result_json),
                ),
            )


def _sync_cursor(received_at: datetime, mutation_id: UUID) -> str:
    return f"{received_at.isoformat()}|{mutation_id}"


def _parse_sync_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    timestamp, separator, mutation_id = cursor.partition("|")
    if separator != "|":
        raise ValueError("invalid sync cursor")
    return (datetime.fromisoformat(timestamp), UUID(mutation_id))
