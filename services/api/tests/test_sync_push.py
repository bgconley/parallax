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


def create_completed_session(client: TestClient) -> tuple[str, str]:
    activity = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("sync-review-activity"), "display_name": "Sync review"},
    )
    assert activity.status_code == 201
    activity_id = activity.json()["id"]
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-review-session"),
            "activity_id": activity_id,
            "client_session_id": "sync-review-session",
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]
    started = client.post(
        f"/v1/timing/sessions/{session_id}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-review-start"),
            "event_type": "session_started",
            "client_time": "2026-04-28T12:00:00Z",
        },
    )
    assert started.status_code == 201
    completed = client.post(
        f"/v1/timing/sessions/{session_id}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-review-complete"),
            "completed_at": "2026-04-28T12:10:00Z",
        },
    )
    assert completed.status_code == 200
    return activity_id, session_id


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
                    "operation": "create_activity",
                    "path": "/v1/activities",
                    "body": {
                        "mutation": mutation("nested-activity"),
                        "display_name": "Synced validation activity",
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


def test_sync_push_applies_supported_create_activity_operation() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-create-activity"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "create_activity",
                    "path": "/v1/activities",
                    "body": {
                        "mutation": mutation("nested-create-activity"),
                        "display_name": "Synced activity",
                    },
                }
            ],
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    listed = client.get("/v1/activities", headers={"X-Parallax-User-Id": USER_ID})
    assert listed.status_code == 200
    assert [activity["display_name"] for activity in listed.json()] == ["Synced activity"]


def test_sync_push_applies_supported_review_operation() -> None:
    client = TestClient(make_app())
    activity_id, session_id = create_completed_session(client)

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-review"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "review_timing_session",
                    "path": f"/v1/timing/sessions/{session_id}/review",
                    "body": {
                        "mutation": mutation("nested-review-session"),
                        "decision": "save_useful_run",
                        "model_inclusion": "full",
                        "scopes": ["active_duration", "wall_duration"],
                    },
                }
            ],
        },
    )

    assert response.status_code == 202
    fetched = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert fetched["status"] == "reviewed"
    profile = client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert profile["latest_stats"]["sample_size"] == 1


def test_sync_push_rejects_invalid_endpoint_payload() -> None:
    client = TestClient(make_app())

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-push-invalid-endpoint-payload"),
            "client_device_id": "ios-test",
            "mutations": [
                {
                    "operation": "create_activity",
                    "path": "/v1/activities",
                    "body": {"mutation": mutation("nested-invalid-endpoint-payload")},
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_sync_operation_payload"


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
