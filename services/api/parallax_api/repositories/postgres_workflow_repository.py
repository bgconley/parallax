from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..schemas.workflows import WorkflowRun


class PostgresWorkflowRunRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def enqueue(
        self,
        user_id: UUID | None,
        workflow_type: str,
        input_ref: dict[str, object],
    ) -> WorkflowRun:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into workflow_run (user_id, workflow_type, status, input_ref)
                values (%s, %s, 'queued', %s)
                returning *
                """,
                (user_id, workflow_type, Jsonb(input_ref)),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("workflow enqueue returned no row")
        return _workflow_from_row(row)

    def get_next_queued(self) -> WorkflowRun | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from workflow_run
                where status = 'queued'
                  and next_run_at <= now()
                order by next_run_at, created_at, id
                limit 1
                for update skip locked
                """
            )
            row = cursor.fetchone()
        return _workflow_from_row(row) if row is not None else None

    def mark_running(self, workflow_id: UUID) -> WorkflowRun:
        return self._update(
            workflow_id,
            """
            update workflow_run
            set status = 'running',
                attempts = attempts + 1,
                started_at = now(),
                last_heartbeat_at = now(),
                updated_at = now()
            where id = %s
            returning *
            """,
            (workflow_id,),
        )

    def mark_succeeded(self, workflow_id: UUID, result_ref: dict[str, object]) -> WorkflowRun:
        return self._update(
            workflow_id,
            """
            update workflow_run
            set status = 'succeeded',
                result_ref = %s,
                error_code = null,
                error_message = null,
                completed_at = now(),
                updated_at = now()
            where id = %s
            returning *
            """,
            (Jsonb(result_ref), workflow_id),
        )

    def mark_failed(
        self,
        workflow_id: UUID,
        error_code: str,
        error_message: str,
        *,
        retryable: bool = True,
    ) -> WorkflowRun:
        return self._update(
            workflow_id,
            """
            update workflow_run
            set status = case
                    when %s and attempts < max_attempts then 'queued'::job_status
                    else 'failed'::job_status
                end,
                error_code = %s,
                error_message = %s,
                completed_at = case
                    when %s and attempts < max_attempts then null
                    else now()
                end,
                next_run_at = case
                    when %s and attempts < max_attempts then
                      now() + make_interval(
                        secs => least(
                          300,
                          greatest(1, (power(2, attempts - 1))::int)
                        )
                      )
                    else next_run_at
                end,
                updated_at = now()
            where id = %s
            returning *
            """,
            (retryable, error_code, error_message, retryable, retryable, workflow_id),
        )

    def _update(
        self,
        workflow_id: UUID,
        sql: str,
        params: tuple[object, ...],
    ) -> WorkflowRun:
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        if row is None:
            raise KeyError(workflow_id)
        return _workflow_from_row(row)


def _workflow_from_row(row: Mapping[str, Any]) -> WorkflowRun:
    return WorkflowRun.model_validate(dict(row))
