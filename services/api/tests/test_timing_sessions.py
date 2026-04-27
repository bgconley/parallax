from fastapi.testclient import TestClient
from parallax_api.main import create_app

USER_ID = "00000000-0000-0000-0000-0000000000b1"


def mutation(client_mutation_id: str, sequence: int = 1) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-test",
        "client_timestamp": "2026-04-27T12:00:00Z",
        "idempotency_key": f"idem-{client_mutation_id}",
        "client_sequence": sequence,
    }


def create_activity(client: TestClient) -> str:
    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("activity"), "display_name": "Clean kitchen"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_timing_session_accepts_append_safe_events_and_completion() -> None:
    client = TestClient(create_app())
    activity_id = create_activity(client)

    created = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session"),
            "activity_id": activity_id,
            "client_session_id": "client-session-1",
            "mode": "whole_task",
        },
    )
    assert created.status_code == 201
    session = created.json()
    assert session["status"] == "draft"
    assert session["model_inclusion"] == "not_reviewed"

    started = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("event-start", 2),
            "event_type": "session_started",
            "client_time": "2026-04-27T12:05:00Z",
            "timer_elapsed_seconds": 0,
            "timer_active_seconds": 0,
            "payload": {},
        },
    )
    assert started.status_code == 201
    assert started.json()["event_type"] == "session_started"

    completed = client.post(
        f"/v1/timing/sessions/{session['id']}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("complete", 3),
            "completed_at": "2026-04-27T12:25:00Z",
            "timer_elapsed_seconds": 1200,
            "timer_active_seconds": 900,
            "payload": {"source": "test"},
        },
    )
    assert completed.status_code == 200
    completed_session = completed.json()
    assert completed_session["status"] == "completed_unreviewed"
    assert completed_session["wall_seconds"] == 1200
    assert completed_session["active_seconds"] == 900
    assert [event["event_type"] for event in completed_session["events"]] == [
        "session_started",
        "session_completed",
    ]


def test_duplicate_timing_event_replay_returns_original_event_once() -> None:
    client = TestClient(create_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-replay"),
            "activity_id": activity_id,
            "client_session_id": "client-session-replay",
            "mode": "whole_task",
        },
    ).json()
    event_payload = {
        "mutation": mutation("event-replay", 2),
        "event_type": "session_started",
        "client_time": "2026-04-27T12:05:00Z",
        "timer_elapsed_seconds": 0,
        "timer_active_seconds": 0,
        "payload": {},
    }

    first = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json=event_payload,
    )
    second = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json=event_payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()

    fetched = client.get(
        f"/v1/timing/sessions/{session['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert [event["id"] for event in fetched.json()["events"]] == [first.json()["id"]]
