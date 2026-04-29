from __future__ import annotations

import argparse
import json
import time
from uuid import UUID, uuid4

import httpx
import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 4 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase4-smoke-{user_id.hex[:8]}"
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
                        "display_name": f"Phase 4 smoke {user_id.hex[:8]}",
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
                        "client_session_id": f"phase4-{uuid4().hex}",
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
                        "mutation": _mutation(device_id, "start", 3),
                        "event_type": "session_started",
                        "client_time": "2026-04-28T12:00:00Z",
                    },
                ),
                201,
            )
            _expect(
                client.patch(
                    "/v1/privacy/context-capture-policy",
                    json={
                        "mutation": _mutation(device_id, "policy-location", 4),
                        "location_enabled": True,
                        "precise_location_enabled": True,
                        "default_location_retention_policy": "store_with_consent",
                        "per_run_context_default": True,
                    },
                ),
                200,
            )
            place = _expect(
                client.post(
                    "/v1/places",
                    json={
                        "mutation": _mutation(device_id, "place", 5),
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
                ),
                201,
            )
            snapshot = _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/capture-context",
                    json={
                        "mutation": _mutation(device_id, "snapshot", 6),
                        "capture_method": "lock_screen_widget",
                        "capture_trigger": "timer_event",
                        "client_captured_at": "2026-04-28T12:02:00Z",
                        "source_device_id": device_id,
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
                ),
                201,
            )
            _wait_for_phase4_count(args.database_url, user_id, "inferred_places", 1)
            resolve = _expect(
                client.post(
                    "/v1/places/resolve",
                    json={
                        "snapshot_id": snapshot["id"],
                        "candidate_category": "unknown",
                        "include_unconfirmed_candidates": True,
                        "privacy_class": "normal",
                    },
                ),
                200,
            )
            if resolve["recommended_place_id"] != place["id"]:
                raise AssertionError(f"place resolver did not read inferred candidate: {resolve}")

            annotation = _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/annotations",
                    json={
                        "mutation": _mutation(device_id, "annotation", 7),
                        "input_mode": "text",
                        "raw_text": (
                            "I had to stop and find the sponge, which took about 10 minutes."
                        ),
                        "timer_elapsed_seconds": 600,
                        "timer_active_seconds": 0,
                        "occurred_at": "2026-04-28T12:10:00Z",
                        "privacy_class": "normal",
                        "metadata": {},
                    },
                ),
                201,
            )
            extraction = _expect(
                client.post(
                    f"/v1/timing/annotations/{annotation['id']}/extract",
                    json={"mutation": _mutation(device_id, "extract", 8), "force": False},
                ),
                202,
            )
            if extraction["status"] != "queued":
                raise AssertionError(f"unexpected extraction status: {extraction}")
            event = _wait_for_extracted_event(
                args.database_url,
                user_id,
                UUID(str(annotation["id"])),
            )
            if event["count_policy"] != "wall_only" or not event["suggested_preflight_text"]:
                raise AssertionError(f"golden extraction candidate is wrong: {event}")
            confirmed = _expect(
                client.post(
                    f"/v1/timing/extracted-events/{event['id']}/confirm",
                    json={
                        "mutation": _mutation(device_id, "confirm", 9),
                        "confirmation_state": "confirmed",
                    },
                ),
                200,
            )
            if confirmed["confirmation_state"] != "confirmed":
                raise AssertionError(f"confirm failed: {confirmed}")
            corrected = _expect(
                client.post(
                    f"/v1/timing/extracted-events/{event['id']}/correct",
                    json={
                        "mutation": _mutation(device_id, "correct", 10),
                        "span_type": "interruption",
                        "friction_category": "interruption",
                        "duration_seconds": 300,
                        "count_policy": "wall_only",
                        "count_in_wall_time": True,
                        "count_in_active_time": False,
                        "suggested_preflight_text": (
                            "Stage the sponge and towels before starting."
                        ),
                        "user_note": "Smoke correction.",
                    },
                ),
                200,
            )
            if corrected["confirmation_state"] != "corrected":
                raise AssertionError(f"correction failed: {corrected}")
            session_after = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            linked_spans = [
                span
                for span in _list_value(session_after, "spans")
                if span["linked_extracted_event_id"] == event["id"]
            ]
            if len(linked_spans) != 1 or linked_spans[0]["duration_seconds"] != 300:
                raise AssertionError(f"derived span did not update: {session_after}")

        counts = _phase4_counts(args.database_url, user_id)
        expected = {
            "model_invocations": 1,
            "extracted_events": 1,
            "corrections": 1,
            "linked_spans": 1,
            "inferred_places": 1,
        }
        for key, value in expected.items():
            if counts[key] != value:
                raise AssertionError(f"unexpected Phase 4 count for {key}: {counts}")
        if counts["preflight_checks"] < 1:
            raise AssertionError(f"expected at least one preflight check: {counts}")

        summary.update(
            {
                "activity_id": activity_id,
                "session_id": session_id,
                "annotation_id": annotation["id"],
                "extracted_event_id": event["id"],
                "snapshot_id": snapshot["id"],
                **counts,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase4", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _mutation(device_id: str, mutation_id: str, sequence: int) -> dict[str, object]:
    return {
        "client_mutation_id": f"{mutation_id}-{uuid4().hex[:8]}",
        "client_device_id": device_id,
        "client_timestamp": "2026-04-28T12:00:00Z",
        "idempotency_key": f"idem-{mutation_id}-{uuid4().hex[:8]}",
        "client_sequence": sequence,
    }


def _wait_for_health(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = client.get("/v1/health")
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"API did not become healthy: {last_error}")


def _expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise AssertionError(
            f"expected {status_code} from {response.request.method} {response.request.url}, "
            f"got {response.status_code}: {response.text}"
        )
    body = response.json()
    if not isinstance(body, dict):
        raise AssertionError(f"expected object response, got {body!r}")
    return body


def _string_value(body: dict[str, object], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str):
        raise AssertionError(f"expected string {key}, got {body}")
    return value


def _list_value(body: dict[str, object], key: str) -> list[dict[str, object]]:
    value = body.get(key)
    if not isinstance(value, list):
        raise AssertionError(f"expected list {key}, got {body}")
    items: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise AssertionError(f"expected object entries in {key}, got {body}")
        items.append(item)
    return items


def _phase4_counts(database_url: str, user_id: UUID) -> dict[str, int]:
    queries = {
        "model_invocations": "select count(*) from model_invocation where user_id = %s",
        "extracted_events": (
            "select count(*) from temporal_extracted_context_event where user_id = %s"
        ),
        "corrections": "select count(*) from temporal_correction where user_id = %s",
        "linked_spans": (
            "select count(*) from timing_event_span "
            "where user_id = %s and linked_extracted_event_id is not null"
        ),
        "inferred_places": (
            "select count(*) from inferred_place_observation where user_id = %s"
        ),
        "preflight_checks": "select count(*) from preflight_check where user_id = %s",
    }
    counts: dict[str, int] = {}
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for key, sql in queries.items():
                cursor.execute(sql, (user_id,))
                row = cursor.fetchone()
                counts[key] = int(row[0]) if row is not None else 0
    return counts


def _wait_for_phase4_count(
    database_url: str,
    user_id: UUID,
    count_name: str,
    expected: int,
) -> None:
    deadline = time.monotonic() + 30
    latest: dict[str, int] = {}
    while time.monotonic() < deadline:
        latest = _phase4_counts(database_url, user_id)
        if latest.get(count_name, 0) >= expected:
            return
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {count_name}={expected}: {latest}")


def _wait_for_extracted_event(
    database_url: str,
    user_id: UUID,
    annotation_id: UUID,
) -> dict[str, object]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        event = _fetch_extracted_event(database_url, user_id, annotation_id)
        if event is not None:
            return event
        time.sleep(1)
    raise AssertionError(f"timed out waiting for extracted event for annotation {annotation_id}")


def _fetch_extracted_event(
    database_url: str,
    user_id: UUID,
    annotation_id: UUID,
) -> dict[str, object] | None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id, annotation_id, session_id, span_type::text, friction_category::text,
                  resource_name, duration_seconds, count_policy::text, count_in_wall_time,
                  count_in_active_time, suggested_preflight_text, confirmation_state::text
                from temporal_extracted_context_event
                where user_id = %s and annotation_id = %s
                order by created_at desc
                limit 1
                """,
                (user_id, annotation_id),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "annotation_id": str(row[1]),
        "session_id": str(row[2]),
        "span_type": row[3],
        "friction_category": row[4],
        "resource_name": row[5],
        "duration_seconds": row[6],
        "count_policy": row[7],
        "count_in_wall_time": row[8],
        "count_in_active_time": row[9],
        "suggested_preflight_text": row[10],
        "confirmation_state": row[11],
    }


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
