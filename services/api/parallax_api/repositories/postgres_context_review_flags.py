from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg

from ..schemas.context import TimingReviewFlag, TimingReviewFlagStatus


class PostgresContextReviewFlagRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def list_review_flags(
        self,
        user_id: UUID,
        session_id: UUID,
        status: TimingReviewFlagStatus | None = None,
    ) -> list[TimingReviewFlag]:
        with self._connection.cursor() as cursor:
            if status is None:
                cursor.execute(
                    """
                    select id, user_id, session_id, snapshot_id, flag_type, status,
                      severity, confidence, reason_code, user_message, evidence,
                      created_at, resolved_at, resolution_note
                    from timing_review_flag
                    where user_id = %s and session_id = %s
                    order by created_at, id
                    """,
                    (user_id, session_id),
                )
            else:
                cursor.execute(
                    """
                    select id, user_id, session_id, snapshot_id, flag_type, status,
                      severity, confidence, reason_code, user_message, evidence,
                      created_at, resolved_at, resolution_note
                    from timing_review_flag
                    where user_id = %s and session_id = %s and status = %s
                    order by created_at, id
                    """,
                    (user_id, session_id, status),
                )
            rows = cursor.fetchall()
        return [TimingReviewFlag.model_validate(dict(row)) for row in rows]

    def update_review_flag(
        self,
        user_id: UUID,
        flag_id: UUID,
        status: TimingReviewFlagStatus,
        resolution_note: str | None,
    ) -> TimingReviewFlag | None:
        resolved_at = datetime.now(UTC) if status in {"resolved", "dismissed"} else None
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update timing_review_flag
                set status = %s,
                    resolved_at = %s,
                    resolution_note = %s
                where user_id = %s and id = %s
                returning id, user_id, session_id, snapshot_id, flag_type, status,
                  severity, confidence, reason_code, user_message, evidence,
                  created_at, resolved_at, resolution_note
                """,
                (status, resolved_at, resolution_note, user_id, flag_id),
            )
            row = cursor.fetchone()
        return TimingReviewFlag.model_validate(dict(row)) if row else None
