from __future__ import annotations

import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_worker.workflow_worker import WorkflowWorker

USER_ID = "00000000-0000-0000-0000-0000000004d1"


def make_app_and_store() -> tuple[FastAPI, InMemoryStore]:
    store = InMemoryStore()
    return create_app(uow_factory=InMemoryUnitOfWorkFactory(store)), store


def mutation(client_mutation_id: str, sequence: int = 1) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-phase4-test",
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"idem-{client_mutation_id}",
        "client_sequence": sequence,
    }


def create_activity(client: TestClient, name: str = "Phase 4 kitchen") -> str:
    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation(f"activity-{name}"), "display_name": name},
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def create_started_session(client: TestClient, activity_id: str, suffix: str = "main") -> str:
    session = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"session-{suffix}", 2),
            "activity_id": activity_id,
            "client_session_id": f"phase4-{suffix}",
            "mode": "whole_task",
        },
    )
    assert session.status_code == 201
    session_id = str(session.json()["id"])
    started = client.post(
        f"/v1/timing/sessions/{session_id}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"start-{suffix}", 3),
            "event_type": "session_started",
            "client_time": "2026-04-28T12:00:00Z",
        },
    )
    assert started.status_code == 201
    return session_id


def create_annotation(
    client: TestClient,
    session_id: str,
    raw_text: str,
    *,
    privacy_class: str = "normal",
    mutation_id: str = "annotation",
) -> dict[str, object]:
    response = client.post(
        f"/v1/timing/sessions/{session_id}/annotations",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(mutation_id, 4),
            "input_mode": "text",
            "raw_text": raw_text,
            "timer_elapsed_seconds": 600,
            "timer_active_seconds": 0,
            "occurred_at": "2026-04-28T12:10:00Z",
            "privacy_class": privacy_class,
            "metadata": {"source": "phase4-test"},
        },
    )
    assert response.status_code == 201
    return response.json()


def drain_one_workflow(store: InMemoryStore) -> None:
    processed = WorkflowWorker(InMemoryUnitOfWorkFactory(store)).drain_once()
    assert processed == 1


def extract_annotation_candidate(
    client: TestClient,
    store: InMemoryStore,
    annotation_id: str,
    *,
    mutation_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/v1/timing/annotations/{annotation_id}/extract",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation(mutation_id, 5), "force": False},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    drain_one_workflow(store)
    return next(iter(store.extracted_events.values())).model_dump(mode="json")


def test_sponge_detour_extraction_creates_candidate_without_mutating_source_timing() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id)
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
    )
    before = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()

    response = client.post(
        f"/v1/timing/annotations/{annotation['id']}/extract",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("extract-sponge", 5), "force": False},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["model_invocation_id"] is None
    assert body["extracted_events"] == []
    drain_one_workflow(store)
    workflow = next(iter(store.workflow_runs.values()))
    assert workflow.status == "succeeded"
    assert workflow.result_ref["status"] == "needs_confirmation"
    assert len(store.extracted_events) == 1
    event = next(iter(store.extracted_events.values())).model_dump(mode="json")
    assert event["annotation_id"] == annotation["id"]
    assert event["session_id"] == session_id
    assert event["span_type"] == "resource_detour"
    assert event["friction_category"] == "resource"
    assert event["resource_name"] == "sponge"
    assert event["duration_seconds"] == 600
    assert event["count_policy"] == "wall_only"
    assert event["count_in_wall_time"] is True
    assert event["count_in_active_time"] is False
    assert event["suggested_preflight_text"]
    assert event["confirmation_state"] == "needs_confirmation"
    assert event["source_json"]["evidence"] == "resource_detour_keyword"

    after = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert after["wall_seconds"] == before["wall_seconds"]
    assert after["active_seconds"] == before["active_seconds"]
    assert after["spans"] == before["spans"]
    assert len(store.model_invocations) == 1
    invocation = next(iter(store.model_invocations.values()))
    assert "sponge" not in str(invocation.request_hash)


def test_private_annotation_extraction_is_blocked_before_model_invocation(caplog) -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id, "private")
    sensitive_note = "PRIVATE_PHASE4_SECRET_NOTE_DO_NOT_MODEL"
    annotation = create_annotation(
        client,
        session_id,
        sensitive_note,
        privacy_class="private",
        mutation_id="annotation-private",
    )

    caplog.set_level(logging.INFO)
    response = client.post(
        f"/v1/timing/annotations/{annotation['id']}/extract",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("extract-private", 5), "force": False},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["extracted_events"] == []
    assert store.model_invocations == {}
    assert store.extracted_events == {}
    assert sensitive_note not in caplog.text
    drain_one_workflow(store)
    workflow = next(iter(store.workflow_runs.values()))
    assert workflow.result_ref["status"] == "blocked_by_privacy"
    assert store.model_invocations == {}
    assert store.extracted_events == {}
    assert sensitive_note not in caplog.text


def test_invalid_extractor_output_is_rejected_without_durable_truth() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id, "invalid")
    annotation = create_annotation(
        client,
        session_id,
        "PARALLAX_TEST_INVALID_STRUCTURED_EXTRACTION",
        mutation_id="annotation-invalid",
    )

    response = client.post(
        f"/v1/timing/annotations/{annotation['id']}/extract",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("extract-invalid", 5), "force": False},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["extracted_events"] == []
    assert store.extracted_events == {}
    drain_one_workflow(store)
    workflow = next(iter(store.workflow_runs.values()))
    assert workflow.result_ref["status"] == "model_output_invalid"
    invocation = next(iter(store.model_invocations.values()))
    assert invocation.schema_valid is False


