from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from test_phase2_review_profile import (
    USER_ID,
    create_activity,
    mutation,
    review_payload,
)


def _client() -> TestClient:
    return TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory()))


def _review_run(
    client: TestClient,
    activity_id: str,
    suffix: str,
    *,
    decision: str = "save_useful_run",
    model_inclusion: str = "full",
    days_ago: int = 1,
    duration_minutes: int = 30,
    with_friction: bool = False,
    sequence: int = 40,
) -> str:
    session_id = _create_completed_session_at(
        client,
        activity_id,
        suffix,
        days_ago=days_ago,
        duration_minutes=duration_minutes,
        with_friction=with_friction,
    )
    reviewed = client.post(
        f"/v1/timing/sessions/{session_id}/review",
        headers={"X-Parallax-User-Id": USER_ID},
        json=review_payload(
            f"phase7-review-{suffix}",
            decision=decision,
            model_inclusion=model_inclusion,
            sequence=sequence,
        ),
    )
    assert reviewed.status_code == 200
    return session_id


def _create_completed_session_at(
    client: TestClient,
    activity_id: str,
    suffix: str,
    *,
    days_ago: int,
    duration_minutes: int,
    with_friction: bool,
) -> str:
    completed_at = datetime.now(UTC) - timedelta(days=days_ago)
    started_at = completed_at - timedelta(minutes=duration_minutes)
    created = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"phase7-{suffix}-session", 1),
            "activity_id": activity_id,
            "client_session_id": f"phase7-{suffix}",
            "mode": "whole_task",
        },
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    events = [("start", 2, "session_started", started_at)]
    if with_friction:
        events.extend(
            [
                ("detour-start", 3, "resource_detour_started", started_at + timedelta(minutes=5)),
                ("detour-end", 4, "resource_detour_completed", started_at + timedelta(minutes=15)),
                ("interrupt-start", 5, "interruption_started", started_at + timedelta(minutes=20)),
                ("interrupt-end", 6, "interruption_completed", started_at + timedelta(minutes=25)),
            ]
        )

    for mutation_id, sequence, event_type, client_time in events:
        response = client.post(
            f"/v1/timing/sessions/{session_id}/events",
            headers={"X-Parallax-User-Id": USER_ID},
            json={
                "mutation": mutation(f"phase7-{suffix}-{mutation_id}", sequence),
                "event_type": event_type,
                "client_time": _iso(client_time),
            },
        )
        assert response.status_code == 201

    completed = client.post(
        f"/v1/timing/sessions/{session_id}/complete",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"phase7-{suffix}-complete", 20),
            "completed_at": _iso(completed_at),
        },
    )
    assert completed.status_code == 200
    return session_id


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _review_two_runs(client: TestClient, activity_id: str) -> None:
    for index in (1, 2):
        _review_run(
            client,
            activity_id,
            f"grounded-{index}",
            days_ago=index,
            duration_minutes=30,
            with_friction=True,
            sequence=40 + index,
        )


def test_temporal_query_returns_deterministic_duration_facts_with_evidence() -> None:
    client = _client()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Clean pots and pans")
    _review_two_runs(client, activity_id)

    response = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={
            "mutation": mutation("phase7-duration-query", 70),
            "question": "How long does cleaning pots and pans usually take?",
        },
    )

    assert response.status_code == 202
    answer = response.json()
    assert answer["status"] == "complete"
    assert answer["sample_size"] == 2
    assert answer["confidence"] == "low"
    assert answer["time_window"] == "last_180_days"
    assert answer["computed_facts"]["intent"] == "duration_summary"
    assert answer["computed_facts"]["activity_id"] == activity_id
    assert answer["computed_facts"]["sample_size"] == 2
    assert answer["computed_facts"]["active_p50_seconds"] == 900
    assert answer["computed_facts"]["wall_p80_seconds"] == 1800
    assert "no LLM narration" in answer["limitations"][0]
    assert len(answer["evidence"]) == 2
    assert all(item["entity_type"] == "timing_session" for item in answer["evidence"])

    fetched = client.get(f"/v1/temporal/query/{answer['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == answer


def test_temporal_query_returns_delay_facts_without_raw_quotes() -> None:
    client = _client()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")
    _review_two_runs(client, activity_id)

    response = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={
            "mutation": mutation("phase7-delay-query", 71),
            "question": "What usually delays washing pans?",
            "activity_id": activity_id,
            "include_raw_quotes": True,
        },
    )

    assert response.status_code == 202
    answer = response.json()
    categories = answer["computed_facts"]["friction_categories"]
    assert answer["computed_facts"]["intent"] == "delay_drivers"
    assert answer["sample_size"] == 2
    assert any(item["friction_category"] == "resource" for item in categories)
    assert any("Raw quotes are disabled" in item for item in answer["limitations"])
    assert all("Reviewed as useful" not in item["summary"] for item in answer["evidence"])
    assert all(item["entity_type"] == "timing_event_span" for item in answer["evidence"])


