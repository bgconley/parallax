from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg

from ..schemas.context import (
    ContextCapturePolicy,
    UpdateContextCapturePolicyRequest,
)
from .postgres_identity import ensure_app_user


class PostgresContextPolicyRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def get_context_capture_policy(self, user_id: UUID) -> ContextCapturePolicy:
        with self._connection.cursor() as cursor:
            ensure_app_user(cursor, user_id)
            cursor.execute(
                """
                insert into context_capture_policy (user_id)
                values (%s)
                on conflict (user_id) do nothing
                """,
                (user_id,),
            )
            cursor.execute(_POLICY_SELECT_SQL, (user_id,))
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("context capture policy upsert returned no row")
        return ContextCapturePolicy.model_validate(dict(row))

    def update_context_capture_policy(
        self,
        user_id: UUID,
        request: UpdateContextCapturePolicyRequest,
    ) -> ContextCapturePolicy:
        current = self.get_context_capture_policy(user_id)
        updates = {
            key: value
            for key, value in request.model_dump(exclude={"mutation"}).items()
            if value is not None
        }
        policy = current.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update context_capture_policy
                set location_enabled = %s,
                    precise_location_enabled = %s,
                    background_location_enabled = %s,
                    radio_context_enabled = %s,
                    motion_context_enabled = %s,
                    device_context_enabled = %s,
                    raw_location_retention_days = %s,
                    raw_radio_retention_days = %s,
                    default_location_retention_policy = %s,
                    default_radio_retention_policy = %s,
                    per_run_context_default = %s,
                    updated_at = %s
                where user_id = %s
                """,
                (
                    policy.location_enabled,
                    policy.precise_location_enabled,
                    policy.background_location_enabled,
                    policy.radio_context_enabled,
                    policy.motion_context_enabled,
                    policy.device_context_enabled,
                    policy.raw_location_retention_days,
                    policy.raw_radio_retention_days,
                    policy.default_location_retention_policy,
                    policy.default_radio_retention_policy,
                    policy.per_run_context_default,
                    policy.updated_at,
                    user_id,
                ),
            )
        return policy


_POLICY_SELECT_SQL = """
select id, user_id, location_enabled, precise_location_enabled,
  background_location_enabled, radio_context_enabled, motion_context_enabled,
  device_context_enabled, raw_location_retention_days, raw_radio_retention_days,
  default_location_retention_policy, default_radio_retention_policy,
  per_run_context_default, updated_at, created_at
from context_capture_policy
where user_id = %s
"""