def test_confirm_and_correct_extracted_event_update_derived_span_and_audit() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id, "correct")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="annotation-correct",
    )
    extracted = extract_annotation_candidate(
        client,
        store,
        str(annotation["id"]),
        mutation_id="extract-correct",
    )

    confirmed = client.post(
        f"/v1/timing/extracted-events/{extracted['id']}/confirm",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation("confirm-event", 6), "confirmation_state": "confirmed"},
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["confirmation_state"] == "confirmed"
    session_after_confirm = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    span = next(
        span
        for span in session_after_confirm["spans"]
        if span["linked_extracted_event_id"] == extracted["id"]
    )
    assert span["span_type"] == "resource_detour"
    assert span["duration_seconds"] == 600
    assert span["count_policy"] == "wall_only"

    corrected = client.post(
        f"/v1/timing/extracted-events/{extracted['id']}/correct",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("correct-event", 7),
            "span_type": "interruption",
            "friction_category": "interruption",
            "duration_seconds": 300,
            "count_policy": "wall_only",
            "count_in_wall_time": True,
            "count_in_active_time": False,
            "suggested_preflight_text": "Stage the sponge and towels before starting.",
            "user_note": "It was a person interruption, not a missing resource.",
        },
    )

    assert corrected.status_code == 200
    corrected_body = corrected.json()
    assert corrected_body["confirmation_state"] == "corrected"
    assert corrected_body["span_type"] == "interruption"
    assert corrected_body["friction_category"] == "interruption"
    assert corrected_body["duration_seconds"] == 300
    assert corrected_body["source_json"]["evidence"] == "resource_detour_keyword"
    assert corrected_body["user_correction_json"]["user_note"]

    session_after_correction = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    corrected_span = next(
        span
        for span in session_after_correction["spans"]
        if span["linked_extracted_event_id"] == extracted["id"]
    )
    assert corrected_span["span_type"] == "interruption"
    assert corrected_span["duration_seconds"] == 300
    assert corrected_span["user_corrected"] is True
    assert len(store.temporal_corrections) == 1


def test_place_resolver_persists_inferred_candidate_without_silent_timer_change() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id, "place")
    before = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    place = client.post(
        "/v1/places",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("place-kitchen", 4),
            "display_name": "Kitchen",
            "category": "kitchen",
            "latitude": 37.33182,
            "longitude": -122.03118,
            "radius_meters": 50,
            "source": "manual_place",
            "privacy_class": "normal",
            "confirmed_by_user": True,
            "is_sensitive": False,
        },
    )
    assert place.status_code == 201
    policy = client.patch(
        "/v1/privacy/context-capture-policy",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("enable-location-for-inference", 5),
            "location_enabled": True,
            "precise_location_enabled": True,
            "default_location_retention_policy": "store_with_consent",
            "per_run_context_default": True,
        },
    )
    assert policy.status_code == 200
    snapshot = client.post(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("snapshot-near-kitchen", 6),
            "capture_method": "lock_screen_widget",
            "capture_trigger": "timer_event",
            "client_captured_at": "2026-04-28T12:02:00Z",
            "source_device_id": "ios-phase4-test",
            "app_foreground_state": "extension",
            "location_state": "available",
            "radio_state": "not_requested",
            "motion_state_available": "not_requested",
            "device_context_state": "not_requested",
            "privacy_class": "normal",
            "retention_policy": "store_with_consent",
            "permission_summary": {"location": "available"},
            "geospatial_observations": [
                {
                    "source": "gps",
                    "observed_at": "2026-04-28T12:02:00Z",
                    "latitude": 37.33183,
                    "longitude": -122.03119,
                    "horizontal_accuracy_meters": 5,
                    "is_precise": True,
                    "is_stale": False,
                    "privacy_class": "normal",
                    "retention_policy": "store_with_consent",
                }
            ],
        },
    )
    assert snapshot.status_code == 201
    assert len(store.inferred_place_observations) == 0
    drain_one_workflow(store)
    assert len(store.inferred_place_observations) == 1
    inferred_count = len(store.inferred_place_observations)

    resolved = client.post(
        "/v1/places/resolve",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "snapshot_id": snapshot.json()["id"],
            "candidate_category": "unknown",
            "include_unconfirmed_candidates": True,
            "privacy_class": "normal",
        },
    )

    assert resolved.status_code == 200
    body = resolved.json()
    assert body["requires_confirmation"] is True
    assert body["recommended_place_id"] == place.json()["id"]
    assert body["candidates"][0]["match_type"] == "inferred_candidate"
    assert body["candidates"][0]["candidate_label"] == "Kitchen"
    assert body["candidates"][0]["evidence"]["source"] == "geospatial_distance"
    assert len(store.inferred_place_observations) == inferred_count

    after = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert after["wall_seconds"] == before["wall_seconds"]
    assert after["active_seconds"] == before["active_seconds"]


def test_sync_push_applies_phase4_extraction_operation() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_started_session(client, activity_id, "sync")
    annotation = create_annotation(
        client,
        session_id,
        "I had to stop and find the sponge, which took about 10 minutes.",
        mutation_id="annotation-sync",
    )

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-phase4", 20),
            "client_device_id": "ios-phase4-test",
            "mutations": [
                {
                    "operation": "extract_context_annotation",
                    "path": f"/v1/timing/annotations/{annotation['id']}/extract",
                    "body": {"mutation": mutation("sync-extract", 21), "force": False},
                }
            ],
        },
    )

    assert response.status_code == 202
    assert response.json()["operation_count"] == 1
    assert len(store.extracted_events) == 0
    drain_one_workflow(store)
    assert len(store.extracted_events) == 1
    event = next(iter(store.extracted_events.values()))
    assert event.annotation_id == UUID(str(annotation["id"]))
