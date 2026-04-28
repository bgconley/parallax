from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from parallax_api.main import create_app
from parallax_api.repositories.in_memory_unit_of_work import InMemoryUnitOfWorkFactory
from parallax_api.repositories.memory import InMemoryStore
from parallax_api.schemas.context import TimingReviewFlag

USER_ID = "00000000-0000-0000-0000-0000000003c1"


def make_app_and_store() -> tuple[FastAPI, InMemoryStore]:
    store = InMemoryStore()
    return create_app(uow_factory=InMemoryUnitOfWorkFactory(store)), store


def mutation(
    client_mutation_id: str,
    sequence: int = 1,
    *,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    return {
        "client_mutation_id": client_mutation_id,
        "client_device_id": "ios-phase3-test",
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": idempotency_key or f"idem-{client_mutation_id}",
        "client_sequence": sequence,
    }


def create_activity(client: TestClient, name: str = "Phase 3 kitchen") -> str:
    response = client.post(
        "/v1/activities",
        headers={"X-Parallax-User-Id": USER_ID},
        json={"mutation": mutation(f"activity-{name}"), "display_name": name},
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def create_session(client: TestClient, activity_id: str, suffix: str = "main") -> str:
    response = client.post(
        "/v1/timing/sessions",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"session-{suffix}"),
            "activity_id": activity_id,
            "client_session_id": f"phase3-{suffix}",
            "mode": "whole_task",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def append_started_event(client: TestClient, session_id: str, suffix: str = "start") -> dict:
    response = client.post(
        f"/v1/timing/sessions/{session_id}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation(f"event-{suffix}", 2),
            "event_type": "session_started",
            "client_time": "2026-04-28T12:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()


def capture_context_payload(
    client_mutation_id: str,
    *,
    location_state: str = "permission_denied",
    radio_state: str = "permission_denied",
    motion_state_available: str = "unsupported",
    device_context_state: str = "not_requested",
) -> dict[str, object]:
    return {
        "mutation": mutation(client_mutation_id, 10, idempotency_key=f"idem-{client_mutation_id}"),
        "capture_method": "lock_screen_widget",
        "capture_trigger": "timer_event",
        "client_captured_at": "2026-04-28T12:00:05Z",
        "source_device_id": "ios-phase3-test",
        "app_foreground_state": "extension",
        "location_state": location_state,
        "radio_state": radio_state,
        "motion_state_available": motion_state_available,
        "device_context_state": device_context_state,
        "privacy_class": "private",
        "retention_policy": "derived_only",
        "permission_summary": {
            "location": location_state,
            "radio": radio_state,
            "motion": motion_state_available,
            "device_context": device_context_state,
        },
        "geospatial_observations": [
            {
                "source": "gps",
                "observed_at": "2026-04-28T12:00:04Z",
                "latitude": 37.33182,
                "longitude": -122.03118,
                "is_precise": True,
                "is_stale": False,
                "privacy_class": "private",
                "retention_policy": "store_with_consent",
            }
        ],
        "radio_observations": [
            {
                "source": "wifi_connected_network",
                "observed_at": "2026-04-28T12:00:04Z",
                "identifier_hash": "hash-only",
                "redacted_display_label": "Home Wi-Fi",
                "raw_encrypted_object_ref": "s3://raw-radio/not-allowed",
                "privacy_class": "sensitive",
                "retention_policy": "store_with_consent",
            }
        ],
        "device_context_observations": [
            {
                "observed_at": "2026-04-28T12:00:04Z",
                "motion_state": "stationary",
                "charging_state": "unknown",
                "network_state": "wifi",
                "device_type": "phone",
                "app_foreground_state": "extension",
                "privacy_class": "normal",
                "retention_policy": "derived_only",
            }
        ],
        "metadata": {"source": "phase3-test"},
    }


def test_annotation_capture_persists_private_note_and_creates_source_event_without_logs(
    caplog,
) -> None:
    app, _store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_session(client, activity_id)
    sensitive_note = "PRIVATE_PHASE3_RAW_NOTE_SHOULD_NOT_LOG"

    caplog.set_level(logging.INFO)
    payload = {
        "mutation": mutation("annotation-private", 3),
        "input_mode": "text",
        "raw_text": sensitive_note,
        "timer_elapsed_seconds": 42,
        "timer_active_seconds": 41,
        "occurred_at": "2026-04-28T12:00:42Z",
        "privacy_class": "private",
        "metadata": {"chip": "say-what-happened"},
    }
    created = client.post(
        f"/v1/timing/sessions/{session_id}/annotations",
        headers={"X-Parallax-User-Id": USER_ID},
        json=payload,
    )
    replay = client.post(
        f"/v1/timing/sessions/{session_id}/annotations",
        headers={"X-Parallax-User-Id": USER_ID},
        json=payload,
    )

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == created.json()
    annotation = created.json()
    assert annotation["raw_text"] == sensitive_note
    assert annotation["privacy_class"] == "private"
    assert annotation["status"] == "extraction_pending"
    assert annotation["timer_elapsed_seconds"] == 42
    assert sensitive_note not in caplog.text

    fetched = client.get(
        f"/v1/timing/annotations/{annotation['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert fetched.status_code == 200
    assert fetched.json() == annotation

    session = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    annotation_events = [
        event for event in session["events"] if event["event_type"] == "annotation_captured"
    ]
    assert len(annotation_events) == 1
    assert annotation_events[0]["timer_elapsed_seconds"] == 42
    assert annotation_events[0]["payload"]["annotation_id"] == annotation["id"]


def test_context_policy_disables_sensor_payloads_and_denied_capture_keeps_timing_totals() -> None:
    app, _store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_session(client, activity_id)
    append_started_event(client, session_id)
    before = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()

    policy = client.patch(
        "/v1/privacy/context-capture-policy",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("policy-disable-sensors", 4),
            "location_enabled": False,
            "radio_context_enabled": False,
            "motion_context_enabled": False,
            "device_context_enabled": False,
            "per_run_context_default": True,
        },
    )
    assert policy.status_code == 200
    assert policy.json()["location_enabled"] is False
    assert policy.json()["radio_context_enabled"] is False

    denied = client.post(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
        json=capture_context_payload("snapshot-denied"),
    )
    assert denied.status_code == 201
    assert denied.json()["capture_method"] == "lock_screen_widget"
    assert denied.json()["location_state"] == "permission_denied"
    assert denied.json()["radio_state"] == "permission_denied"

    uploaded_despite_policy = client.post(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
        json=capture_context_payload(
            "snapshot-policy-disabled",
            location_state="available",
            radio_state="available",
            motion_state_available="available",
            device_context_state="available",
        ),
    )
    assert uploaded_despite_policy.status_code == 201
    filtered = uploaded_despite_policy.json()
    assert filtered["location_state"] == "disabled_by_system"
    assert filtered["radio_state"] == "disabled_by_system"
    assert filtered["motion_state_available"] == "disabled_by_system"
    assert filtered["device_context_state"] == "disabled_by_system"
    assert filtered["geospatial_observations"] == []
    assert filtered["radio_observations"] == []
    assert filtered["device_context_observations"] == []

    after = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert after["wall_seconds"] == before["wall_seconds"]
    assert after["active_seconds"] == before["active_seconds"]


def test_pending_snapshot_refs_resolve_for_timing_events_and_annotations() -> None:
    app, _store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_session(client, activity_id)

    start = client.post(
        f"/v1/timing/sessions/{session_id}/events",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("event-with-pending-context", 2),
            "event_type": "session_started",
            "client_time": "2026-04-28T12:00:00Z",
            "capture_context_snapshot_ref": "snapshot-start-ref",
        },
    )
    assert start.status_code == 201
    assert start.json()["capture_context_snapshot_id"] is None

    snapshot = client.post(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
        json=capture_context_payload("snapshot-start-ref"),
    )
    assert snapshot.status_code == 201
    snapshot_id = snapshot.json()["id"]

    session = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert session["events"][0]["capture_context_snapshot_id"] == snapshot_id

    annotation = client.post(
        f"/v1/timing/sessions/{session_id}/annotations",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("annotation-with-pending-context", 3),
            "input_mode": "quick_chip",
            "raw_text": "Sponge was missing.",
            "capture_context_snapshot_ref": "idem-snapshot-annotation-ref",
            "occurred_at": "2026-04-28T12:01:00Z",
            "privacy_class": "sensitive",
            "metadata": {},
        },
    )
    assert annotation.status_code == 201
    assert annotation.json()["capture_context_snapshot_id"] is None

    annotation_snapshot = client.post(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
        json=capture_context_payload(
            "snapshot-annotation-ref",
            location_state="stale",
            radio_state="unsupported",
        ),
    )
    assert annotation_snapshot.status_code == 201

    fetched_annotation = client.get(
        f"/v1/timing/annotations/{annotation.json()['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert fetched_annotation["capture_context_snapshot_id"] == annotation_snapshot.json()["id"]


def test_places_resolver_is_read_only_and_confirmed_places_can_be_created_and_updated() -> None:
    app, _store = make_app_and_store()
    client = TestClient(app)

    resolved = client.post(
        "/v1/places/resolve",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "candidate_label": "Kitchen",
            "candidate_category": "kitchen",
            "include_unconfirmed_candidates": False,
            "privacy_class": "sensitive",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["requires_confirmation"] is True
    assert client.get("/v1/places", headers={"X-Parallax-User-Id": USER_ID}).json() == []

    unconfirmed_sensitive = client.post(
        "/v1/places",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("place-unconfirmed-sensitive", 4),
            "display_name": "Home",
            "category": "home",
            "source": "manual_place",
            "privacy_class": "private",
            "confirmed_by_user": False,
        },
    )
    assert unconfirmed_sensitive.status_code == 400

    created = client.post(
        "/v1/places",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("place-create", 5),
            "display_name": "Kitchen",
            "category": "kitchen",
            "source": "manual_place",
            "privacy_class": "sensitive",
            "confirmed_by_user": True,
            "is_sensitive": True,
            "aliases": ["sink"],
            "metadata": {"created_from": "phase3-test"},
        },
    )
    assert created.status_code == 201
    place = created.json()
    assert place["confirmed_by_user"] is True
    assert place["is_sensitive"] is True

    resolved_after_create = client.post(
        "/v1/places/resolve",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "candidate_label": "Kitchen",
            "candidate_category": "kitchen",
            "include_unconfirmed_candidates": False,
            "existing_place_id": place["id"],
            "privacy_class": "sensitive",
        },
    )
    assert resolved_after_create.status_code == 200
    assert resolved_after_create.json()["recommended_place_id"] == place["id"]

    updated = client.patch(
        f"/v1/places/{place['id']}",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("place-update", 6),
            "display_name": "Kitchen sink",
            "aliases": ["dish area"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Kitchen sink"
    assert updated.json()["aliases"] == ["dish area"]


def test_review_flag_resolve_does_not_mutate_source_timing_facts() -> None:
    app, store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_session(client, activity_id)
    append_started_event(client, session_id)
    before = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    flag = TimingReviewFlag(
        id=uuid4(),
        user_id=UUID(USER_ID),
        session_id=UUID(session_id),
        snapshot_id=None,
        flag_type="manual_review_requested",
        status="open",
        severity="medium",
        confidence=0.7,
        reason_code="manual_probe",
        user_message="Review this timer.",
        evidence={"source": "test"},
        created_at=datetime.now(UTC),
        resolved_at=None,
        resolution_note=None,
    )
    store.review_flags[flag.id] = flag

    listed = client.get(
        f"/v1/timing/sessions/{session_id}/review-flags",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [str(flag.id)]

    resolved = client.patch(
        f"/v1/timing/review-flags/{flag.id}",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("review-flag-resolve", 6),
            "status": "resolved",
            "resolution_note": "Looks fine.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    after = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert after["events"] == before["events"]
    assert after["wall_seconds"] == before["wall_seconds"]
    assert after["active_seconds"] == before["active_seconds"]


def test_sync_push_applies_phase3_annotation_and_capture_snapshot_operations() -> None:
    app, _store = make_app_and_store()
    client = TestClient(app)
    activity_id = create_activity(client)
    session_id = create_session(client, activity_id)

    response = client.post(
        "/v1/sync/push",
        headers={"X-Parallax-User-Id": USER_ID},
        json={
            "mutation": mutation("sync-phase3-batch", 20),
            "client_device_id": "ios-phase3-test",
            "mutations": [
                {
                    "operation": "create_capture_context_snapshot",
                    "path": f"/v1/timing/sessions/{session_id}/capture-context",
                    "body": capture_context_payload("sync-snapshot"),
                },
                {
                    "operation": "create_context_annotation",
                    "path": f"/v1/timing/sessions/{session_id}/annotations",
                    "body": {
                        "mutation": mutation("sync-annotation", 21),
                        "input_mode": "text",
                        "raw_text": "Had to find the sponge.",
                        "occurred_at": "2026-04-28T12:02:00Z",
                        "privacy_class": "sensitive",
                        "metadata": {},
                    },
                },
            ],
        },
    )
    assert response.status_code == 202
    assert response.json()["operation_count"] == 2

    snapshots = client.get(
        f"/v1/timing/sessions/{session_id}/capture-context",
        headers={"X-Parallax-User-Id": USER_ID},
    )
    assert snapshots.status_code == 200
    assert len(snapshots.json()) == 1
    session = client.get(
        f"/v1/timing/sessions/{session_id}",
        headers={"X-Parallax-User-Id": USER_ID},
    ).json()
    assert [event["event_type"] for event in session["events"]] == ["annotation_captured"]
