from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory

USER_ID = "00000000-0000-0000-0000-0000000002b1"


def make_app() -> FastAPI:
    return create_app(uow_factory=InMemoryUnitOfWorkFactory())


def mutation(
    client_mutation_id: str,
    sequence: int = 1,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-phase2-test",
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": idempotency_key or f"idem-{client_mutation_id}",
        "client_sequence": sequence,
    }


def create_activity(client: TestClient, name: str = "Clean kitchen") -> str:
    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation(f"activity-{name}"), "display_name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_completed_session(
    client: TestClient,
    activity_id: str,
    *,
    client_session_id: str,
    mutation_prefix: str,
    with_friction: bool = False,
) -> str:
    created = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"{mutation_prefix}-session", 1),
            "activity_id": activity_id,
            "client_session_id": client_session_id,
            "mode": "whole_task",
        },
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    events = [("start", 2, "session_started", "2026-04-28T12:00:00Z")]
    if with_friction:
        events.extend(
            [
                ("detour-start", 3, "resource_detour_started", "2026-04-28T12:05:00Z"),
                ("detour-end", 4, "resource_detour_completed", "2026-04-28T12:15:00Z"),
                ("interrupt-start", 5, "interruption_started", "2026-04-28T12:20:00Z"),
                ("interrupt-end", 6, "interruption_completed", "2026-04-28T12:25:00Z"),
            ]
        )

    for mutation_id, sequence, event_type, client_time in events:
        response = client.post(
            f"/v1/timing/sessions/{session_id}/events",
            headers={"X-Parallax-User-Id": USER_ID},
            json={
                "mutation": mutation(f"{mutation_prefix}-{mutation_id}", sequence),
                "event_type": event_type,
                "client_time": client_time,
            },
        )
        assert response.status_code == 201

    completed = client.post(
        f"/v1/timing/sessions/{session_id}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"{mutation_prefix}-complete", 20),
            "completed_at": "2026-04-28T12:30:00Z",
        },
    )
    assert completed.status_code == 200
    return session_id


def review_payload(
    mutation_id: str,
    *,
    decision: str = "save_useful_run",
    model_inclusion: str = "full",
    sequence: int = 30,
) -> dict[str, object]:
    return {
        "mutation": mutation(mutation_id, sequence),
        "decision": decision,
        "model_inclusion": model_inclusion,
        "scopes": ["active_duration", "wall_duration", "friction_patterns"],
        "user_note": "Reviewed as useful.",
    }


def test_review_derives_wall_only_friction_spans_and_updates_profile() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client)
    session_id = create_completed_session(
        client,
        activity_id,
        client_session_id="phase2-friction",
        mutation_prefix="friction",
        with_friction=True,
    )

    reviewed = client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload("review-friction"),
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["decision"] == "save_useful_run"
    assert reviewed.json()["model_inclusion"] == "full"

    fetched = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert fetched["status"] == "reviewed"
    assert fetched["model_inclusion"] == "full"
    assert fetched["wall_seconds"] == 1800
    assert fetched["active_seconds"] == 900
    assert fetched["detour_seconds"] == 600
    assert fetched["interruption_seconds"] == 300
    review_events = [
        event for event in fetched["events"] if event["event_type"] == "review_saved"
    ]
    assert len(review_events) == 1
    assert review_events[0]["timer_elapsed_seconds"] == 1800
    assert review_events[0]["timer_active_seconds"] == 900
    assert review_events[0]["payload"]["decision"] == "save_useful_run"
    assert review_events[0]["payload"]["model_inclusion"] == "full"

    spans_by_type = {span["span_type"]: span for span in fetched["spans"]}
    assert spans_by_type["resource_detour"]["count_policy"] == "wall_only"
    assert spans_by_type["resource_detour"]["count_in_wall_time"] is True
    assert spans_by_type["resource_detour"]["count_in_active_time"] is False
    assert spans_by_type["interruption"]["count_policy"] == "wall_only"
    assert spans_by_type["interruption"]["count_in_active_time"] is False

    profile = client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert profile.status_code == 200
    body = profile.json()
    assert body["latest_stats"]["sample_size"] == 1
    assert body["latest_stats"]["confidence"] == "very_low"
    assert body["latest_stats"]["active_p50_seconds"] == 900
    assert body["latest_stats"]["active_p80_seconds"] == 900
    assert body["latest_stats"]["wall_p50_seconds"] == 1800
    assert body["latest_stats"]["wall_p80_seconds"] == 1800
    assert body["recent_sessions"][0]["id"] == session_id
    assert "Only 1 reviewed run is available." in body["limitations"]


