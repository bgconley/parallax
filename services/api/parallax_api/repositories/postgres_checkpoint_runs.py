from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

_LOAD_CHECKPOINT_RUN_SELECT = """
select id, user_id, session_id, checkpoint_template_id, sequence_order, label,
  started_at, completed_at, active_seconds, wall_seconds, friction_seconds,
  status, user_corrected, metadata, created_at
from checkpoint_run
where user_id = %s and session_id = %s
"""

_LOAD_CHECKPOINT_RUN_BY_ID_SQL = f"{_LOAD_CHECKPOINT_RUN_SELECT} and id = %s limit 1"
_LOAD_CHECKPOINT_RUN_BY_TEMPLATE_SQL = (
    f"{_LOAD_CHECKPOINT_RUN_SELECT} and checkpoint_template_id = %s limit 1"
)
_LOAD_CHECKPOINT_RUN_BY_SEQUENCE_SQL = (
    f"{_LOAD_CHECKPOINT_RUN_SELECT} and sequence_order = %s limit 1"
)


def create_checkpoint_runs_for_session(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    *,
    user_id: UUID,
    session_id: UUID,
    activity_id: UUID,
) -> None:
    cursor.execute(
        """
        insert into checkpoint_run (
          user_id, session_id, checkpoint_template_id, sequence_order, label, metadata
        )
        select user_id, %s, id, sequence_order, label,
          jsonb_build_object('phase_type', phase_type, 'optional', optional)
        from checkpoint_template
        where user_id = %s and activity_id = %s
        order by sequence_order
        on conflict (session_id, sequence_order) do nothing
        """,
        (session_id, user_id, activity_id),
    )


def checkpoint_event_payload(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    *,
    user_id: UUID,
    session_id: UUID,
    event_type: str,
    client_time: datetime,
    payload: dict[str, object],
) -> dict[str, object]:
    if not event_type.startswith("checkpoint_"):
        return payload
    run = _resolve_checkpoint_run(cursor, user_id, session_id, payload)
    if run is None:
        return payload
    _apply_checkpoint_state(cursor, run, event_type, client_time)
    return {**payload, "checkpoint_run_id": str(run["id"])}


def _resolve_checkpoint_run(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    user_id: UUID,
    session_id: UUID,
    payload: dict[str, object],
) -> Mapping[str, Any] | None:
    run_id = _payload_uuid(payload, "checkpoint_run_id")
    template_id = _payload_uuid(payload, "checkpoint_template_id")
    sequence_order = _payload_int(payload, "sequence_order")
    if run_id is not None:
        return _load_checkpoint_run(
            cursor,
            user_id,
            session_id,
            "id",
            run_id,
        )
    elif template_id is not None:
        return _load_checkpoint_run(
            cursor,
            user_id,
            session_id,
            "checkpoint_template_id",
            template_id,
        )
    elif sequence_order is not None:
        row = _load_checkpoint_run(
            cursor,
            user_id,
            session_id,
            "sequence_order",
            sequence_order,
        )
        if row is not None:
            return row
        return _insert_ad_hoc_checkpoint_run(
            cursor,
            user_id,
            session_id,
            sequence_order,
            template_id,
            str(payload.get("label") or f"Checkpoint {sequence_order}"),
        )
    else:
        return None


def _load_checkpoint_run(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    user_id: UUID,
    session_id: UUID,
    field: str,
    value: object,
) -> Mapping[str, Any] | None:
    if field == "id":
        query = _LOAD_CHECKPOINT_RUN_BY_ID_SQL
    elif field == "checkpoint_template_id":
        query = _LOAD_CHECKPOINT_RUN_BY_TEMPLATE_SQL
    elif field == "sequence_order":
        query = _LOAD_CHECKPOINT_RUN_BY_SEQUENCE_SQL
    else:
        raise ValueError(f"unsupported checkpoint lookup field: {field}")
    cursor.execute(
        query,
        (user_id, session_id, value),
    )
    return cursor.fetchone()


def _insert_ad_hoc_checkpoint_run(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    user_id: UUID,
    session_id: UUID,
    sequence_order: int,
    template_id: UUID | None,
    label: str,
) -> Mapping[str, Any]:
    cursor.execute(
        """
        insert into checkpoint_run (
          user_id, session_id, checkpoint_template_id, sequence_order, label, metadata
        )
        values (%s, %s, %s, %s, %s, %s)
        returning id, user_id, session_id, checkpoint_template_id, sequence_order, label,
          started_at, completed_at, active_seconds, wall_seconds, friction_seconds,
          status, user_corrected, metadata, created_at
        """,
        (user_id, session_id, template_id, sequence_order, label, Jsonb({"ad_hoc": True})),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("checkpoint run insert returned no row")
    return row


def _apply_checkpoint_state(
    cursor: psycopg.Cursor[Mapping[str, Any]],
    run: Mapping[str, Any],
    event_type: str,
    client_time: datetime,
) -> None:
    if event_type == "checkpoint_started":
        cursor.execute(
            """
            update checkpoint_run
            set status = 'running',
                started_at = coalesce(started_at, %s),
                metadata = metadata || %s
            where id = %s
            """,
            (client_time, Jsonb({"last_event_type": event_type}), run["id"]),
        )
        return
    if event_type == "checkpoint_completed":
        started_at = run["started_at"] or client_time
        duration = _non_negative_seconds(started_at, client_time)
        cursor.execute(
            """
            update checkpoint_run
            set status = 'completed',
                started_at = %s,
                completed_at = %s,
                active_seconds = %s,
                wall_seconds = %s,
                metadata = metadata || %s
            where id = %s
            """,
            (
                started_at,
                client_time,
                duration,
                duration,
                Jsonb({"last_event_type": event_type}),
                run["id"],
            ),
        )
        return
    if event_type == "checkpoint_skipped":
        cursor.execute(
            """
            update checkpoint_run
            set status = 'skipped',
                completed_at = %s,
                active_seconds = 0,
                wall_seconds = 0,
                metadata = metadata || %s
            where id = %s
            """,
            (client_time, Jsonb({"last_event_type": event_type}), run["id"]),
        )


def _payload_uuid(payload: dict[str, object], key: str) -> UUID | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _payload_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except ValueError:
        return None
    return parsed if parsed >= 1 else None


def _non_negative_seconds(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds()))
