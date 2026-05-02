from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_api.schemas.extraction import ExtractedContextEvent
from test_phase4_structured_extraction import (
    USER_ID,
    create_activity,
    create_annotation,
    create_started_session,
    extract_annotation_candidate,
    mutation,
)


def _client_and_store() -> tuple[TestClient, InMemoryStore]:
    store = InMemoryStore()
    client = TestClient(create_app(uow_factory=InMemoryUnitOfWorkFactory(store)))
    return client, store


def test_suggested_alias_requires_user_decision_before_resolver_uses_it() -> None:
    client, _store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")

    suggested = client.post(
        f"/v1/activities/{activity_id}/aliases",
        headers=headers,
        json={
            "mutation": mutation("phase6-alias-suggested", 10),
            "alias_text": "scrub pans",
            "user_confirmed": False,
        },
    )
    assert suggested.status_code == 201
    alias_id = suggested.json()["id"]

    unresolved = client.post(
        "/v1/activities/resolve",
        headers=headers,
        json={"query": "scrub pans", "limit": 5},
    )
    assert unresolved.status_code == 200
    assert unresolved.json()["recommended_activity_id"] is None

    accepted = client.post(
        f"/v1/activities/{activity_id}/aliases/{alias_id}/decision",
        headers=headers,
        json={
            "mutation": mutation("phase6-alias-accept", 11),
            "decision": "accept",
            "reason": "User confirmed this is the same activity.",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["user_confirmed"] is True
    assert accepted.json()["rejected"] is False

    resolved = client.post(
        "/v1/activities/resolve",
        headers=headers,
        json={"query": "scrub pans", "limit": 5},
    )
    assert resolved.status_code == 200
    assert resolved.json()["recommended_activity_id"] == activity_id
    assert resolved.json()["candidates"][0]["match_type"] == "alias"

    rejected = client.post(
        f"/v1/activities/{activity_id}/aliases",
        headers=headers,
        json={
            "mutation": mutation("phase6-alias-rejected", 12),
            "alias_text": "wash car",
            "user_confirmed": False,
        },
    )
    assert rejected.status_code == 201
    rejected_alias_id = rejected.json()["id"]
    decision = client.post(
        f"/v1/activities/{activity_id}/aliases/{rejected_alias_id}/decision",
        headers=headers,
        json={
            "mutation": mutation("phase6-alias-reject", 13),
            "decision": "reject",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["rejected"] is True

    listed = client.get(f"/v1/activities/{activity_id}/aliases", headers=headers)
    assert listed.status_code == 200
    assert [item["alias_text"] for item in listed.json()] == ["scrub pans", "wash car"]


def test_soft_merge_preserves_source_history_and_returns_audit_record() -> None:
    client, _store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    source_activity_id = create_activity(client, "Clean skillet")
    target_activity_id = create_activity(client, "Wash pans")
    session_id = create_started_session(client, source_activity_id, "phase6-merge")

    preview = client.post(
        f"/v1/activities/{source_activity_id}/merge-preview",
        headers=headers,
        json={"target_activity_id": target_activity_id},
    )
    assert preview.status_code == 200
    assert preview.json()["source_activity_id"] == source_activity_id
    assert preview.json()["target_activity_id"] == target_activity_id
    assert preview.json()["affected_session_count"] == 1
    assert preview.json()["history_preservation"] == "source_activity_soft_merged"

    merged = client.post(
        f"/v1/activities/{source_activity_id}/merge",
        headers=headers,
        json={
            "mutation": mutation("phase6-merge", 14),
            "target_activity_id": target_activity_id,
            "reason": "User confirmed duplicate activity.",
        },
    )
    assert merged.status_code == 200
    assert merged.json()["change_type"] == "merge"
    assert merged.json()["audit_id"]
    assert merged.json()["affected_session_count"] == 1

    source = client.get(f"/v1/activities/{source_activity_id}", headers=headers)
    assert source.status_code == 200
    assert source.json()["status"] == "merged"
    assert source.json()["merged_into_activity_id"] == target_activity_id

    session = client.get(f"/v1/timing/sessions/{session_id}", headers=headers)
    assert session.status_code == 200
    assert session.json()["activity_id"] == source_activity_id

    relationships = client.get(
        f"/v1/activities/{source_activity_id}/relationships",
        headers=headers,
    )
    assert relationships.status_code == 200
    assert relationships.json()[0]["kind"] == "same_as"
    assert relationships.json()[0]["to_activity_id"] == target_activity_id


def test_repeated_resource_detours_create_dependency_and_preflight_suggestion() -> None:
    client, _store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")
    confirmed_event_ids: set[str] = set()

    for suffix in ("one", "two"):
        session_id = create_started_session(client, activity_id, f"phase6-sponge-{suffix}")
        annotation = create_annotation(
            client,
            session_id,
            "I had to stop and find the sponge, which took about 10 minutes.",
            mutation_id=f"phase6-sponge-note-{suffix}",
        )
        extracted = extract_annotation_candidate(
            client,
            _store,
            str(annotation["id"]),
            mutation_id=f"phase6-sponge-extract-{suffix}",
        )
        confirmed = client.post(
            f"/v1/timing/extracted-events/{extracted['id']}/confirm",
            headers=headers,
            json={
                "mutation": mutation(f"phase6-sponge-confirm-{suffix}", 20),
                "confirmation_state": "confirmed",
            },
        )
        assert confirmed.status_code == 200
        confirmed_event_ids.add(str(extracted["id"]))

    assert len(confirmed_event_ids) == 2

    dependencies = client.get(
        f"/v1/activities/{activity_id}/resource-dependencies",
        headers=headers,
    )
    assert dependencies.status_code == 200
    assert dependencies.json()[0]["resource_name"] == "sponge"
    assert dependencies.json()[0]["failure_count"] == 2
    assert dependencies.json()[0]["suggest_precheck"] is True

    checks = client.get(f"/v1/activities/{activity_id}/preflight-checks", headers=headers)
    assert checks.status_code == 200
    resource_check = next(
        check for check in checks.json() if check["source"] == "resource_dependency"
    )
    assert resource_check["state"] == "suggested"
    assert resource_check["failure_count"] == 2
    assert resource_check["check_text"] == "Check sponge/scrubber before washing pans."


def test_resource_dependency_counts_each_extracted_event_once() -> None:
    client, _store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")
    session_id = create_started_session(client, activity_id, "phase6-duplicate-sponge")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="phase6-duplicate-sponge-note",
    )
    extracted = extract_annotation_candidate(
        client,
        _store,
        str(annotation["id"]),
        mutation_id="phase6-duplicate-sponge-extract",
    )

    for sequence in (1, 2):
        confirmed = client.post(
            f"/v1/timing/extracted-events/{extracted['id']}/confirm",
            headers=headers,
            json={
                "mutation": mutation(f"phase6-duplicate-confirm-{sequence}", 50 + sequence),
                "confirmation_state": "confirmed",
            },
        )
        assert confirmed.status_code == 200

    dependencies = client.get(
        f"/v1/activities/{activity_id}/resource-dependencies",
        headers=headers,
    )
    assert dependencies.status_code == 200
    assert dependencies.json()[0]["resource_name"] == "sponge"
    assert dependencies.json()[0]["failure_count"] == 1
    assert dependencies.json()[0]["suggest_precheck"] is False

    checks = client.get(f"/v1/activities/{activity_id}/preflight-checks", headers=headers)
    assert checks.status_code == 200
    assert [
        check for check in checks.json() if check["source"] == "resource_dependency"
    ] == []


def test_resource_dependency_aggregates_resource_evidence_without_preflight_text() -> None:
    client, store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")
    session_id = create_started_session(client, activity_id, "phase6-resource-only")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and look for the pan scraper.",
        mutation_id="phase6-resource-only-note",
    )
    event_id = uuid4()
    store.extracted_events[event_id] = ExtractedContextEvent(
        id=event_id,
        user_id=UUID(USER_ID),
        annotation_id=UUID(str(annotation["id"])),
        session_id=UUID(session_id),
        span_type="resource_detour",
        friction_category="resource",
        resource_name="pan scraper",
        duration_seconds=420,
        count_policy="wall_only",
        count_in_wall_time=True,
        count_in_active_time=False,
        model_update_scopes=["friction_patterns"],
        suggested_preflight_text=None,
        confidence=0.91,
        confirmation_state="needs_confirmation",
        sensitive_data_detected=False,
        source_json={"evidence": "resource_only_test"},
        user_correction_json={},
    )

    confirmed = client.post(
        f"/v1/timing/extracted-events/{event_id}/confirm",
        headers=headers,
        json={
            "mutation": mutation("phase6-resource-only-confirm", 60),
            "confirmation_state": "confirmed",
        },
    )
    assert confirmed.status_code == 200

    dependencies = client.get(
        f"/v1/activities/{activity_id}/resource-dependencies",
        headers=headers,
    )
    assert dependencies.status_code == 200
    assert dependencies.json()[0]["resource_name"] == "pan scraper"
    assert dependencies.json()[0]["failure_count"] == 1

    checks = client.get(f"/v1/activities/{activity_id}/preflight-checks", headers=headers)
    assert checks.status_code == 200
    assert [
        check for check in checks.json() if check["source"] == "model_suggested"
    ] == []


def test_preflight_checks_can_be_accepted_hidden_snoozed_and_retired() -> None:
    client, _store = _client_and_store()
    headers = {"X-Parallax-User-Id": USER_ID}
    activity_id = create_activity(client, "Wash pans")
    check_ids: list[str] = []

    for index, text in enumerate(("A", "B", "C", "D"), start=1):
        response = client.post(
            f"/v1/activities/{activity_id}/preflight-checks",
            headers=headers,
            json={
                "mutation": mutation(f"phase6-preflight-{text}", 30 + index),
                "check_text": f"Check {text}.",
                "source": "model_suggested",
            },
        )
        assert response.status_code == 201
        assert response.json()["state"] == "suggested"
        check_ids.append(response.json()["id"])

    expected = [
        ("accept", "active", None),
        ("hide", "hidden", None),
        ("snooze", "snoozed", "2026-05-02T12:00:00Z"),
        ("retire", "retired", None),
    ]
    for index, (decision, state, snoozed_until) in enumerate(expected):
        body: dict[str, object] = {
            "mutation": mutation(f"phase6-preflight-{decision}", 40 + index),
            "decision": decision,
            "reason": f"phase6 {decision}",
        }
        if snoozed_until is not None:
            body["snoozed_until"] = snoozed_until
        decided = client.post(
            f"/v1/activities/{activity_id}/preflight-checks/{check_ids[index]}/decision",
            headers=headers,
            json=body,
        )
        assert decided.status_code == 200
        assert decided.json()["state"] == state
        assert decided.json()["last_decided_at"]
        if state == "snoozed":
            assert datetime.fromisoformat(
                decided.json()["snoozed_until"].replace("Z", "+00:00")
            ) == datetime(2026, 5, 2, 12, tzinfo=UTC)
