from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory

USER_ID = "00000000-0000-0000-0000-0000000000c1"


def make_app() -> FastAPI:
    return create_app(uow_factory=InMemoryUnitOfWorkFactory())


def mutation(client_mutation_id: str) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-test",
        "client_timestamp": "2026-04-27T12:00:00Z",
        "idempotency_key": f"idem-{client_mutation_id}",
        "client_sequence": 1,
    }


def test_sync_push_validates_top_level_and_nested_mutation_envelopes() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "append_timing_event",
                    "path": "/v1/timing/sessions/00000000-0000-0000-0000-000000000501/events",
                    "body": {
                        "mutation": mutation("nested-event"),
                        "event_type": "session_started",
                        "client_time": "2026-04-27T12:00:00Z",
                    },
                }
            ],
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert response.json()["operation_count"] == 1

    replay = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push"),
            "client_device_id": "ios-test",
            "mutations": [],
        },
    )
    assert replay.status_code == 202
    assert replay.json() == response.json()


def test_sync_push_rejects_invalid_nested_mutation_envelope() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-invalid"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "append_timing_event",
                    "path": "/v1/timing/sessions/00000000-0000-0000-0000-000000000501/events",
                    "body": {
                        "mutation": {
                            "client_mutation_id": "nested-invalid",
                            "client_device_id": "ios-test",
                            "client_timestamp": "2026-04-27T12:00:00Z",
                        },
                        "event_type": "session_started",
                        "client_time": "2026-04-27T12:00:00Z",
                    },
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_sync_operation"


def test_sync_push_rejects_known_mutating_operation_without_nested_mutation() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-missing-nested"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "append_timing_event",
                    "path": "/v1/timing/sessions/00000000-0000-0000-0000-000000000501/events",
                    "body": {
                        "event_type": "session_started",
                        "client_time": "2026-04-27T12:00:00Z",
                    },
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_sync_operation"


def test_sync_push_rejects_unknown_operation() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-unknown-op"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "future_phase_operation",
                    "path": "/v1/future",
                    "body": {"mutation": mutation("nested-future")},
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "unsupported_sync_operation"
