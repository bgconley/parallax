from __future__ import annotations

from typing import Any
from uuid import UUID


def ensure_app_user(cursor: Any, user_id: UUID) -> None:
    cursor.execute("insert into app_user (id) values (%s) on conflict (id) do nothing", (user_id,))
    cursor.execute(
        "insert into privacy_settings (user_id) values (%s) on conflict (user_id) do nothing",
        (user_id,),
    )


def mark_user_device_seen(cursor: Any, user_id: UUID, client_device_id: str) -> None:
    cursor.execute(
        """
        insert into user_device (user_id, client_device_id, last_seen_at)
        values (%s, %s, now())
        on conflict (user_id, client_device_id)
        do update set last_seen_at = excluded.last_seen_at
        """,
        (user_id, client_device_id),
    )
