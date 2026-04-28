from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 1 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase1-smoke-{user_id.hex[:8]}"
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
                        "display_name": f"Phase 1 smoke {user_id.hex[:8]}",
                    },
                ),
                201,
            )
            activity_id = _string_value(activity, "id")

            duplicate_activity = client.post(
                "/v1/activities",
                json={
                    "mutation": _mutation(device_id, "activity-duplicate-key", 2),
                    "display_name": activity["display_name"],
                },
            )
            if duplicate_activity.status_code != 400:
                raise AssertionError("duplicate canonical activity key was not rejected safely")

            session = _expect(
                client.post(
                    "/v1/timing/sessions",
                    json={
                        "mutation": _mutation(device_id, "session", 3),
                        "activity_id": activity_id,
                        "client_session_id": f"client-session-{user_id.hex}",
                        "mode": "whole_task",
                    },
                ),
                201,
            )
            session_id = _string_value(session, "id")

            start_body = {
                "mutation": _mutation(device_id, "event-start", 4),
                "event_type": "session_started",
                "client_time": "2026-04-27T12:00:00Z",
            }
            start_responses = [
                _expect(
                    client.post(f"/v1/timing/sessions/{session_id}/events", json=start_body),
                    201,
                )
                for _ in range(3)
            ]
            if len({response["id"] for response in start_responses}) != 1:
                raise AssertionError("duplicate start replay created more than one event")

            for mutation_id, sequence, event_type, client_time in [
                ("event-pause", 5, "session_paused", "2026-04-27T12:10:00Z"),
                ("event-resume", 6, "session_resumed", "2026-04-27T12:15:00Z"),
            ]:
                _expect(
                    client.post(
                        f"/v1/timing/sessions/{session_id}/events",
                        json={
                            "mutation": _mutation(device_id, mutation_id, sequence),
                            "event_type": event_type,
                            "client_time": client_time,
                        },
                    ),
                    201,
                )

            completed = _expect(
                client.post(
                    f"/v1/timing/sessions/{session_id}/complete",
                    json={
                        "mutation": _mutation(device_id, "event-complete", 7),
                        "completed_at": "2026-04-27T12:20:00Z",
                    },
                ),
                200,
            )
            if completed["wall_seconds"] != 1200 or completed["active_seconds"] != 900:
                raise AssertionError(f"unexpected reconstructed totals: {completed}")

            delayed_replay = _expect(
                client.post(f"/v1/timing/sessions/{session_id}/events", json=start_body),
                201,
            )
            if delayed_replay["id"] != start_responses[0]["id"]:
                raise AssertionError("delayed replay did not return original event")

            fetched = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            if fetched["wall_seconds"] != 1200 or fetched["active_seconds"] != 900:
                raise AssertionError("delayed replay changed reconstructed totals")

            out_of_order_session = _expect(
                client.post(
                    "/v1/timing/sessions",
                    json={
                        "mutation": _mutation(device_id, "session-out-of-order", 8),
                        "activity_id": activity_id,
                        "client_session_id": f"client-session-ooo-{user_id.hex}",
                        "mode": "whole_task",
                    },
                ),
                201,
            )
            out_of_order_id = _string_value(out_of_order_session, "id")
            _expect(
                client.post(
                    f"/v1/timing/sessions/{out_of_order_id}/events",
                    json={
                        "mutation": _mutation(device_id, "event-impossible-pause", 10),
                        "event_type": "session_paused",
                        "client_time": "2026-04-27T13:10:00Z",
                    },
                ),
                201,
            )
            _expect(
                client.post(
                    f"/v1/timing/sessions/{out_of_order_id}/events",
                    json={
                        "mutation": _mutation(device_id, "event-late-start", 9),
                        "event_type": "session_started",
                        "client_time": "2026-04-27T13:00:00Z",
                    },
                ),
                201,
            )
            out_of_order = _expect(client.get(f"/v1/timing/sessions/{out_of_order_id}"), 200)
            if not out_of_order["needs_timeline_recompute"]:
                raise AssertionError("out-of-order/impossible sequence did not flag recompute")

            sync_push = _expect(
                client.post(
                    "/v1/sync/push",
                    json={
                        "mutation": _mutation(device_id, "sync-push", 11),
                        "client_device_id": device_id,
                        "mutations": [
                            {
                                "operation": "append_timing_event",
                                "path": f"/v1/timing/sessions/{session_id}/events",
                                "body": start_body,
                            }
                        ],
                    },
                ),
                202,
            )
            if sync_push["operation_count"] != 1:
                raise AssertionError("sync push did not validate the nested operation")

            synced_activity_name = f"Phase 1 sync replay {user_id.hex[:8]}"
            sync_create_activity = _expect(
                client.post(
                    "/v1/sync/push",
                    json={
                        "mutation": _mutation(device_id, "sync-create-activity", 12),
                        "client_device_id": device_id,
                        "mutations": [
                            {
                                "operation": "create_activity",
                                "path": "/v1/activities",
                                "body": {
                                    "mutation": _mutation(device_id, "sync-nested-activity", 13),
                                    "display_name": synced_activity_name,
                                },
                            }
                        ],
                    },
                ),
                202,
            )
            if sync_create_activity["operation_count"] != 1:
                raise AssertionError("sync push did not replay the create activity operation")

            activities_response = client.get("/v1/activities")
            if activities_response.status_code != 200:
                raise AssertionError(
                    f"GET /v1/activities returned {activities_response.status_code}: "
                    f"{activities_response.text}"
                )
            activities = activities_response.json()
            if not isinstance(activities, list):
                raise AssertionError("expected list response from GET /v1/activities")
            activity_names = {str(item["display_name"]) for item in activities}
            if synced_activity_name not in activity_names:
                raise AssertionError("sync push accepted create activity without applying it")

            failed_sync_activity_name = f"Phase 1 rollback probe {user_id.hex[:8]}"
            missing_session_id = uuid4()
            failed_sync = client.post(
                "/v1/sync/push",
                json={
                    "mutation": _mutation(device_id, "sync-rollback", 14),
                    "client_device_id": device_id,
                    "mutations": [
                        {
                            "operation": "create_activity",
                            "path": "/v1/activities",
                            "body": {
                                "mutation": _mutation(
                                    device_id,
                                    "sync-rollback-nested-activity",
                                    15,
                                ),
                                "display_name": failed_sync_activity_name,
                            },
                        },
                        {
                            "operation": "append_timing_event",
                            "path": f"/v1/timing/sessions/{missing_session_id}/events",
                            "body": {
                                "mutation": _mutation(
                                    device_id,
                                    "sync-rollback-missing-session-event",
                                    16,
                                ),
                                "event_type": "session_started",
                                "client_time": "2026-04-27T15:00:00Z",
                            },
                        },
                    ],
                },
            )
            if failed_sync.status_code != 404:
                raise AssertionError(
                    "sync push did not reject a batch with a missing nested session: "
                    f"{failed_sync.status_code} {failed_sync.text}"
                )
            activities_after_failed_sync_response = client.get("/v1/activities")
            if activities_after_failed_sync_response.status_code != 200:
                raise AssertionError(
                    "GET /v1/activities after failed sync returned "
                    f"{activities_after_failed_sync_response.status_code}: "
                    f"{activities_after_failed_sync_response.text}"
                )
            activities_after_failed_sync = activities_after_failed_sync_response.json()
            if not isinstance(activities_after_failed_sync, list):
                raise AssertionError("expected list response from GET /v1/activities")
            if failed_sync_activity_name in {
                str(item["display_name"]) for item in activities_after_failed_sync
            }:
                raise AssertionError("failed sync batch partially committed an activity")

        with psycopg.connect(args.database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select count(*)
                    from timing_event
                    where user_id = %s and session_id = %s and idempotency_key = %s
                    """,
                    (user_id, UUID(session_id), f"{device_id}:event-start"),
                )
                event_count_row = cursor.fetchone()
                if event_count_row is None:
                    raise AssertionError("event count query returned no row")
                event_count = event_count_row[0]
                cursor.execute(
                    """
                    select count(*)
                    from client_mutation_log
                    where user_id = %s and idempotency_key = %s
                    """,
                    (user_id, f"{device_id}:event-start"),
                )
                mutation_count_row = cursor.fetchone()
                if mutation_count_row is None:
                    raise AssertionError("mutation count query returned no row")
                mutation_count = mutation_count_row[0]
                cursor.execute(
                    """
                    select count(*)
                    from activity
                    where user_id = %s and display_name = %s
                    """,
                    (user_id, failed_sync_activity_name),
                )
                failed_activity_row = cursor.fetchone()
                if failed_activity_row is None:
                    raise AssertionError("failed sync activity count returned no row")
                failed_activity_count = failed_activity_row[0]
                cursor.execute(
                    """
                    select count(*)
                    from client_mutation_log
                    where user_id = %s and idempotency_key in (%s, %s, %s)
                    """,
                    (
                        user_id,
                        f"{device_id}:sync-rollback",
                        f"{device_id}:sync-rollback-nested-activity",
                        f"{device_id}:sync-rollback-missing-session-event",
                    ),
                )
                failed_mutation_row = cursor.fetchone()
                if failed_mutation_row is None:
                    raise AssertionError("failed sync mutation count returned no row")
                failed_mutation_count = failed_mutation_row[0]

        if event_count != 1 or mutation_count != 1:
            raise AssertionError(
                f"expected one event and one mutation log row, got {event_count}/{mutation_count}"
            )
        if failed_activity_count != 0 or failed_mutation_count != 0:
            raise AssertionError(
                "failed sync batch left persisted rows: "
                f"activities={failed_activity_count}, mutations={failed_mutation_count}"
            )

        summary.update(
            {
                "activity_id": activity_id,
                "session_id": session_id,
                "wall_seconds": fetched["wall_seconds"],
                "active_seconds": fetched["active_seconds"],
                "duplicate_event_rows": event_count,
                "duplicate_mutation_rows": mutation_count,
                "out_of_order_recompute_flagged": out_of_order["needs_timeline_recompute"],
                "sync_push_accepted": sync_push["accepted"],
                "sync_create_activity_applied": synced_activity_name,
                "sync_failed_batch_rolled_back": True,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase1", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


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
    raise AssertionError(f"API did not become healthy before Phase 1 smoke: {last_error}")


def _string_value(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise AssertionError(f"expected {key} to be a string")
    return value


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
