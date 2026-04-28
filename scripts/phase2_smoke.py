from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import psycopg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Parallax Phase 2 API smoke test.")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()

    user_id = uuid4()
    device_id = f"phase2-smoke-{user_id.hex[:8]}"
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
                        "display_name": f"Phase 2 smoke {user_id.hex[:8]}",
                    },
                ),
                201,
            )
            activity_id = _string_value(activity, "id")
            session_id = _create_completed_session(
                client,
                activity_id=activity_id,
                device_id=device_id,
                mutation_prefix="reviewed",
                sequence_start=2,
            )

            review_body = {
                "mutation": _mutation(device_id, "review", 20),
                "decision": "save_useful_run",
                "model_inclusion": "full",
                "scopes": ["active_duration", "wall_duration", "friction_patterns"],
            }
            review = _expect(
                client.post(f"/v1/timing/sessions/{session_id}/review", json=review_body),
                200,
            )
            replayed_review = _expect(
                client.post(f"/v1/timing/sessions/{session_id}/review", json=review_body),
                200,
            )
            if replayed_review != review:
                raise AssertionError("duplicate review replay did not return original decision")

            reviewed_session = _expect(client.get(f"/v1/timing/sessions/{session_id}"), 200)
            _assert_reviewed_friction_totals(reviewed_session)

            profile = _expect(client.get(f"/v1/activities/{activity_id}/profile"), 200)
            stats = _dict_value(profile, "latest_stats")
            if stats.get("sample_size") != 1:
                raise AssertionError(f"unexpected profile sample size: {stats}")
            if stats.get("active_p50_seconds") != 900 or stats.get("wall_p50_seconds") != 1800:
                raise AssertionError(f"unexpected profile ranges: {stats}")

            bad_timer_session_id = _create_completed_session(
                client,
                activity_id=activity_id,
                device_id=device_id,
                mutation_prefix="bad-timer",
                sequence_start=30,
            )
            discarded = _expect(
                client.post(
                    f"/v1/timing/sessions/{bad_timer_session_id}/discard",
                    json={
                        "mutation": _mutation(device_id, "discard-bad-timer", 50),
                        "decision": "discard_all",
                        "model_inclusion": "exclude",
                        "scopes": [],
                    },
                ),
                200,
            )
            if discarded["model_inclusion"] != "exclude":
                raise AssertionError(f"discard did not exclude model training: {discarded}")
            profile_after_discard = _expect(
                client.get(f"/v1/activities/{activity_id}/profile"),
                200,
            )
            profile_after_discard_stats = _dict_value(profile_after_discard, "latest_stats")
            if profile_after_discard_stats["sample_size"] != 1:
                raise AssertionError("discarded bad timer changed Activity Profile sample size")

        with psycopg.connect(args.database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      (select count(*) from model_update_decision where user_id = %s) as decisions,
                      (select count(*) from timing_event_span where user_id = %s) as spans,
                      (select count(*) from activity_stats_snapshot where user_id = %s) as stats
                    """,
                    (user_id, user_id, user_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise AssertionError("Phase 2 SQL proof returned no row")
                decision_count, span_count, stats_count = row

        if decision_count != 2 or span_count < 2 or stats_count < 1:
            raise AssertionError(
                "expected Phase 2 persistence rows, got "
                f"decisions={decision_count}, spans={span_count}, stats={stats_count}"
            )

        summary.update(
            {
                "activity_id": activity_id,
                "reviewed_session_id": session_id,
                "bad_timer_session_id": bad_timer_session_id,
                "active_seconds": reviewed_session["active_seconds"],
                "wall_seconds": reviewed_session["wall_seconds"],
                "detour_seconds": reviewed_session["detour_seconds"],
                "interruption_seconds": reviewed_session["interruption_seconds"],
                "profile_sample_size": profile_after_discard_stats["sample_size"],
                "model_update_decisions": decision_count,
                "timing_event_spans": span_count,
                "activity_stats_snapshots": stats_count,
            }
        )
        print(json.dumps({"status": "passed", "phase": "phase2", "summary": summary}, indent=2))
        return 0
    finally:
        if not args.keep_data:
            _cleanup(args.database_url, user_id)


def _create_completed_session(
    client: httpx.Client,
    *,
    activity_id: str,
    device_id: str,
    mutation_prefix: str,
    sequence_start: int,
) -> str:
    session = _expect(
        client.post(
            "/v1/timing/sessions",
            json={
                "mutation": _mutation(device_id, f"{mutation_prefix}-session", sequence_start),
                "activity_id": activity_id,
                "client_session_id": f"{mutation_prefix}-{uuid4().hex}",
                "mode": "whole_task",
            },
        ),
        201,
    )
    session_id = _string_value(session, "id")
    for mutation_id, offset, event_type, client_time in [
        ("start", 1, "session_started", "2026-04-28T12:00:00Z"),
        ("detour-start", 2, "resource_detour_started", "2026-04-28T12:05:00Z"),
        ("detour-end", 3, "resource_detour_completed", "2026-04-28T12:15:00Z"),
        ("interrupt-start", 4, "interruption_started", "2026-04-28T12:20:00Z"),
        ("interrupt-end", 5, "interruption_completed", "2026-04-28T12:25:00Z"),
    ]:
        _expect(
            client.post(
                f"/v1/timing/sessions/{session_id}/events",
                json={
                    "mutation": _mutation(
                        device_id,
                        f"{mutation_prefix}-{mutation_id}",
                        sequence_start + offset,
                    ),
                    "event_type": event_type,
                    "client_time": client_time,
                },
            ),
            201,
        )
    _expect(
        client.post(
            f"/v1/timing/sessions/{session_id}/complete",
            json={
                "mutation": _mutation(
                    device_id,
                    f"{mutation_prefix}-complete",
                    sequence_start + 10,
                ),
                "completed_at": "2026-04-28T12:30:00Z",
            },
        ),
        200,
    )
    return session_id


def _assert_reviewed_friction_totals(session: dict[str, object]) -> None:
    expected = {
        "status": "reviewed",
        "model_inclusion": "full",
        "active_seconds": 900,
        "wall_seconds": 1800,
        "detour_seconds": 600,
        "interruption_seconds": 300,
    }
    for key, value in expected.items():
        if session.get(key) != value:
            raise AssertionError(f"unexpected reviewed session {key}: {session}")
    spans = session.get("spans")
    if not isinstance(spans, list):
        raise AssertionError(f"expected span list, got {session}")
    by_type = {span["span_type"]: span for span in spans if isinstance(span, dict)}
    if by_type["resource_detour"]["count_in_active_time"]:
        raise AssertionError(f"resource detour counted as active: {by_type['resource_detour']}")
    if by_type["interruption"]["count_in_active_time"]:
        raise AssertionError(f"interruption counted as active: {by_type['interruption']}")


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
    raise AssertionError(f"API did not become healthy before Phase 2 smoke: {last_error}")


def _string_value(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise AssertionError(f"expected {key} to be a string")
    return value


def _dict_value(data: dict[str, object], key: str) -> dict[str, object]:
    value = data[key]
    if not isinstance(value, dict):
        raise AssertionError(f"expected {key} to be an object")
    return value


def _cleanup(database_url: str, user_id: UUID) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from app_user where id = %s", (user_id,))


if __name__ == "__main__":
    raise SystemExit(main())
