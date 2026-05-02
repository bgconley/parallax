from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.activity_metadata import PreflightCheck, PreflightDecision, ResourceDependency


class PostgresActivityPreflightQueries:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def list_resource_dependencies(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ResourceDependency]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select id, user_id, activity_id, resource_name, required_state,
                  usual_location, failure_count, median_delay_seconds,
                  p80_delay_seconds, suggest_precheck, last_failed_at,
                  created_from_event_id, created_at, updated_at
                from resource_dependency
                where user_id = %s and activity_id = %s
                order by failure_count desc, lower(resource_name)
                """,
                (user_id, activity_id),
            )
            rows = cursor.fetchall()
        return [ResourceDependency.model_validate(dict(row)) for row in rows]

    def decide_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        check_id: UUID,
        decision: PreflightDecision,
        *,
        snoozed_until: datetime | None,
        reason: str | None,
    ) -> PreflightCheck | None:
        state = _state_for_decision(decision)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update preflight_check
                set state = %s,
                    snoozed_until = %s,
                    last_decided_at = now(),
                    decision_reason = %s,
                    updated_at = now()
                where id = %s and user_id = %s and activity_id = %s
                returning id, user_id, activity_id, check_text, state, source,
                  confidence, failure_count, last_triggered_at, source_event_id,
                  source_dependency_id, snoozed_until, evidence_count,
                  evidence_summary, last_decided_at, decision_reason,
                  created_at, updated_at
                """,
                (
                    state,
                    snoozed_until if state == "snoozed" else None,
                    reason,
                    check_id,
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
                    values (%s, %s, 'preflight.check_decided', 'preflight_check', %s, %s)
                    """,
                    (
                        user_id,
                        user_id,
                        check_id,
                        Jsonb({"decision": decision, "state": state, "reason": reason}),
                    ),
                )
        return PreflightCheck.model_validate(dict(row)) if row is not None else None


def _state_for_decision(decision: PreflightDecision) -> str:
    return {
        "accept": "active",
        "hide": "hidden",
        "snooze": "snoozed",
        "retire": "retired",
    }[decision]
