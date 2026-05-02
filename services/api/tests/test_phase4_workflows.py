from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_api.schemas.context import TemporalContextAnnotation
from parallax_worker.workflow_worker import WorkflowWorker
from test_phase4_structured_extraction import (
    USER_ID,
    create_activity,
    create_annotation,
    create_started_session,
    mutation,
)


def test_annotation_extraction_records_durable_workflow_boundary() -> None:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    activity_id = create_activity(client, "Workflow boundary")
    session_id = create_started_session(client, activity_id, "workflow-boundary")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="annotation-workflow-boundary",
    )

    response = client.post(
        f"/v1/timing/annotations/{annotation['id']}/extract",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("extract-workflow-boundary", 6), "force": False},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    workflows = list(store.workflow_runs.values())
    assert len(workflows) == 1
    assert workflows[0].workflow_type == "ProcessContextAnnotationWorkflow"
    assert workflows[0].status == "queued"
    assert workflows[0].input_ref["annotation_id"] == annotation["id"]
    assert store.extracted_events == {}

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    refreshed = store.workflow_runs[workflows[0].id]
    assert refreshed.status == "succeeded"
    assert refreshed.result_ref["status"] == "needs_confirmation"


def test_worker_processes_queued_context_annotation_workflow() -> None:
    store = InMemoryStore()
    app = create_app(uow_factory=InMemoryUnitOfWorkFactory(store))
    client = TestClient(app)
    activity_id = create_activity(client, "Worker extraction")
    session_id = create_started_session(client, activity_id, "worker")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="annotation-worker",
    )
    workflow = store.workflow_runs.create_context_annotation_workflow(
        user_id=USER_ID,
        annotation_id=cast(str, annotation["id"]),
        mutation=mutation("extract-worker", 6),
        force=False,
    )

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    refreshed = store.workflow_runs[workflow.id]
    assert refreshed.status == "succeeded"
    assert refreshed.result_ref["status"] == "needs_confirmation"
    assert len(store.extracted_events) == 1


def test_worker_marks_invalid_workflow_failed_without_stopping_queue() -> None:
    store = InMemoryStore()
    workflow = store.workflow_runs.create(
        user_id=None,
        workflow_type="InferPlaceFromContextWorkflow",
        input_ref={"snapshot_id": "00000000-0000-0000-0000-000000000001"},
    )

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    refreshed = store.workflow_runs[workflow.id]
    assert refreshed.status == "failed"
    assert refreshed.error_code == "ValueError"
    assert refreshed.attempts == 1


def test_worker_requeues_retryable_failures_with_backoff() -> None:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    activity_id = create_activity(client, "Workflow retry")
    session_id = create_started_session(client, activity_id, "workflow-retry")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="annotation-workflow-retry",
    )
    workflow = store.workflow_runs.create_context_annotation_workflow(
        user_id=USER_ID,
        annotation_id=cast(str, annotation["id"]),
        mutation=mutation("extract-worker-retry", 6),
        force=False,
    )

    processed = WorkflowWorker(
        InMemoryUnitOfWorkFactory(store),
        extractor=TransientExtractor(),
    ).drain_once()

    assert processed == 1
    retrying = store.workflow_runs[workflow.id]
    assert retrying.status == "queued"
    assert retrying.error_code == "RuntimeError"
    assert retrying.attempts == 1
    assert retrying.next_run_at is not None
    assert retrying.next_run_at > retrying.updated_at

    store.workflow_runs[workflow.id] = retrying.model_copy(
        update={"next_run_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    refreshed = store.workflow_runs[workflow.id]
    assert refreshed.status == "succeeded"
    assert refreshed.attempts == 2
    assert refreshed.error_code is None
    assert refreshed.error_message is None


class TransientExtractor:
    def extract(self, annotation: TemporalContextAnnotation) -> dict[str, object]:
        raise RuntimeError("transient extractor outage")
