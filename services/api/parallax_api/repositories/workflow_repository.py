from __future__ import annotations

from datetime import UTC, datetime
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
        queued = [
            workflow
            for workflow in self._store.workflow_runs.values()
            if workflow.status == "queued"
        ]
        return sorted(queued, key=lambda workflow: workflow.created_at)[0] if queued else None

    def mark_running(self, workflow_id: UUID) -> WorkflowRun:
        workflow = self._store.workflow_runs[workflow_id]
        now = datetime.now(UTC)
        updated = workflow.model_copy(
            update={
                "status": "running",
                "started_at": now,
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
                "completed_at": now,
                "updated_at": now,
            }
        )
        self._store.workflow_runs[workflow_id] = updated
        return updated

    def mark_failed(self, workflow_id: UUID, error_code: str, error_message: str) -> WorkflowRun:
        workflow = self._store.workflow_runs[workflow_id]
        now = datetime.now(UTC)
        updated = workflow.model_copy(
            update={
                "status": "failed",
                "error_code": error_code,
                "error_message": error_message,
                "completed_at": now,
                "updated_at": now,
            }
        )
        self._store.workflow_runs[workflow_id] = updated
        return updated
