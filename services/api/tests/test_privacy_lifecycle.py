from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_api.schemas.temporal import TemporalQueryAnswer
from parallax_worker.workflow_worker import WorkflowWorker

USER_ID = "00000000-0000-0000-0000-00000000d001"
HEADERS = {"X-Parallax-User-Id": USER_ID}


def mutation(label: str) -> dict[str, object]:
    unique = uuid4()
    return {
        "client_mutation_id": f"{label}-{unique}",
        "client_device_id": "privacy-lifecycle-test",
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"privacy-lifecycle-test:{label}:{unique}",
        "client_sequence": 1,
    }


def make_client_and_store() -> tuple[TestClient, InMemoryStore]:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    return client, store


def seed_temporal_query_answer(store: InMemoryStore) -> TemporalQueryAnswer:
    answer = TemporalQueryAnswer(
        id=uuid4(),
        user_id=UUID(USER_ID),
        question="What did my private context say?",
        answer="Derived answer",
        confidence="very_low",
        sample_size=0,
        time_window="last_180_days",
        computed_facts={},
        limitations=[],
        evidence=[],
        status="complete",
    )
    store.temporal_query_answers[answer.id] = answer
    return answer


def test_place_context_delete_is_durable_and_redacts_place_after_worker_runs() -> None:
    client, store = make_client_and_store()
    place = client.post(
        "/v1/places",
        headers=HEADERS,
        json={
            "mutation": mutation("place"),
            "display_name": "Private Home Label",
            "category": "home",
            "latitude": 40.0,
            "longitude": -70.0,
            "radius_meters": 50,
            "source": "manual_place",
            "privacy_class": "private",
            "confirmed_by_user": True,
            "is_sensitive": True,
            "aliases": ["home alias"],
            "metadata": {"raw_hint": "garage side door"},
        },
    ).json()

    response = client.post(
        "/v1/privacy/delete",
        headers=HEADERS,
        json={
            "mutation": mutation("delete-place-context"),
            "delete_scope": "place_context",
            "entity_id": place["id"],
            "confirm": True,
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    listed_places = client.get("/v1/places", headers=HEADERS).json()
    assert listed_places[0]["display_name"] == "Private Home Label"
    query_answer = seed_temporal_query_answer(store)

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    redacted = client.get("/v1/places", headers=HEADERS).json()[0]
    assert redacted["id"] == place["id"]
    assert redacted["display_name"] == "Deleted place"
    assert redacted["latitude"] is None
    assert redacted["longitude"] is None
    assert redacted["aliases"] == []
    workflow = next(iter(store.workflow_runs.values()))
    assert workflow.workflow_type == "DataExportDeletionWorkflow"
    assert workflow.status == "succeeded"
    deleted = cast(dict[str, Any], workflow.result_ref["deleted"])
    assert deleted["places"] == 1
    assert deleted["query_answers"] == 1
    assert query_answer.id not in store.temporal_query_answers


def test_privacy_redact_waits_for_worker_and_redacts_annotation_payload() -> None:
    client, store = make_client_and_store()
    activity = client.post(
        "/v1/activities",
        headers=HEADERS,
        json={"mutation": mutation("activity"), "display_name": "Privacy annotation"},
    ).json()
    session = client.post(
        "/v1/timing/sessions",
        headers=HEADERS,
        json={
            "mutation": mutation("session"),
            "activity_id": activity["id"],
            "client_session_id": "privacy-annotation",
        },
    ).json()
    annotation = client.post(
        f"/v1/timing/sessions/{session['id']}/annotations",
        headers=HEADERS,
        json={
            "mutation": mutation("annotation"),
            "input_mode": "text",
            "raw_text": "PRIVATE_ANNOTATION_TEXT",
            "audio_object_ref": "audio/private.wav",
            "occurred_at": "2026-04-28T12:10:00Z",
            "privacy_class": "private",
        },
    ).json()

    response = client.post(
        "/v1/privacy/redact",
        headers=HEADERS,
        json={
            "mutation": mutation("redact-annotation"),
            "entity_type": "temporal_context_annotation",
            "entity_id": annotation["id"],
            "reason": "user requested redaction",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert client.get(f"/v1/timing/annotations/{annotation['id']}", headers=HEADERS).json()[
        "raw_text"
    ] == "PRIVATE_ANNOTATION_TEXT"
    query_answer = seed_temporal_query_answer(store)

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    redacted = client.get(f"/v1/timing/annotations/{annotation['id']}", headers=HEADERS).json()
    assert redacted["raw_text"] is None
    assert redacted["audio_object_ref"] is None
    assert redacted["status"] == "redacted"
    assert query_answer.id not in store.temporal_query_answers
    workflow = next(iter(store.workflow_runs.values()))
    redacted_result = cast(dict[str, Any], workflow.result_ref["redacted"])
    derived = cast(dict[str, Any], redacted_result["derived_artifacts"])
    assert derived["query_answers"] == 1


def test_privacy_export_worker_records_export_manifest() -> None:
    client, store = make_client_and_store()
    client.post(
        "/v1/activities",
        headers=HEADERS,
        json={"mutation": mutation("activity"), "display_name": "Exported activity"},
    )

    response = client.post(
        "/v1/privacy/export",
        headers=HEADERS,
        json={"mutation": mutation("export"), "include_raw_context": True, "include_audio": False},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"

    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()

    assert processed == 1
    workflow = next(iter(store.workflow_runs.values()))
    assert workflow.workflow_type == "DataExportDeletionWorkflow"
    assert workflow.status == "succeeded"
    export_manifest = cast(dict[str, Any], workflow.result_ref["export_manifest"])
    assert export_manifest["activities"] == 1
    assert export_manifest["include_raw_context"] is True
