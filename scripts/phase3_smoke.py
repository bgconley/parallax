from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg.types.json import Jsonb


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 3 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase3-smoke-{user_id.hex[:8]}"
    api_url = args.api_url.rstrip("/")
    headers = {"X-Parallax-User-Id": str(user_id)}
    summary: dict[str, object] = {"user_id": str(user_id), "device_id": device_id}

    try:
        with httpx.Client(base_url=api_url, headers=headers, timeout=10) as client:
            _wait_for_health(client)
            activity = _expect(
                client.post(
                    "/v1/activities",
                    json={
                        "mutation": _mutation(device_id, "activity", 1),
                        "display_name": f"Phase 3 smoke {user_id.hex[:8]}",
                    },
                ),
                201,
            )
            activity_id = _string_value(activity, "id")
            session = _expect(
                client.post(
                    "/v1/timing/sessions",
                    json={
                        "mutation": _mutation(device_id, "session", 2),
                        "activity_id": activity_id,
                        "client_session_id": f"phase3-{uuid4().hex}",
                        "mode": "whole_task",
                    },
                ),
                201,
            )
            session_id = _string_value(session, "id")

            _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/events",
                    json={
                        "mutation": _mutation(device_id, "start-with-context-ref", 3),
                        "event_type": "session_started",
                        "client_time": "2026-04-28T12:00:00Z",
                        "capture_context_snapshot_ref": "start-snapshot-ref",
                    },
                ),
                201,
            )
            before_context = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)

            policy = _expect(client.get("/v1/privacy/context-capture-policy"), 200)
            if policy["location_enabled"] or policy["radio_context_enabled"]:
                raise AssertionError(
                    f"default context policy should disable optional sensors: {policy}"
                )
            updated_policy = _expect(
                client.patch(
                    "/v1/privacy/context-capture-policy",
                    json={
                        "mutation": _mutation(device_id, "policy-update", 4),
                        "location_enabled": False,
                        "radio_context_enabled": False,
                        "motion_context_enabled": False,
                        "device_context_enabled": False,
                    },
                ),
                200,
            )
            if updated_policy["device_context_enabled"]:
                raise AssertionError(f"context policy update did not persist: {updated_policy}")

            snapshot = _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/capture-context",
                    json=_snapshot_payload(device_id, "start-snapshot-ref"),
                ),
                201,
            )
            snapshot_id = _string_value(snapshot, "id")
            if snapshot["location_state"] != "disabled_by_system":
                raise AssertionError(
                    f"backend policy did not disable uploaded location: {snapshot}"
                )
            if snapshot["geospatial_observations"] or snapshot["radio_observations"]:
                raise AssertionError(f"disabled policy stored raw context: {snapshot}")

            session_after_snapshot = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            first_event = _list_value(session_after_snapshot, "events")[0]
            if (
                not isinstance(first_event, dict)
                or first_event["capture_context_snapshot_id"] != snapshot_id
            ):
                raise AssertionError(
                    f"pending snapshot ref did not resolve: {session_after_snapshot}"
                )
            _assert_context_did_not_change_totals(before_context, session_after_snapshot)

            annotation = _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/annotations",
                    json={
                        "mutation": _mutation(device_id, "annotation", 5),
                        "input_mode": "text",
                        "raw_text": "Had to find the sponge.",
                        "occurred_at": "2026-04-28T12:01:00Z",
                        "privacy_class": "sensitive",
                        "capture_context_snapshot_ref": "start-snapshot-ref",
                        "metadata": {},
                    },
                ),
                201,
            )
            if annotation["status"] != "extraction_pending":
                raise AssertionError(f"annotation not left pending for Phase 4: {annotation}")
            if annotation["capture_context_snapshot_id"] != snapshot_id:
                raise AssertionError(f"annotation snapshot ref did not resolve: {annotation}")
            fetched_annotation = _expect(
                client.get(f"/v1/timing/annotations/{annotation['id']}"),
                200,
            )
            if fetched_annotation != annotation:
                raise AssertionError("annotation GET did not return created annotation")

            resolve = _expect(
                client.post(
                    "/v1/places/resolve",
                    json={
                        "candidate_label": "Kitchen",
                        "candidate_category": "kitchen",
                        "include_unconfirmed_candidates": False,
                        "privacy_class": "sensitive",
                    },
                ),
                200,
            )
            if resolve["requires_confirmation"] is not True:
                raise AssertionError(f"read-only resolver should require confirmation: {resolve}")
            if _expect_list(client.get("/v1/places")):
                raise AssertionError("place resolver created a place")
            place = _expect(
                client.post(
                    "/v1/places",
                    json={
                        "mutation": _mutation(device_id, "place", 6),
                        "display_name": "Kitchen",
                        "category": "kitchen",
                        "source": "manual_place",
                        "privacy_class": "sensitive",
                        "confirmed_by_user": True,
                        "is_sensitive": True,
                    },
                ),
                201,
            )
            place_id = _string_value(place, "id")
            updated_place = _expect(
                client.patch(
                    f"/v1/places/{place_id}",
                    json={
                        "mutation": _mutation(device_id, "place-update", 7),
                        "display_name": "Kitchen sink",
                    },
                ),
                200,
            )
            if updated_place["display_name"] != "Kitchen sink":
                raise AssertionError(f"place update failed: {updated_place}")

            flag_id = _seed_review_flag(
                args.database_url,
                user_id,
                UUID(session_id),
                UUID(snapshot_id),
            )
            flags = _expect_list(client.get(f"/v1/timing/sessions/{session_id}/review-flags"))
            if [flag["id"] for flag in flags] != [str(flag_id)]:
                raise AssertionError(f"review flag list failed: {flags}")
            session_before_flag = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            resolved_flag = _expect(
                client.patch(
                    f"/v1/timing/review-flags/{flag_id}",
                    json={
                        "mutation": _mutation(device_id, "flag-resolve", 8),
                        "status": "resolved",
                        "resolution_note": "No timer correction needed.",
                    },
                ),
                200,
            )
            if resolved_flag["status"] != "resolved":
                raise AssertionError(f"review flag did not resolve: {resolved_flag}")
            session_after_flag = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            _assert_context_did_not_change_totals(session_before_flag, session_after_flag)

        counts = _phase3_counts(args.database_url, user_id)
        if counts["annotations"] != 1 or counts["snapshots"] != 1 or counts["places"] != 1:
            raise AssertionError(f"unexpected Phase 3 persistence counts: {counts}")
        if counts["review_flags"] != 1:
            raise AssertionError(f"review flag SQL proof failed: {counts}")

        summary.update(
            {
                "activity_id": activity_id,
                "session_id": session_id,
                "snapshot_id": snapshot_id,
                "annotation_id": annotation["id"],
                "place_id": place_id,
                **counts,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase3", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _snapshot_payload(device_id: str, mutation_id: str) -> dict[str, object]:
    return {
        "mutation": _mutation(device_id, mutation_id, 10),
        "capture_method": "lock_screen_widget",
        "capture_trigger": "timer_event",
        "client_captured_at": "2026-04-28T12:00:05Z",
        "source_device_id": device_id,
        "app_foreground_state": "extension",
        "location_state": "available",
        "radio_state": "available",
        "motion_state_available": "available",
        "device_context_state": "available",
        "privacy_class": "private",
        "retention_policy": "derived_only",
        "permission_summary": {"location": "available", "radio": "available"},
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
                "raw_encrypted_object_ref": "s3://raw-radio/not-allowed",
                "privacy_class": "sensitive",
                "retention_policy": "store_with_consent",
            }
        ],
        "metadata": {"source": "phase3-smoke"},
    }


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": mutation_id,
        "client_device_id": device_id,
        "client_timestamp": datetime.now(UTC).isoformat(),
        "idempotency_key": f"{device_id}:{mutation_id}",
        "client_sequence": sequence,
    }