def test_duration_query_honors_metric_model_inclusion_scopes() -> None:
    client = _client()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Scoped duration")
    _review_run(client, activity_id, "duration-full", duration_minutes=30)
    _review_run(
        client,
        activity_id,
        "duration-active-only",
        decision="active_only",
        model_inclusion="active_duration_only",
        duration_minutes=60,
    )
    _review_run(
        client,
        activity_id,
        "duration-wall-only",
        decision="mark_unusual",
        model_inclusion="wall_envelope_only",
        duration_minutes=120,
    )
    _review_run(
        client,
        activity_id,
        "duration-query-only",
        decision="query_evidence_only",
        model_inclusion="query_evidence_only",
        duration_minutes=240,
    )

    response = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={
            "mutation": mutation("phase7-scoped-duration-query", 80),
            "question": "How long does scoped duration usually take?",
            "activity_id": activity_id,
        },
    )

    assert response.status_code == 202
    answer = response.json()
    facts = answer["computed_facts"]
    assert answer["sample_size"] == 2
    assert facts["sample_size"] == 2
    assert facts["active_sample_size"] == 2
    assert facts["wall_sample_size"] == 2
    assert facts["active_p80_seconds"] == 3600
    assert facts["wall_p80_seconds"] == 7200
    assert "14400" not in json.dumps(answer)
    assert any(
        "active=3600s" in item["summary"] and "wall=" not in item["summary"]
        for item in answer["evidence"]
    )
    assert any(
        "wall=7200s" in item["summary"] and "active=" not in item["summary"]
        for item in answer["evidence"]
    )


def test_delay_query_honors_friction_model_inclusion_scopes() -> None:
    client = _client()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Scoped friction")
    _review_run(client, activity_id, "friction-full", with_friction=True)
    _review_run(
        client,
        activity_id,
        "friction-active-only",
        decision="active_only",
        model_inclusion="active_duration_only",
        with_friction=True,
    )
    _review_run(
        client,
        activity_id,
        "friction-wall-only",
        decision="mark_unusual",
        model_inclusion="wall_envelope_only",
        with_friction=True,
    )
    _review_run(
        client,
        activity_id,
        "friction-patterns-only",
        decision="friction_only",
        model_inclusion="friction_patterns_only",
        with_friction=True,
    )
    _review_run(
        client,
        activity_id,
        "friction-query-only",
        decision="query_evidence_only",
        model_inclusion="query_evidence_only",
        with_friction=True,
    )

    response = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={
            "mutation": mutation("phase7-scoped-friction-query", 81),
            "question": "What usually delays scoped friction?",
            "activity_id": activity_id,
        },
    )

    assert response.status_code == 202
    answer = response.json()
    categories = answer["computed_facts"]["friction_categories"]
    resource = next(item for item in categories if item["friction_category"] == "resource")
    assert answer["sample_size"] == 3
    assert resource["event_count"] == 3


def test_temporal_query_applies_requested_window_in_memory_repository() -> None:
    client = _client()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Windowed duration")
    _review_run(client, activity_id, "window-recent", days_ago=1)
    _review_run(client, activity_id, "window-old", days_ago=20)

    response = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={
            "mutation": mutation("phase7-window-query", 82),
            "question": "How long does windowed duration usually take?",
            "activity_id": activity_id,
            "time_window": "last_7_days",
        },
    )

    assert response.status_code == 202
    answer = response.json()
    assert answer["time_window"] == "last_7_days"
    assert answer["sample_size"] == 1
    assert answer["computed_facts"]["window_days"] == 7
