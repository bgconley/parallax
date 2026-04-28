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
                order by created_at, id
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
            set status = 'running', started_at = now(), updated_at = now()
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
                completed_at = now(),
                updated_at = now()
            where id = %s
            returning *
            """,
            (Jsonb(result_ref), workflow_id),
        )

    def mark_failed(self, workflow_id: UUID, error_code: str, error_message: str) -> WorkflowRun:
        return self._update(
            workflow_id,
            """
            update workflow_run
            set status = 'failed',
                error_code = %s,
                error_message = %s,
                completed_at = now(),
                updated_at = now()
            where id = %s
            returning *
            """,
            (error_code, error_message, workflow_id),
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
