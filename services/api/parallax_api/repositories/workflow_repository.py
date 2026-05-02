from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from ..schemas.workflows import WorkflowRun
from .memory import InMemoryStore


class WorkflowRunRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def enqueue(
        self,
        user_id: UUID | None,
        workflow_type: str,
        input_ref: dict[str, object],
    ) -> WorkflowRun:
        return self._store.workflow_runs.create(
            user_id=user_id,
            workflow_type=workflow_type,
            input_ref=input_ref,
        )

    def get_next_queued(self) -> WorkflowRun | None:
        now = datetime.now(UTC)
        queued = [
            workflow
            for workflow in self._store.workflow_runs.values()
            if workflow.status == "queued"
            and (workflow.next_run_at is None or workflow.next_run_at <= now)
        ]
        return sorted(
            queued,
            key=lambda workflow: (workflow.next_run_at or workflow.created_at, workflow.created_at),
        )[0] if queued else None

    def mark_running(self, workflow_id: UUID) -> WorkflowRun:
        workflow = self._store.workflow_runs[workflow_id]
        now = datetime.now(UTC)
        updated = workflow.model_copy(
            update={
                "status": "running",
                "attempts": workflow.attempts + 1,
                "started_at": now,
                "last_heartbeat_at": now,
                "updated_at": now,
            }
        )
        self._store.workflow_runs[workflow_id] = updated
        return updated

    def mark_succeeded(self, workflow_id: UUID, result_ref: dict[str, object]) -> WorkflowRun:
        workflow = self._store.workflow_runs[workflow_id]
        now = datetime.now(UTC)
        updated = workflow.model_copy(
            update={
                "status": "succeeded",
                "result_ref": result_ref,
                "error_code": None,
                "error_message": None,
                "completed_at": now,
                "updated_at": now,
            }
        )
        self._store.workflow_runs[workflow_id] = updated
        return updated

    def mark_failed(
        self,
        workflow_id: UUID,
        error_code: str,
        error_message: str,
        *,
        retryable: bool = True,
    ) -> WorkflowRun:
        workflow = self._store.workflow_runs[workflow_id]
        now = datetime.now(UTC)
        should_retry = retryable and workflow.attempts < workflow.max_attempts
        next_run_at = (
            now + _retry_delay(workflow.attempts) if should_retry else workflow.next_run_at
        )
        updated = workflow.model_copy(
            update={
                "status": "queued" if should_retry else "failed",
                "error_code": error_code,
                "error_message": error_message,
                "completed_at": None if should_retry else now,
                "next_run_at": next_run_at,
                "updated_at": now,
            }
        )
        self._store.workflow_runs[workflow_id] = updated
        return updated


def _retry_delay(attempts: int) -> timedelta:
    seconds = min(300, max(1, 2 ** max(0, attempts - 1)))
    return timedelta(seconds=seconds)
