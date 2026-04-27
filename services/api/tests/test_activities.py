from uuid import UUID

from fastapi.testclient import TestClient
from parallax_api.main import create_app

USER_ID = "00000000-0000-0000-0000-0000000000a1"


def mutation(client_mutation_id: str) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "mac-test",
        "client_timestamp": "2026-04-27T12:00:00Z",
        "idempotency_key": f"idem-{client_mutation_id}",
        "client_sequence": 1,
    }


def test_create_list_and_get_activity_are_user_scoped() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("activity-1"),
            "display_name": "Clean kitchen",
            "default_timing_mode": "whole_task",
            "privacy_class": "normal",
        },
    )

    assert created.status_code == 201
    activity = created.json()
    assert UUID(activity["id"])
    assert activity["user_id"] == USER_ID
    assert activity["display_name"] == "Clean kitchen"
    assert activity["canonical_key"] == "clean-kitchen"
    assert activity["status"] == "active"

    listed = client.get("/v1/activities", headers={"X-Parallax-User-Id": USER_ID})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [activity["id"]]

    fetched = client.get(
        f"/v1/activities/{activity['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == activity["id"]


def test_duplicate_activity_mutation_replays_original_result() -> None:
    client = TestClient(create_app())
    payload = {
        "mutation": mutation("activity-replay"),
        "display_name": "Wash pans",
        "default_timing_mode": "whole_task",
        "privacy_class": "normal",
    }

    first = client.post("/v1/activities", headers={"X-Parallax-User-Id": USER_ID}, json=payload)
    second = client.post("/v1/activities", headers={"X-Parallax-User-Id": USER_ID}, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert len(client.get("/v1/activities", headers={"X-Parallax-User-Id": USER_ID}).json()) == 1


def test_activity_resolver_is_read_only() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/activities/resolve",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"query": "Clean kitchen", "limit": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "candidates": [
            {
                "activity": None,
                "display_name": "Clean kitchen",
                "confidence": 0.0,
                "match_type": "no_match",
                "evidence": {"reason": "no matching activity"},
            }
        ],
        "recommended_activity_id": None,
        "requires_confirmation": True,
    }
    assert client.get("/v1/activities", headers={"X-Parallax-User-Id": USER_ID}).json() == []