@pytest.mark.parametrize(
    ("decision", "model_inclusion", "expected_status", "expected_run_quality"),
    [
        ("save_useful_run", "full", "reviewed", "typical"),
        ("mark_unusual", "friction_patterns_only", "reviewed", "useful_unusual"),
        ("save_partial", "active_duration_only", "reviewed", "partial"),
        ("active_only", "active_duration_only", "reviewed", "typical"),
        ("friction_only", "friction_patterns_only", "reviewed", "typical"),
        ("query_evidence_only", "query_evidence_only", "reviewed", "do_not_train"),
        ("discard_timing_keep_note", "exclude", "discarded", "do_not_train"),
        ("discard_all", "exclude", "discarded", "bad_timer"),
    ],
)
def test_review_decisions_update_session_model_inclusion(
    decision: str,
    model_inclusion: str,
    expected_status: str,
    expected_run_quality: str,
) -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client, name=f"Decision {decision}")
    session_id = create_completed_session(
        client,
        activity_id,
        client_session_id=f"phase2-{decision}",
        mutation_prefix=decision,
    )
    endpoint = "discard" if decision.startswith("discard_") else "review"

    response = client.post(
        f"/v1/timing/sessions/{session_id}/{endpoint}",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload(
            f"review-{decision}",
            decision=decision,
            model_inclusion=model_inclusion,
        ),
    )

    assert response.status_code == 200
    assert response.json()["model_inclusion"] == model_inclusion
    fetched = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert fetched["status"] == expected_status
    assert fetched["model_inclusion"] == model_inclusion
    assert fetched["run_quality"] == expected_run_quality


def test_duplicate_review_replay_does_not_double_count_profile_sample() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client, name="Duplicate review")
    session_id = create_completed_session(
        client,
        activity_id,
        client_session_id="phase2-duplicate-review",
        mutation_prefix="duplicate-review",
    )
    payload = review_payload("review-duplicate")

    first = client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers={"X-Parallax-User-Id": USER_ID},
        json=payload,
    )
    second = client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers={"X-Parallax-User-Id": USER_ID},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    profile = client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert profile["latest_stats"]["sample_size"] == 1
    fetched = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert [event["event_type"] for event in fetched["events"]].count("review_saved") == 1


def test_discard_all_marks_bad_timer_and_excludes_activity_profile_baseline() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client, name="Forgot stop")
    session_id = create_completed_session(
        client,
        activity_id,
        client_session_id="phase2-bad-timer",
        mutation_prefix="bad-timer",
    )

    discarded = client.post(
        f"/v1/timing/sessions/{session_id}/discard",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload(
            "discard-bad-timer",
            decision="discard_all",
            model_inclusion="exclude",
        ),
    )

    assert discarded.status_code == 200
    fetched = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert fetched["status"] == "discarded"
    assert fetched["run_quality"] == "bad_timer"
    assert fetched["model_inclusion"] == "exclude"

    profile = client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert profile.status_code == 200
    assert profile.json()["latest_stats"] is None
    assert "No reviewed runs are eligible for duration stats." in profile.json()["limitations"]


def test_discard_after_review_removes_session_from_profile_baseline() -> None:
    client = TestClient(make_app())
    activity_id = create_activity(client, name="Review then discard")
    session_id = create_completed_session(
        client,
        activity_id,
        client_session_id="phase2-review-then-discard",
        mutation_prefix="review-then-discard",
    )
    reviewed = client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload("review-before-discard"),
    )
    assert reviewed.status_code == 200
    assert client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()["latest_stats"]["sample_size"] == 1

    discarded = client.post(
        f"/v1/timing/sessions/{session_id}/discard",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload(
            "discard-after-review",
            decision="discard_all",
            model_inclusion="exclude",
            sequence=31,
        ),
    )

    assert discarded.status_code == 200
    profile = client.get(
        f"/v1/activities/{activity_id}/profile",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert profile["latest_stats"] is None
    assert "No reviewed runs are eligible for duration stats." in profile["limitations"]