def _expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise AssertionError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}, expected {status_code}: {response.text}"
        )
    data = response.json()
    if not isinstance(data, dict):
        raise AssertionError(f"expected object response, got {type(data).__name__}")
    return data


def _expect_list(response: httpx.Response) -> list[dict[str, object]]:
    if response.status_code != 200:
        raise AssertionError(
            f"{response.request.url} returned {response.status_code}: {response.text}"
        )
    data = response.json()
    if not isinstance(data, list):
        raise AssertionError(f"expected list response, got {type(data).__name__}")
    return data


def _wait_for_health(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = client.get("/v1/health")
            if response.status_code == 200 and response.json().get("status") == "healthy":
                return
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(1)
    raise AssertionError(f"API did not become healthy before Phase 3 smoke: {last_error}")


def _string_value(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise AssertionError(f"expected {key} to be a string")
    return value


def _list_value(data: dict[str, object], key: str) -> list[object]:
    value = data[key]
    if not isinstance(value, list):
        raise AssertionError(f"expected {key} to be a list")
    return value


def _assert_context_did_not_change_totals(
    before: dict[str, object],
    after: dict[str, object],
) -> None:
    for key in ("wall_seconds", "active_seconds"):
        if after.get(key) != before.get(key):
            raise AssertionError(f"context changed {key}: before={before}, after={after}")


def _seed_review_flag(
    database_url: str,
    user_id: UUID,
    session_id: UUID,
    snapshot_id: UUID,
) -> UUID:
    flag_id = uuid4()
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into timing_review_flag (
                  id, user_id, session_id, snapshot_id, flag_type, status, severity,
                  confidence, reason_code, user_message, evidence
                )
                values (%s, %s, %s, %s, 'manual_review_requested', 'open', 'medium',
                  0.7, 'phase3_smoke', 'Review this timer.', %s)
                """,
                (flag_id, user_id, session_id, snapshot_id, Jsonb({"source": "phase3-smoke"})),
            )
    return flag_id


def _phase3_counts(database_url: str, user_id: UUID) -> dict[str, int]:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  (select count(*) from temporal_context_annotation where user_id = %s),
                  (select count(*) from capture_context_snapshot where user_id = %s),
                  (select count(*) from user_place where user_id = %s),
                  (select count(*) from timing_review_flag where user_id = %s)
                """,
                (user_id, user_id, user_id, user_id),
            )
            row = cursor.fetchone()
    if row is None:
        raise AssertionError("Phase 3 SQL proof returned no row")
    return {
        "annotations": int(row[0]),
        "snapshots": int(row[1]),
        "places": int(row[2]),
        "review_flags": int(row[3]),
    }


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
