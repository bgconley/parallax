from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg


def update_session_projection(
    connection: psycopg.Connection[Any],
    user_id: UUID,
    session_id: UUID,
    updates: dict[str, object],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update timing_session
            set status = %s,
                started_at = %s,
                completed_at = %s,
                wall_seconds = %s,
                active_seconds = %s,
                needs_timeline_recompute = %s,
                updated_at = now()
            where user_id = %s and id = %s
            """,
            (
                updates["status"],
                updates["started_at"],
                updates["completed_at"],
                updates["wall_seconds"],
                updates["active_seconds"],
                updates["needs_timeline_recompute"],
                user_id,
                session_id,
            ),
        )


def update_session_friction_totals(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    user_id: UUID,
    session_id: UUID,
) -> None:
    cursor.execute(
        """
        select span_type, coalesce(sum(duration_seconds), 0)::integer as seconds
        from timing_event_span
        where user_id = %s and session_id = %s
        group by span_type
        """,
        (user_id, session_id),
    )
    totals = {row["span_type"]: row["seconds"] for row in cursor.fetchall()}
    cursor.execute(
        """
        update timing_session
        set setup_seconds = %s,
            detour_seconds = %s,
            interruption_seconds = %s,
            waiting_seconds = %s,
            side_quest_seconds = %s,
            start_latency_seconds = %s,
            transition_seconds = %s,
            updated_at = now()
        where user_id = %s and id = %s
        """,
        (
            totals.get("setup", 0),
            totals.get("resource_detour", 0),
            totals.get("interruption", 0),
            totals.get("waiting", 0),
            totals.get("side_quest", 0),
            totals.get("start_latency", 0),
            totals.get("transition", 0),
            user_id,
            session_id,
        ),
    )
