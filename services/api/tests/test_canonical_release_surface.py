from __future__ import annotations

from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from test_phase4_structured_extraction import USER_ID, create_activity, mutation


def test_release_surface_endpoints_perform_minimal_canonical_behaviors() -> None:
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory()))
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Release surface")
    other_activity_id = create_activity(client, "Release related")

    alias = client.post(
        f"/v1/activities/{activity_id}/aliases",
        headers=headers,
        json={
            "mutation": mutation("release-alias", 10),
            "alias_text": "release alias",
            "user_confirmed": True,
        },
    )
    assert alias.status_code == 201
    assert alias.json()["normalized_alias"] == "release-alias"

    relationship = client.post(
        f"/v1/activities/{activity_id}/relationships",
        headers=headers,
        json={
            "mutation": mutation("release-relationship", 11),
            "to_activity_id": other_activity_id,
            "kind": "related_to",
        },
    )
    assert relationship.status_code == 201
    assert relationship.json()["to_activity_id"] == other_activity_id

    checkpoints = client.put(
        f"/v1/activities/{activity_id}/checkpoints",
        headers=headers,
        json={
            "mutation": mutation("release-checkpoints", 12),
            "checkpoints": [{"label": "Prep", "sequence_order": 1}],
        },
    )
    assert checkpoints.status_code == 200
    listed_checkpoints = client.get(
        f"/v1/activities/{activity_id}/checkpoints",
        headers=headers,
    )
    assert listed_checkpoints.json()[0]["label"] == "Prep"

    preflight = client.post(
        f"/v1/activities/{activity_id}/preflight-checks",
        headers=headers,
        json={
            "mutation": mutation("release-preflight", 13),
            "check_text": "Stage supplies.",
            "source": "user_created",
        },
    )
    assert preflight.status_code == 201
    listed_preflight = client.get(
        f"/v1/activities/{activity_id}/preflight-checks",
        headers=headers,
    )
    assert listed_preflight.json()[0]["check_text"] == "Stage supplies."

    settings = client.get("/v1/privacy/settings", headers=headers)
    assert settings.status_code == 200
    updated_settings = {
        **settings.json(),
        "retain_audio": True,
    }
    privacy_update = client.put(
        "/v1/privacy/settings",
        headers=headers,
        json={"mutation": mutation("release-privacy-settings", 14), "settings": updated_settings},
    )
    assert privacy_update.status_code == 200
    assert privacy_update.json()["retain_audio"] is True

    export = client.post(
        "/v1/privacy/export",
        headers=headers,
        json={"mutation": mutation("release-export", 15)},
    )
    assert export.status_code == 202
    assert export.json()["request_type"] == "export"

    prediction = client.post(
        "/v1/temporal/predictions",
        headers=headers,
        json={
            "mutation": mutation("release-prediction", 16),
            "activity_id": activity_id,
            "prediction_type": "duration_range",
        },
    )
    assert prediction.status_code == 201
    assert prediction.json()["basis"] == "insufficient_data"

    query = client.post(
        "/v1/temporal/query",
        headers=headers,
        json={"mutation": mutation("release-query", 17), "question": "How long does this take?"},
    )
    assert query.status_code == 202
    fetched_query = client.get(f"/v1/temporal/query/{query.json()['id']}", headers=headers)
    assert fetched_query.status_code == 200

    sync_pull = client.get("/v1/sync/pull", headers=headers)
    assert sync_pull.status_code == 200
    assert sync_pull.json()["changes"] == []
