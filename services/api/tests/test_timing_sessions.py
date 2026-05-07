from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory

USER_ID = "00000000-0000-0000-0000-0000000000b1"
OTHER_USER_ID = "00000000-0000-0000-0000-0000000000b2"


def make_app() -> FastAPI:
    return create_app(uow_factory=InMemoryUnitOfWorkFactory())


def mutation(
    client_mutation_id: str,
    sequence: int = 1,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-test",
        "client_timestamp": "2026-04-27T12:00:00Z",
        "idempotency_key": idempotency_key or f"idem-{client_mutation_id}",
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
    client = TestClient(make_app())
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

    other_fetch = client.get(
        f"/v1/timing/sessions/{session['id']}",
        headers={"X-Parallax-User-Id": OTHER_USER_ID},
    )
    assert other_fetch.status_code == 404

    other_append = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": OTHER_USER_ID},
        json={
            "mutation": mutation("other-user-event", 4),
            "event_type": "session_started",
            "client_time": "2026-04-27T12:30:00Z",
        },
    )
    assert other_append.status_code == 404


def test_duplicate_timing_event_replay_returns_original_event_once() -> None:
    client = TestClient(make_app())
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


def test_phase1_scripted_timer_reconstructs_wall_and_active_time() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-reconstruct"),
            "activity_id": activity_id,
            "client_session_id": "client-session-reconstruct",
            "mode": "whole_task",
        },
    ).json()

    for mutation_id, sequence, event_type, client_time in [
        ("reconstruct-start", 2, "session_started", "2026-04-27T12:00:00Z"),
        ("reconstruct-pause", 3, "session_paused", "2026-04-27T12:10:00Z"),
        ("reconstruct-resume", 4, "session_resumed", "2026-04-27T12:15:00Z"),
    ]:
        response = client.post(
            f"/v1/timing/sessions/{session['id']}/events",
            headers={"X-Parallax-User-Id": USER_ID},
            json={
                "mutation": mutation(mutation_id, sequence),
                "event_type": event_type,
                "client_time": client_time,
            },
        )
        assert response.status_code == 201

    completed = client.post(
        f"/v1/timing/sessions/{session['id']}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("reconstruct-complete", 5),
            "completed_at": "2026-04-27T12:20:00Z",
        },
    )

    assert completed.status_code == 200
    completed_session = completed.json()
    assert completed_session["status"] == "completed_unreviewed"
    assert completed_session["wall_seconds"] == 1200
    assert completed_session["active_seconds"] == 900
    assert completed_session["needs_timeline_recompute"] is False


def test_completion_derives_spans_before_review() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-complete-spans"),
            "activity_id": activity_id,
            "client_session_id": "client-session-complete-spans",
            "mode": "whole_task",
        },
    ).json()

    for mutation_id, sequence, event_type, client_time in [
        ("complete-spans-start", 2, "session_started", "2026-04-27T12:00:00Z"),
        (
            "complete-spans-detour",
            3,
            "resource_detour_started",
            "2026-04-27T12:05:00Z",
        ),
    ]:
        response = client.post(
            f"/v1/timing/sessions/{session['id']}/events",
            headers={"X-Parallax-User-Id": USER_ID},
            json={
                "mutation": mutation(mutation_id, sequence),
                "event_type": event_type,
                "client_time": client_time,
            },
        )
        assert response.status_code == 201

    completed = client.post(
        f"/v1/timing/sessions/{session['id']}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("complete-spans-complete", 4),
            "completed_at": "2026-04-27T12:20:00Z",
        },
    )

    assert completed.status_code == 200
    completed_session = completed.json()
    assert completed_session["status"] == "completed_unreviewed"
    assert completed_session["wall_seconds"] == 1200
    assert completed_session["active_seconds"] == 300
    assert completed_session["detour_seconds"] == 900

    spans_by_type = {span["span_type"]: span for span in completed_session["spans"]}
    assert spans_by_type["active_work"]["duration_seconds"] == 300
    assert spans_by_type["active_work"]["count_in_active_time"] is True
    assert spans_by_type["resource_detour"]["duration_seconds"] == 900
    assert spans_by_type["resource_detour"]["count_policy"] == "wall_only"
    assert spans_by_type["resource_detour"]["count_in_active_time"] is False


def test_duplicate_timing_event_replay_uses_idempotency_key() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-idem"),
            "activity_id": activity_id,
            "client_session_id": "client-session-idem",
            "mode": "whole_task",
        },
    ).json()
    payload = {
        "event_type": "session_started",
        "client_time": "2026-04-27T12:05:00Z",
    }

    responses = [
        client.post(
            f"/v1/timing/sessions/{session['id']}/events",
            headers={"X-Parallax-User-Id": USER_ID},
            json={
                **payload,
                "mutation": mutation(f"event-idem-{index}", 2 + index, "idem-shared-event"),
            },
        )
        for index in range(3)
    ]

    assert [response.status_code for response in responses] == [201, 201, 201]
    assert responses[1].json() == responses[0].json()
    assert responses[2].json() == responses[0].json()

    fetched = client.get(
        f"/v1/timing/sessions/{session['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert [event["id"] for event in fetched.json()["events"]] == [responses[0].json()["id"]]


def test_out_of_order_and_impossible_events_are_accepted_and_flag_recompute() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-out-of-order"),
            "activity_id": activity_id,
            "client_session_id": "client-session-out-of-order",
            "mode": "whole_task",
        },
    ).json()

    pause = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("event-impossible-pause", 3),
            "event_type": "session_paused",
            "client_time": "2026-04-27T12:10:00Z",
        },
    )
    late_start = client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("event-late-start", 2),
            "event_type": "session_started",
            "client_time": "2026-04-27T12:00:00Z",
        },
    )

    assert pause.status_code == 201
    assert late_start.status_code == 201
    fetched = client.get(
        f"/v1/timing/sessions/{session['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert [event["event_type"] for event in fetched["events"]] == [
        "session_started",
        "session_paused",
    ]
    assert fetched["needs_timeline_recompute"] is True


def test_duplicate_completion_with_distinct_mutations_is_flagged_for_recompute() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("session-duplicate-complete"),
            "activity_id": activity_id,
            "client_session_id": "client-session-duplicate-complete",
            "mode": "whole_task",
        },
    ).json()
    client.post(
        f"/v1/timing/sessions/{session['id']}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("duplicate-complete-start", 2),
            "event_type": "session_started",
            "client_time": "2026-04-27T12:00:00Z",
        },
    )

    first = client.post(
        f"/v1/timing/sessions/{session['id']}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("duplicate-complete-first", 3),
            "completed_at": "2026-04-27T12:10:00Z",
        },
    )
    second = client.post(
        f"/v1/timing/sessions/{session['id']}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("duplicate-complete-second", 4),
            "completed_at": "2026-04-27T12:20:00Z",
        },
    )
    fetched = client.get(
        f"/v1/timing/sessions/{session['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert [event["event_type"] for event in fetched["events"]] == [
        "session_started",
        "session_completed",
        "session_completed",
    ]
    assert fetched["needs_timeline_recompute"] is True
